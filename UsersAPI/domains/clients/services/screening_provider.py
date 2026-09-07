from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from difflib import SequenceMatcher

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import ClientDB, ScreeningEntryDB, ScreeningSourceDB


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
                or_(
                    ScreeningEntryDB.normalized_name.ilike(f"%{name}%"),
                    ScreeningEntryDB.identification_numbers.contains([document]),
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
