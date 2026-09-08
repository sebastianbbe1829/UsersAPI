from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
import logging
import re
import unicodedata
from defusedxml import ElementTree as ET

import requests
from sqlalchemy.orm import Session

from ..models import ClientDB, ScreeningEntryDB, ScreeningSourceDB


logger = logging.getLogger("UsersAPI.screening")

OFAC_SDN_CODE = "OFAC_SDN"
OFAC_CONSOLIDATED_CODE = "OFAC_CONSOLIDATED"
UN_CONSOLIDATED_CODE = "UN_CONSOLIDATED"

OFAC_SDN_URL = (
    "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
)
OFAC_CONSOLIDATED_URL = (
    "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/CONSOLIDATED.XML"
)
UN_CONSOLIDATED_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

SCREENING_HTTP_TIMEOUT = (15, 120)


@dataclass(frozen=True)
class ScreeningResult:
    status: str
    risk_level: str
    matched: bool
    list_type: str | None
    response: dict


def normalize_screening_text(value: str | None) -> str:
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.upper()
    value = re.sub(r"[^A-Z0-9 ]+", " ", value)
    return " ".join(value.split())


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1].upper()


def _text(elements: list[ET.Element] | None) -> list[str]:
    return [
        " ".join((element.text or "").split())
        for element in (elements or [])
        if (element.text or "").strip()
    ]


def _children_map(element: ET.Element) -> dict[str, list[ET.Element]]:
    result: dict[str, list[ET.Element]] = {}
    for child in element.iter():
        if child is element:
            continue
        result.setdefault(_local_name(child), []).append(child)
    return result


def _child_text(element: ET.Element, name: str) -> str | None:
    target = name.upper()
    for child in element.iter():
        if _local_name(child) == target and child is not element and child.text:
            value = child.text.strip()
            if value:
                return value
    return None


def _parse_ofac(xml_content: bytes, source_code: str) -> list[dict]:
    root = ET.fromstring(xml_content)
    entries: list[dict] = []

    for node in root.iter():
        if _local_name(node) != "SDNENTRY":
            continue

        fields = _children_map(node)
        external_id = (_text(fields.get("UID")) or [None])[0]
        entry_type = (_text(fields.get("SDNTYPE")) or ["ENTITY"])[0].upper()
        first_name = (_text(fields.get("FIRSTNAME")) or [None])[0]
        last_name = (_text(fields.get("LASTNAME")) or [None])[0]
        entity_name = (_text(fields.get("ENTITYNAME")) or [None])[0]
        ship_name = (_text(fields.get("SHIPNAME")) or [None])[0]
        name = entity_name or ship_name or " ".join(
            part for part in (first_name, last_name) if part
        )
        if not external_id or not name:
            continue

        aliases: list[str] = []
        for aka in node.iter():
            if _local_name(aka) != "AKA":
                continue
            aka_fields = _children_map(aka)
            aka_name = (_text(aka_fields.get("NAME")) or [None])[0]
            if not aka_name:
                aka_first = (_text(aka_fields.get("FIRSTNAME")) or [None])[0]
                aka_last = (_text(aka_fields.get("LASTNAME")) or [None])[0]
                aka_name = " ".join(
                    part for part in (aka_first, aka_last) if part
                )
            if aka_name and aka_name not in aliases:
                aliases.append(aka_name)

        identification_numbers: list[str] = []
        for identifier in node.iter():
            if _local_name(identifier) != "ID":
                continue
            for child in identifier.iter():
                if _local_name(child) in {"NUMBER", "IDNUMBER"} and child.text:
                    value = child.text.strip()
                    if value and value not in identification_numbers:
                        identification_numbers.append(value)

        entries.append(
            {
                "external_id": external_id,
                "entry_type": entry_type,
                "name": name,
                "normalized_name": normalize_screening_text(name),
                "aliases": aliases,
                "identification_numbers": identification_numbers,
                "raw_data": {"source": source_code, "uid": external_id},
            }
        )

    if not entries:
        raise ValueError(f"{source_code} no contiene registros procesables")
    return entries


def _parse_ofac_sdn(xml_content: bytes) -> list[dict]:
    return _parse_ofac(xml_content, OFAC_SDN_CODE)


