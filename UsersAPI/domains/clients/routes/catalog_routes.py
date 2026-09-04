from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.security.permissions import require_permission

from ..controllers.catalog_controller import (
    listar_ciudades,
    listar_departamentos,
    listar_paises,
    listar_tipos_identificacion,
)
from ..schemas.catalog import (
    CityRead,
    CountryRead,
    DepartmentRead,
    IdentificationTypeRead,
)


catalog_routes = APIRouter(
    prefix="/clients/catalogs",
    tags=["Catálogos de clientes"],
)


@catalog_routes.get(
    "/identification-types",
    response_model=list[IdentificationTypeRead],
    status_code=status.HTTP_200_OK,
    summary="Listar tipos de identificación",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def list_identification_types_route(db: Session = Depends(get_db)):
    return listar_tipos_identificacion(db)


@catalog_routes.get(
    "/countries",
    response_model=list[CountryRead],
    status_code=status.HTTP_200_OK,
    summary="Listar países",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def list_countries_route(db: Session = Depends(get_db)):
    return listar_paises(db)


@catalog_routes.get(
    "/departments",
    response_model=list[DepartmentRead],
    status_code=status.HTTP_200_OK,
    summary="Listar departamentos",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def list_departments_route(
    country_id: int | None = None,
    db: Session = Depends(get_db),
):
    return listar_departamentos(db, country_id)


@catalog_routes.get(
    "/cities",
    response_model=list[CityRead],
    status_code=status.HTTP_200_OK,
    summary="Listar ciudades",
    dependencies=[Depends(require_permission("CLIENT_READ"))],
)
async def list_cities_route(
    department_id: int | None = None,
    db: Session = Depends(get_db),
):
    return listar_ciudades(db, department_id)
