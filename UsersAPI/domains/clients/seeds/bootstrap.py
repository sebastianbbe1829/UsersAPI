"""Initialize CLIENTS domain master data.

This bootstrap is intentionally isolated from the CORE bootstrap. It is safe
for repeated execution and can be invoked by deployment tooling after the
CLIENTS migrations have been applied.
"""

from sqlalchemy.orm import Session

from UsersAPI.domains.clients.seeds.countries import seed_countries
from UsersAPI.domains.clients.seeds.divipola import seed_divipola
from UsersAPI.domains.clients.seeds.identification_types import seed_identification_types


def bootstrap_clients(db: Session) -> dict[str, object]:
    countries_created, countries_updated = seed_countries(db)
    identification_created, identification_updated, identification_deactivated = (
        seed_identification_types(db)
    )
    divipola = seed_divipola(db)
    db.commit()

    return {
        "countries": {
            "created": countries_created,
            "updated": countries_updated,
        },
        "identification_types": {
            "created": identification_created,
            "updated": identification_updated,
            "deactivated": identification_deactivated,
        },
        "divipola": divipola,
    }