def _parse_un(xml_content: bytes) -> list[dict]:
    root = ET.fromstring(xml_content)
    entries: list[dict] = []

    for section in root.iter():
        section_name = _local_name(section)
        if section_name not in {"INDIVIDUAL", "ENTITY"}:
            continue

        fields = _children_map(section)
        names: list[str] = []
        for key in (
            "FIRST_NAME",
            "SECOND_NAME",
            "THIRD_NAME",
            "FOURTH_NAME",
            "NAME",
        ):
            names.extend(_text(fields.get(key)))
        name = " ".join(dict.fromkeys(names)).strip()
        if not name:
            continue

        aliases: list[str] = []
        for key in ("ALIAS_NAME", "ALIAS"):
            aliases.extend(_text(fields.get(key)))

        external_id = (_text(fields.get("REFERENCE_NUMBER")) or [name])[0]
        identification_numbers: list[str] = []
        for key in ("NUMBER", "IDENTIFICATION_NUMBER", "PASSPORT_NUMBER"):
            for value in _text(fields.get(key)):
                if value not in identification_numbers:
                    identification_numbers.append(value)

        entries.append(
            {
                "external_id": external_id,
                "entry_type": (
                    "INDIVIDUAL" if section_name == "INDIVIDUAL" else "ENTITY"
                ),
                "name": name,
                "normalized_name": normalize_screening_text(name),
                "aliases": aliases,
                "identification_numbers": identification_numbers,
                "raw_data": {
                    "source": UN_CONSOLIDATED_CODE,
                    "reference_number": external_id,
                },
            }
        )

    if not entries:
        raise ValueError("UN_CONSOLIDATED no contiene registros procesables")
    return entries


def _parse_source(source_code: str, xml_content: bytes) -> list[dict]:
    if source_code in {OFAC_SDN_CODE, OFAC_CONSOLIDATED_CODE}:
        return _parse_ofac(xml_content, source_code)
    if source_code == UN_CONSOLIDATED_CODE:
        return _parse_un(xml_content)
    raise ValueError(f"Fuente de listas restrictivas no soportada: {source_code}")


def _get_source(db: Session, source_code: str) -> ScreeningSourceDB:
    source = (
        db.query(ScreeningSourceDB)
        .filter(ScreeningSourceDB.code == source_code)
        .one_or_none()
    )
    if source is None:
        raise RuntimeError(
            f"La fuente {source_code} no está configurada. "
            "Ejecute las migraciones de catálogos de listas restrictivas."
        )
    return source


def _sync_source(db: Session, source_code: str) -> dict[str, int | str]:
    source = _get_source(db, source_code)
    now = datetime.now(UTC).replace(tzinfo=None)
    source_name = getattr(source, "name", source_code)
    logger.info(
        "[SCREENING_SYNC] Iniciando fuente %s (%s) URL=%s",
        source_code,
        source_name,
        source.url,
    )

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
        logger.info(
            "[SCREENING_SYNC] %s XML procesado: %s registros",
            source_code,
            len(parsed_entries),
        )

        logger.info(
            "[SCREENING_SYNC] %s consultando registros existentes...",
            source_code,
        )
        existing = {
            item.external_id: item
            for item in db.query(ScreeningEntryDB)
            .filter(ScreeningEntryDB.source_id == source.id)
            .all()
        }
        logger.info(
            "[SCREENING_SYNC] %s registros existentes: %s",
            source_code,
            len(existing),
        )

        seen_ids: set[str] = set()
        created = updated = deactivated = 0

        for data in parsed_entries:
            external_id = str(data["external_id"])[:150]
            seen_ids.add(external_id)
            values = {
                "external_id": external_id,
                "entry_type": str(data["entry_type"])[:20],
                "name": str(data["name"])[:300],
                "normalized_name": normalize_screening_text(data["name"])[:300],
                "aliases": [str(value)[:300] for value in data["aliases"]],
                "identification_numbers": [
                    str(value)[:150] for value in data["identification_numbers"]
                ],
                "raw_data": data["raw_data"],
            }
            item = existing.get(external_id)
            if item is None:
                db.add(ScreeningEntryDB(source_id=source.id, **values))
                created += 1
            else:
                for field, value in values.items():
                    setattr(item, field, value)
                item.active = True
                item.updated_at = now
                updated += 1

        for external_id, item in existing.items():
            if external_id not in seen_ids and item.active:
                item.active = False
                item.updated_at = now
                deactivated += 1

        logger.info(
            "[SCREENING_SYNC] %s persistiendo: creados=%s actualizados=%s "
            "desactivados=%s",
            source_code,
            created,
            updated,
            deactivated,
        )
        source.last_sync_at = now
        source.last_sync_status = "SUCCESS"
        source.last_sync_error = None
        db.add(source)
        db.commit()

        result = {
            "source": source_code,
            "status": "SUCCESS",
            "total": len(parsed_entries),
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
        }
        logger.info(
            "[SCREENING_SYNC] Fuente %s finalizada correctamente: %s",
            source_code,
            result,
        )
        return result
    except Exception as exc:
        db.rollback()
        source = _get_source(db, source_code)
        source.last_sync_at = now
        source.last_sync_status = "ERROR"
        source.last_sync_error = str(exc)[:2000]
        db.commit()
        logger.exception(
            "[SCREENING_SYNC] Fuente %s ERROR: %s",
            source_code,
            exc,
        )
        raise


