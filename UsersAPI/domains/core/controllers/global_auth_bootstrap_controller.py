from sqlalchemy.orm import Session

from ..schemas import SuperBootstrapMfaVerifyRequest
from ..services.global_auth_service import verify_bootstrap_mfa as verify_bootstrap_mfa_service


def verify_bootstrap_mfa(
    datos: SuperBootstrapMfaVerifyRequest,
    bootstrap_secret: str,
    db: Session,
):
    return verify_bootstrap_mfa_service(
        datos,
        bootstrap_secret,
        db,
    )
