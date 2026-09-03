from types import SimpleNamespace

from UsersAPI.util import excel_utils
from UsersAPI.util import extinguisher_excel_utils


def test_excel_user_resolution_paths():
    assert excel_utils._obtener_datos_usuario(None) == ("Usuario no identificado", "N/A")
    assert excel_utils._obtener_datos_usuario(SimpleNamespace(name="Ana", dni=123)) == ("Ana", "123")
    assert excel_utils._obtener_datos_usuario(SimpleNamespace(name="Ana")) == ("Ana", "N/A")
    assert excel_utils._obtener_datos_usuario(
        SimpleNamespace(user=SimpleNamespace(name="Bob", dni="2"))
    ) == ("Bob", "2")
    assert excel_utils._obtener_datos_usuario(
        SimpleNamespace(app_user=SimpleNamespace(name="Cat", dni="3"))
    ) == ("Cat", "3")
    assert excel_utils._obtener_datos_usuario(SimpleNamespace(email="mail@test.com", dni="4")) == (
        "mail@test.com", "4"
    )
    assert excel_utils._obtener_datos_usuario(SimpleNamespace(dni="5")) == (
        "Usuario no identificado", "5"
    )


def test_export_to_excel_with_rows_and_user():
    data = [
        {"DNI": "1", "Nombre": "Ana", "Email": "a@x", "Teléfono": "111", "Estado": "Activo"},
        {"DNI": "2", "Nombre": "Bob", "Email": "b@x", "Teléfono": "222", "Estado": "Inactivo"},
    ]
    response = excel_utils.export_to_excel(data, "usuarios.xlsx", SimpleNamespace(name="Admin", dni="9"))
    assert response.media_type.startswith("application/vnd.openxmlformats")
    assert response.headers["content-disposition"] == 'attachment; filename="usuarios.xlsx"'


def test_export_to_excel_empty_data():
    response = excel_utils.export_to_excel([], "empty.xlsx")
    assert response.headers["content-disposition"] == 'attachment; filename="empty.xlsx"'


def test_extinguisher_user_resolution_paths():
    assert extinguisher_excel_utils._obtener_usuario(None) == ("Usuario no identificado", "N/A")
    assert extinguisher_excel_utils._obtener_usuario(SimpleNamespace(name="Ana", dni=1)) == ("Ana", "1")
    assert extinguisher_excel_utils._obtener_usuario(
        SimpleNamespace(user=SimpleNamespace(name="Bob", dni=2))
    ) == ("Bob", "2")
    assert extinguisher_excel_utils._obtener_usuario(SimpleNamespace(email="x@y", dni=3)) == ("x@y", "3")
    assert extinguisher_excel_utils._obtener_usuario(SimpleNamespace(dni=4)) == (
        "Usuario no identificado", "4"
    )


def test_export_extinguishers_to_excel_with_statuses():
    data = [
        {
            "Código": "E1", "Tipo": "ABC", "Capacidad": "10", "Ubicación": "A",
            "Estado": "Activo", "Stock": 1, "Hidrostática requerida": "Sí",
        },
        {
            "Código": "E2", "Tipo": "CO2", "Capacidad": "5", "Ubicación": "B",
            "Estado": "Inactivo", "Stock": 0, "Hidrostática requerida": "No",
        },
    ]
    response = extinguisher_excel_utils.export_extinguishers_to_excel(
        data, SimpleNamespace(name="Admin", dni="9")
    )
    assert response.media_type.startswith("application/vnd.openxmlformats")
    assert response.headers["content-disposition"] == 'attachment; filename="extintores.xlsx"'


def test_export_extinguishers_to_excel_empty():
    response = extinguisher_excel_utils.export_extinguishers_to_excel([])
    assert response.headers["content-disposition"] == 'attachment; filename="extintores.xlsx"'