def sync_ofac_sdn(db: Session) -> dict[str, int | str]:
    return _sync_source(db, OFAC_SDN_CODE)


def sync_ofac_consolidated(db: Session) -> dict[str, int | str]:
    return _sync_source(db, OFAC_CONSOLIDATED_CODE)


def sync_un_consolidated(db: Session) -> dict[str, int | str]:
    return _sync_source(db, UN_CONSOLIDATED_CODE)


SCREENING_LIST_PROVIDERS = {
    OFAC_SDN_CODE: sync_ofac_sdn,
    OFAC_CONSOLIDATED_CODE: sync_ofac_consolidated,
    UN_CONSOLIDATED_CODE: sync_un_consolidated,
}


def sync_all_screening_lists(db: Session) -> dict:
    logger.info(
        "[SCREENING_SYNC] Iniciando sincronización de %s fuentes: %s",
        len(SCREENING_LIST_PROVIDERS),
        ", ".join(SCREENING_LIST_PROVIDERS),
    )
    results: list[dict] = []

    for code, provider in SCREENING_LIST_PROVIDERS.items():
        try:
            results.append(provider(db))
        except Exception as exc:
            logger.error(
                "[SCREENING_SYNC] Fuente %s terminó con ERROR; "
                "continuando con las demás",
                code,
            )
            results.append(
                {
                    "source": code,
                    "status": "ERROR",
                    "error": str(exc)[:2000],
                }
            )

    successful = sum(1 for result in results if result["status"] == "SUCCESS")
    failed = len(results) - successful
    final_status = (
        "SUCCESS" if failed == 0 else "PARTIAL_ERROR" if successful else "ERROR"
    )

    result = {
        "status": final_status,
        "sources": results,
        "total_sources": len(results),
        "successful_sources": successful,
        "failed_sources": failed,
    }
    logger.info(
        "[SCREENING_SYNC] Sincronización finalizada: status=%s total=%s "
        "exitosas=%s fallidas=%s",
        final_status,
        len(results),
        successful,
        failed,
    )
    return result


class ScreeningProvider:
    code = "INTERNAL_OFFICIAL"

    def screen(self, client: ClientDB, db: Session) -> ScreeningResult:
        sources = (
            db.query(ScreeningSourceDB)
            .filter(ScreeningSourceDB.active.is_(True))
            .all()
        )
        if not sources:
            return ScreeningResult(
                status="PENDING",
                risk_level="UNKNOWN",
                matched=False,
                list_type=None,
                response={"reason": "No screening sources are synchronized"},
            )

        source_ids = [source.id for source in sources]
        document = normalize_screening_text(client.identification_number)
        name = normalize_screening_text(client.full_name)

        candidates = (
            db.query(ScreeningEntryDB)
            .filter(
                ScreeningEntryDB.source_id.in_(source_ids),
                ScreeningEntryDB.active.is_(True),
                (
                    ScreeningEntryDB.normalized_name.ilike(f"%{name}%")
                    | ScreeningEntryDB.identification_numbers.contains([document])
                ),
            )
            .all()
        )

        matches: list[dict] = []
        for entry in candidates:
            document_match = document and document in (
                entry.identification_numbers or []
            )
            name_score = _similarity(name, entry.normalized_name)
            alias_score = max(
                [
                    _similarity(name, normalize_screening_text(alias))
                    for alias in (entry.aliases or [])
                ],
                default=0.0,
            )
            score = max(name_score, alias_score)
            if document_match or score >= 0.88:
                matches.append(
                    {
                        "source": entry.source.code if entry.source else None,
                        "source_name": entry.source.name if entry.source else None,
                        "external_id": entry.external_id,
                        "name": entry.name,
                        "entry_type": entry.entry_type,
                        "score": round(score, 4),
                        "document_match": bool(document_match),
                        "aliases": entry.aliases or [],
                    }
                )

        if matches:
            return ScreeningResult(
                status="MATCH",
                risk_level="HIGH",
                matched=True,
                list_type=matches[0]["source"],
                response={"matches": matches},
            )

        return ScreeningResult(
            status="CLEAR",
            risk_level="LOW",
            matched=False,
            list_type=None,
            response={"matches": []},
        )
