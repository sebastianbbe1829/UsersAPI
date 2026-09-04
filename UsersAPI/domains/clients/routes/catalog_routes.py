from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from UsersAPI.domains.core.database import get_db
from UsersAPI.security.permissions import require_permission

from ..controllers.catalog_controller import (
    actualizar_ciudad,
    actualizar_departamento,
    actualizar_pais,
    actualizar_tipo_identificacion,
    crear_ciudad,
    crear_departamento,
    crear_pais,
    crear_tipo_identificacion,
    eliminar_ciudad,
    eliminar_departamento,
    eliminar_pais,
    eliminar_tipo_identificacion,
    listar_ciudades,
    listar_departamentos,
    listar_paises,
    listar_tipos_identificacion,
    obtener_ciudad,
    obtener_departamento,
    obtener_pais,
    obtener_tipo_identificacion,
)
from ..schemas.catalog import (
    CityCreate,
    CityRead,
    CityUpdate,
    CountryCreate,
    CountryRead,
    CountryUpdate,
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
    IdentificationTypeCreate,
    IdentificationTypeRead,
    IdentificationTypeUpdate,
)


catalog_routes = APIRouter(
    prefix="/clients/catalogs",
    tags=["Catálogos de clientes"],
)


# ============================================================
# TIPOS DE IDENTIFICACIÓN
# ============================================================

@catalog_routes.get("/identification-types", response_model=list[IdentificationTypeRead], dependencies=[Depends(require_permission("CLIENT_READ"))])
async def list_identification_types_route(include_inactive: bool = False, db: Session = Depends(get_db)):
    return listar_tipos_identificacion(db, include_inactive)


@catalog_routes.get("/identification-types/{item_id}", response_model=IdentificationTypeRead, dependencies=[Depends(require_permission("CLIENT_READ"))])
async def get_identification_type_route(item_id: int, db: Session = Depends(get_db)):
    return obtener_tipo_identificacion(db, item_id)


@catalog_routes.post("/identification-types", response_model=IdentificationTypeRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("CLIENT_CREATE"))])
async def create_identification_type_route(data: IdentificationTypeCreate, db: Session = Depends(get_db)):
    return crear_tipo_identificacion(db, data)


@catalog_routes.patch("/identification-types/{item_id}", response_model=IdentificationTypeRead, dependencies=[Depends(require_permission("CLIENT_UPDATE"))])
async def update_identification_type_route(item_id: int, data: IdentificationTypeUpdate, db: Session = Depends(get_db)):
    return actualizar_tipo_identificacion(db, item_id, data)


@catalog_routes.delete("/identification-types/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("CLIENT_DELETE"))])
async def delete_identification_type_route(item_id: int, db: Session = Depends(get_db)):
    eliminar_tipo_identificacion(db, item_id)


# ============================================================
# PAÍSES
# ============================================================

@catalog_routes.get("/countries", response_model=list[CountryRead], dependencies=[Depends(require_permission("CLIENT_READ"))])
async def list_countries_route(include_inactive: bool = False, db: Session = Depends(get_db)):
    return listar_paises(db, include_inactive)


@catalog_routes.get("/countries/{item_id}", response_model=CountryRead, dependencies=[Depends(require_permission("CLIENT_READ"))])
async def get_country_route(item_id: int, db: Session = Depends(get_db)):
    return obtener_pais(db, item_id)


@catalog_routes.post("/countries", response_model=CountryRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("CLIENT_CREATE"))])
async def create_country_route(data: CountryCreate, db: Session = Depends(get_db)):
    return crear_pais(db, data)


@catalog_routes.patch("/countries/{item_id}", response_model=CountryRead, dependencies=[Depends(require_permission("CLIENT_UPDATE"))])
async def update_country_route(item_id: int, data: CountryUpdate, db: Session = Depends(get_db)):
    return actualizar_pais(db, item_id, data)


@catalog_routes.delete("/countries/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("CLIENT_DELETE"))])
async def delete_country_route(item_id: int, db: Session = Depends(get_db)):
    eliminar_pais(db, item_id)


# ============================================================
# DEPARTAMENTOS
# ============================================================

@catalog_routes.get("/departments", response_model=list[DepartmentRead], dependencies=[Depends(require_permission("CLIENT_READ"))])
async def list_departments_route(country_id: int | None = None, include_inactive: bool = False, db: Session = Depends(get_db)):
    return listar_departamentos(db, country_id, include_inactive)


@catalog_routes.get("/departments/{item_id}", response_model=DepartmentRead, dependencies=[Depends(require_permission("CLIENT_READ"))])
async def get_department_route(item_id: int, db: Session = Depends(get_db)):
    return obtener_departamento(db, item_id)


@catalog_routes.post("/departments", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("CLIENT_CREATE"))])
async def create_department_route(data: DepartmentCreate, db: Session = Depends(get_db)):
    return crear_departamento(db, data)


@catalog_routes.patch("/departments/{item_id}", response_model=DepartmentRead, dependencies=[Depends(require_permission("CLIENT_UPDATE"))])
async def update_department_route(item_id: int, data: DepartmentUpdate, db: Session = Depends(get_db)):
    return actualizar_departamento(db, item_id, data)


@catalog_routes.delete("/departments/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("CLIENT_DELETE"))])
async def delete_department_route(item_id: int, db: Session = Depends(get_db)):
    eliminar_departamento(db, item_id)


# ============================================================
# CIUDADES / MUNICIPIOS
# ============================================================

@catalog_routes.get("/cities", response_model=list[CityRead], dependencies=[Depends(require_permission("CLIENT_READ"))])
async def list_cities_route(department_id: int | None = None, include_inactive: bool = False, db: Session = Depends(get_db)):
    return listar_ciudades(db, department_id, include_inactive)


@catalog_routes.get("/cities/{item_id}", response_model=CityRead, dependencies=[Depends(require_permission("CLIENT_READ"))])
async def get_city_route(item_id: int, db: Session = Depends(get_db)):
    return obtener_ciudad(db, item_id)


@catalog_routes.post("/cities", response_model=CityRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_permission("CLIENT_CREATE"))])
async def create_city_route(data: CityCreate, db: Session = Depends(get_db)):
    return crear_ciudad(db, data)


@catalog_routes.patch("/cities/{item_id}", response_model=CityRead, dependencies=[Depends(require_permission("CLIENT_UPDATE"))])
async def update_city_route(item_id: int, data: CityUpdate, db: Session = Depends(get_db)):
    return actualizar_ciudad(db, item_id, data)


@catalog_routes.delete("/cities/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_permission("CLIENT_DELETE"))])
async def delete_city_route(item_id: int, db: Session = Depends(get_db)):
    eliminar_ciudad(db, item_id)
