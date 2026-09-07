"""Synchronize official sanctions lists used by the internal screening engine."""

from __future__ import annotations

from datetime import UTC, datetime
import re
import xml.etree.ElementTree as ET

import requests

from UsersAPI.database import SessionLocal
from UsersAPI.domains.clients.models import ScreeningEntryDB, ScreeningSourceDB
from UsersAPI.domains.clients.services.screening_provider import normalize_screening_text

TIMEOUT = 60


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


def _children_map(element: ET.Element) -> dict[str, list[ET.Element]]:
    result: dict[str, list[ET.Element]] = {}
    for child in element.iter():
        if child is element:
            continue
        result.setdefault(_local_name(child.tag), []).append(child)
    return result


def _text(elements: list[ET.Element] | None) -> list[str]:
    return [" ".join((element.text or "").split()) for element in (elements or []) if (element.text or "").strip()]


def _parse_ofac(root: ET.Element) -> list[dict]:
    entries = []
    for node in root.iter():
        if _local_name(node.tag) != "SDNENTRY":
            continue
        fields = _children_map(node)
        first = _text(fields.get("FIRSTNAME"))
        last = _text(fields.get("LASTNAME"))
        name = " ".join(first + last).strip()
        if not name:
            continue
        aliases = []
        for aka in node.iter():
            if _local_name(aka.tag) != "AKA":
                continue
            aka_fields = _children_map(aka)
            aliases.extend(_text(aka_fields.get("FIRSTNAME")))
            aliases.extend(_text(aka_fields.get("LASTNAME")))
        identifiers = []
        for identifier in node.iter():
            if _local_name(identifier.tag) != "ID":
                continue
            for child in identifier.iter():
                if _local_name(child.tag) == "NUMBER" and child.text:
                    identifiers.append(child.text.strip())
        external_id = (_text(fields.get("UID")) or [name])[0]
        entry_type = (_text(fields.get("SDNTYPE")) or ["UNKNOWN"])[0].upper()
        entries.append(
            {
                "external_id": external_id,
                "entry_type": entry_type,
                "name": name,
                "aliases": aliases,
                "identification_numbers": identifiers,
                "raw_data": {"source": "OFAC", "uid": external_id},
            }
        )
    return entries


def _parse_un(root: ET.Element) -> list[dict]:
    entries = []
    for section in root.iter():
        section_name = _local_name(section.tag)
        if section_name not in {"INDIVIDUAL", "ENTITY"}:
            continue
        fields = _children_map(section)
        names = []
        for key in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME", "NAME"):
            names.extend(_text(fields.get(key)))
        name = " ".join(dict.fromkeys(names)).strip()
        if not name:
            continue
        aliases = []
        for key in ("ALIAS_NAME", "ALIAS"):
            aliases.extend(_text(fields.get(key)))
        external_id = (_text(fields.get("REFERENCE_NUMBER")) or [name])[0]
        identifiers = []
        for key in ("NUMBER", "IDENTIFICATION_NUMBER", "PASSPORT_NUMBER"):
            identifiers.extend(_text(fields.get(key)))
        entries.append(
            {
                "external_id": external_id,
                "entry_type": "INDIVIDUAL" if section_name == "INDIVIDUAL" else "ENTITY",
                "name": name,
                "aliases": aliases,
                "identification_numbers": identifiers,
                "raw_data": {"source": "UN", "reference_number": external_id},
            }
        )
    return entries


def _parse(source_code: str, content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    if source_code == "OFAC_SDN":
        return _parse_ofac(root)
    if source_code == "UN_CONSOLIDATED":
        return _parse_un(root)
    raise ValueError(f"Unsupported screening source: {source_code}")


def sync_source(db, source: ScreeningSourceDB) -> int:
    response = requests.get(source.url, timeout=TIMEOUT)
    response.raise_for_status()
    entries = _parse(source.code, response.content)
    if not entries:
        raise RuntimeError(f"No entries parsed from {source.code}")

    db.query(ScreeningEntryDB).filter(ScreeningEntryDB.source_id == source.id).delete(
        synchronize_session=False
    )
    for item in entries:
        db.add(
            ScreeningEntryDB(
                source_id=source.id,
                external_id=str(item["external_id"])[:150],
                entry_type=str(item["entry_type"])[:20],
                name=str(item["name"])[:300],
                normalized_name=normalize_screening_text(item["name"])[:300],
                aliases=[str(alias)[:300] for alias in item["aliases"]],
                identification_numbers=[str(value)[:150] for value in item["identification_numbers"]],
                raw_data=item["raw_data"],
                active=True,
            )
        )
    source.last_sync_at = datetime.now(UTC)
    source.last_sync_status = "SUCCESS"
    source.last_sync_error = None
    return len(entries)


def main() -> None:
    db = SessionLocal()
    try:
        sources = db.query(ScreeningSourceDB).filter(ScreeningSourceDB.active.is_(True)).all()
        if not sources:
            raise RuntimeError("No active screening sources configured")
        for source in sources:
            try:
                count = sync_source(db, source)
                db.commit()
                print(f"{source.code}: {count} registros sincronizados")
            except Exception as exc:
                db.rollback()
                source = db.query(ScreeningSourceDB).filter(ScreeningSourceDB.code == source.code).one()
                source.last_sync_at = datetime.now(UTC)
                source.last_sync_status = "ERROR"
                source.last_sync_error = str(exc)[:2000]
                db.commit()
                raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
