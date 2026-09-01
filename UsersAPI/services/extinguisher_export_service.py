from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models import ExtinguisherInspectionDB, UserTenantDB
from ..repositories.extinguisher_repository import ExtinguisherRepository
from ..util.extinguisher_excel_utils import export_extinguishers_to_excel


def export_extinguishers(db: Session, current_user: UserTenantDB, tenant_id: int):
    extinguishers = ExtinguisherRepository(db).get_all_by_tenant(tenant_id, include_inactive=True)
    data = []
    for extinguisher in extinguishers:
        ultima = (
            db.query(ExtinguisherInspectionDB)
            .filter(ExtinguisherInspectionDB.tenant_id == tenant_id, ExtinguisherInspectionDB.extinguisher_id == extinguisher.id)
            .order_by(desc(ExtinguisherInspectionDB.inspection_date), desc(ExtinguisherInspectionDB.id))
            .first()
        )
        contador = int(extinguisher.inspections_since_hydrostatic_test or 0)
        data.append({
            "Código": extinguisher.code,
            "Tipo": extinguisher.extinguisher_type.name if extinguisher.extinguisher_type else "",
            "Capacidad": extinguisher.capacity or "",
            "Ubicación": extinguisher.location or "",
            "Estado": "Activo" if extinguisher.active else "Inactivo",
            "Stock": "Sí" if extinguisher.is_stock else "No",
            "Última recarga": extinguisher.last_recharge_date or "",
            "Próxima recarga": extinguisher.next_recharge_date or "",
            "Última revisión": ultima.inspection_date if ultima else "",
            "Resultado última revisión": ultima.result if ultima else "",
            "Revisiones desde hidrostática": contador,
            "Última prueba hidrostática": extinguisher.last_hydrostatic_test_date or "",
            "Próxima prueba hidrostática": extinguisher.next_hydrostatic_test_date or "",
            "Hidrostática requerida": "Sí" if contador >= 4 else "No",
        })
    return export_extinguishers_to_excel(data, current_user)
