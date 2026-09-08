from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..models import ScreeningEntryDB
from .screening_provider import (
    SCREENING_HTTP_TIMEOUT,
    SCREENING_LIST_PROVIDERS,
    _get_source,
    _parse_source,
    logger,
    normalize_screening_text,
    requests,
)


BATCH_SIZE = 500


def _sync_source_bulk(db: Session, source_code: str) -> dict[str, int | str]:
    source = _get_source(db, source_code)
    now = datetime.now(UTC).replace(tzinfo=None)
    logger.info("[SCREENING_SYNC] Iniciando fuente %s (%s) URL=%s", source_code, source.name, source.url)

    try:
        logger.info("[SCREENING_SYNC] %s descargando datos...", source_code)
        response = requests.get(
            source.url,
            headers={"User-Agent": "UsersAPI-Compliance-Screening/1.0"},
            timeout=SCREENING_HTTP_TIMEOUT,
        )
        response.raise_for_status()
        logger.info(
            "[SCREENING_SYNC] %s descarga completada: %s bytes, HTTP %s",
            source_code,
            len(response.content),
            response.status_code,
        )

        logger.info("[SCREENING_SYNC] %s procesando XML...", source_code)
        parsed_entries = _parse_source(source_code, response.content)
        logger.info("[SCREENING_SYNC] %s XML procesado: %s registros", source_code, len(parsed_entries))

        logger.info("[SCREENING_SYNC] %s consultando IDs existentes...", source_code)
        existing_ids = {
            external_id
            for (external_id,) in db.query(ScreeningEntryDB.external_id)
            .filter(ScreeningEntryDB.source_id == source.id)
            .all()
        }
        logger.info("[SCREENING_SYNC] %s IDs existentes: %s", source_code, len(existing_ids))

        rows: list[dict] = []
        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()
        for data in parsed_entries:
            external_id = str(data["external_id"])[:150]
            if external_id in seen_ids:
                duplicate_ids.add(external_id)
                continue
            seen_ids.add(external_id)
            rows.append(
                {
                    "source_id": source.id,
                    "external_id": external_id,
                    "entry_type": str(data["entry_type"])[:20],
                    "name": str(data["name"])[:300],
                    "normalized_name": normalize_screening_text(data["name"])[:300],
                    "aliases": [str(value)[:300] for value in data["aliases"]],
                    "identification_numbers": [str(value)[:150] for value in data["identification_numbers"]],
                    "raw_data": data["raw_data"],
                    "active": True,
                    "updated_at": now,
                }
            )

        created = sum(1 for row in rows if row["external_id"] not in existing_ids)
        updated = len(rows) - created
        logger.info(
            "[SCREENING_SYNC] %s preparados: %s registros (creados=%s actualizados=%s duplicados_omitidos=%s)",
            source_code,
            len(rows),
            created,
            updated,
            len(duplicate_ids),
        )

        for offset in range(0, len(rows), BATCH_SIZE):
            batch = rows[offset : offset + BATCH_SIZE]
            statement = insert(ScreeningEntryDB).values(batch)
            statement = statement.on_conflict_do_update(
                constraint="uq_screening_entries_source_external_id",
                set_={
                    "entry_type": statement.excluded.entry_type,
                    "name": statement.excluded.name,
                    "normalized_name": statement.excluded.normalized_name,
                    "aliases": statement.excluded.aliases,
                    "identification_numbers": statement.excluded.identification_numbers,
                    "raw_data": statement.excluded.raw_data,
                    "active": True,
                    "updated_at": statement.excluded.updated_at,
                },
            )
            db.execute(statement)
            logger.info(
                "[SCREENING_SYNC] %s lote persistido: %s-%s de %s",
                source_code,
                offset + 1,
                offset + len(batch),
                len(rows),
            )

        missing_ids = existing_ids - seen_ids
        deactivated = 0
        if missing_ids:
            result = db.execute(
                update(ScreeningEntryDB)
                .where(
                    ScreeningEntryDB.source_id == source.id,
                    ScreeningEntryDB.external_id.in_(missing_ids),
                    ScreeningEntryDB.active.is_(True),
                )
                .values(active=False, updated_at=now)
            )
            deactivated = result.rowcount or 0

        source.last_sync_at = now
        source.last_sync_status = "SUCCESS"
        source.last_sync_error = None
        db.add(source)
        db.commit()

        result = {
            "source": source_code,
            "status": "SUCCESS",
            "total": len(rows),
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
        }
        logger.info("[SCREENING_SYNC] Fuente %s finalizada correctamente: %s", source_code, result)
        return result
    except Exception as exc:
        db.rollback()
        source = _get_source(db, source_code)
        source.last_sync_at = now
        source.last_sync_status = "ERROR"
        source.last_sync_error = str(exc)[:2000]
        db.commit()
        logger.exception("[SCREENING_SYNC] Fuente %s ERROR: %s", source_code, exc)
        raise


def sync_all_screening_lists_bulk(db: Session) -> dict:
    logger.info(
        "[SCREENING_SYNC] Iniciando sincronización optimizada de %s fuentes: %s",
        len(SCREENING_LIST_PROVIDERS),
        ", ".join(SCREENING_LIST_PROVIDERS),
    )
    results: list[dict] = []
    for code in SCREENING_LIST_PROVIDERS:
        try:
            results.append(_sync_source_bulk(db, code))
        except Exception as exc:
            logger.error(
                "[SCREENING_SYNC] Fuente %s terminó con ERROR; continuando con las demás",
                code,
            )
            results.append({"source": code, "status": "ERROR", "error": str(exc)[:2000]})

    successful = sum(1 for result in results if result["status"] == "SUCCESS")
    failed = len(results) - successful
    final_status = "SUCCESS" if failed == 0 else "PARTIAL_ERROR" if successful else "ERROR"
    result = {
        "status": final_status,
        "sources": results,
        "total_sources": len(results),
        "successful_sources": successful,
        "failed_sources": failed,
    }
    logger.info(
        "[SCREENING_SYNC] Sincronización optimizada finalizada: status=%s total=%s exitosas=%s fallidas=%s",
        final_status,
        len(results),
        successful,
        failed,
    )
    return result
