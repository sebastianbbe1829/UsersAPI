from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
import re
import unicodedata
from defusedxml import ElementTree as ET

import requests
from sqlalchemy.orm import Session

from ..models import ClientDB, ScreeningEntryDB, ScreeningSourceDB


OFAC_SDN_URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.XML"
OFAC_SDN_CODE = "OFAC_SDN"


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
    return element.tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if _local_name(child) == name and child is not element and child.text:
            value = child.text.strip()
            if value:
                return value
    return None


def _child_values(element: ET.Element, name: str) -> list[str]:
    values: list[str] = []
    for child in element.iter():
        if _local_name(child) == name and child is not element and child.text:
            value = child.text.strip()
            if value:
                values.append(value)
    return values


def _parse_ofac_sdn(xml_content: bytes) -> list[dict]:
    root = ET.fromstring(xml_content)
    entries: list[dict] = []

    for node in root.iter():
        if _local_name(node) != "sdnEntry":
            continue

        external_id = _child_text(node, "uid")
        entry_type = (_child_text(node, "sdnType") or "ENTITY").upper()
        first_name = _child_text(node, "firstName")
        last_name = _child_text(node, "lastName")
        entity_name = _child_text(node, "entityName")
        ship_name = _child_text(node, "shipName")
        name = (
            entity_name
            or ship_name
            or " ".join(part for part in (first_name, last_name) if part)
        )
        if not external_id or not name:
            continue

        aliases: list[str] = []
        for aka in node.iter():
            if _local_name(aka) != "aka":
                continue
            aka_first = _child_text(aka, "firstName")
            aka_last = _child_text(aka, "lastName")
            aka_name = _child_text(aka, "name") or " ".join(
                part for part in (aka_first, aka_last) if part
            )
            if aka_name and aka_name not in aliases:
                aliases.append(aka_name)

        identification_numbers = _child_values(node, "idNumber")
        entries.append(
            {
                "external_id": external_id,
                "entry_type": entry_type,
                "name": name,
                "normalized_name": normalize_screening_text(name),
                "aliases": aliases,
                "identification_numbers": identification_numbers,
                "raw_data": {"source": OFAC_SDN_CODE, "uid": external_id},
            }
        )

    if not entries:
        raise ValueError("OFAC SDN no contiene registros procesables")
    return entries


def sync_ofac_sdn(db: Session) -> dict[str, int | str]:
    now = datetime.now(UTC).replace(tzinfo=None)
    source = (
        db.query(ScreeningSourceDB)
        .filter(ScreeningSourceDB.code == OFAC_SDN_CODE)
        .one_or_none()
    )
    if source is None:
        source = ScreeningSourceDB(
            code=OFAC_SDN_CODE,
            name="OFAC SDN",
            provider="OFAC",
            url=OFAC_SDN_URL,
            active=True,
        )
        db.add(source)
        db.flush()
    elif source.url != OFAC_SDN_URL:
        source.url = OFAC_SDN_URL

    try:
        response = requests.get(
            OFAC_SDN_URL,
            headers={"User-Agent": "UsersAPI-Compliance-Screening/1.0"},
            timeout=(15, 120),
        )
        response.raise_for_status()
        parsed_entries = _parse_ofac_sdn(response.content)

        existing = {
            item.external_id: item
            for item in db.query(ScreeningEntryDB)
            .filter(ScreeningEntryDB.source_id == source.id)
            .all()
        }
        seen_ids: set[str] = set()
        created = updated = 0

        for data in parsed_entries:
            external_id = data["external_id"]
            seen_ids.add(external_id)
            item = existing.get(external_id)
            if item is None:
                item = ScreeningEntryDB(source_id=source.id, **data)
                db.add(item)
                created += 1
            else:
                for field, value in data.items():
                    setattr(item, field, value)
                item.active = True
                item.updated_at = now
                updated += 1

        deactivated = 0
        for external_id, item in existing.items():
            if external_id not in seen_ids and item.active:
                item.active = False
                item.updated_at = now
                deactivated += 1

        source.last_sync_at = now
        source.last_sync_status = "SUCCESS"
        source.last_sync_error = None
        db.add(source)
        db.commit()

        return {
            "source": OFAC_SDN_CODE,
            "status": "SUCCESS",
            "total": len(parsed_entries),
            "created": created,
            "updated": updated,
            "deactivated": deactivated,
        }
    except Exception as exc:
        db.rollback()
        source = (
            db.query(ScreeningSourceDB)
            .filter(ScreeningSourceDB.code == OFAC_SDN_CODE)
            .one_or_none()
        )
        if source is not None:
            source.last_sync_at = now
            source.last_sync_status = "ERROR"
            source.last_sync_error = str(exc)[:2000]
            db.commit()
        raise


SCREENING_LIST_PROVIDERS = {
    OFAC_SDN_CODE: sync_ofac_sdn,
}


def sync_all_screening_lists(db: Session) -> dict:
    results: list[dict] = []

    for code, provider in SCREENING_LIST_PROVIDERS.items():
        try:
            results.append(provider(db))
        except Exception as exc:
            results.append(
                {
                    "source": code,
                    "status": "ERROR",
                    "error": str(exc)[:2000],
                }
            )

    successful = sum(1 for result in results if result["status"] == "SUCCESS")
    failed = len(results) - successful

    return {
        "status": (
            "SUCCESS"
            if failed == 0
            else "PARTIAL_ERROR"
            if successful
            else "ERROR"
        ),
        "sources": results,
        "total_sources": len(results),
        "successful_sources": successful,
        "failed_sources": failed,
    }


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
                    _similarity(
                        name,
                        normalize_screening_text(alias),
                    )
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
