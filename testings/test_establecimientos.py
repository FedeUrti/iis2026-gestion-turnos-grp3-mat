"""Tests de /establecimientos (US01): CP01 a CP07 + validaciones.

Usa las fixtures `establecimiento` y `personal` de conftest.py.
No se importan: pytest las inyecta por el nombre del parámetro.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def payload_valido(**cambios):
    """Payload completo con nombre único. `cambios` pisa los campos que quieras."""
    payload = {
        "nombre_comercial": f"Test {uuid.uuid4().hex[:8]}",
        "direccion": "Calle Falsa 123",
        "telefono": "099123456",
        "correo_electronico": "test@example.com",
        "horario_apertura": "08:00:00",
        "horario_cierre": "18:00:00",
    }
    payload.update(cambios)
    return payload


# ---------------------------------------------------------------------------
# CP01: POST válido -> 201 y queda guardado (JD01, JD02, JD03)
# Un mismo test se repite con 3 juegos de datos. Al nombre se le agrega un
# sufijo único para que una corrida no choque (409) con la anterior.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("datos", [
    pytest.param({
        "nombre_comercial": "Barbería Supercool",
        "direccion": "18 de julio 228",
        "telefono": "099321654",
        "correo_electronico": "barberiasupercool@gmail.com",
        "horario_apertura": "12:30:00",
        "horario_cierre": "20:30:00",
    }, id="JD01"),
    pytest.param({
        "nombre_comercial": "Clínica de nombre muy creativo",
        "direccion": "José Dodera 033",
        "telefono": "067666777",
        "correo_electronico": "mailmuycreativo@gmail.com",
        "horario_apertura": "06:00:00",
        "horario_cierre": "23:00:00",
    }, id="JD02"),
    pytest.param({
        "nombre_comercial": "Beauty Spa",
        "direccion": "Florida 222",
        "telefono": "099123123",
        "correo_electronico": "beautyspa@hotmail.com",
        "horario_apertura": "10:30:00",
        "horario_cierre": "18:30:00",
    }, id="JD03"),
])
def test_cp01_crear_establecimiento_valido(datos):
    payload = {**datos, "nombre_comercial": f"{datos['nombre_comercial']} {uuid.uuid4().hex[:6]}"}

    r = client.post("/establecimientos", json=payload)
    assert r.status_code == 201, r.text   # el ", r.text" muestra el motivo si falla

    id_est = r.json()["id_establecimiento"]
    try:
        assert r.json()["nombre_comercial"] == payload["nombre_comercial"]

        # Se comprueba que realmente quedó guardado, consultándolo por su id.
        g = client.get(f"/establecimientos/{id_est}")
        assert g.status_code == 200
        assert g.json()["direccion"] == payload["direccion"]
        assert g.json()["telefono"] == payload["telefono"]
        assert g.json()["correo_electronico"] == payload["correo_electronico"]
    finally:
        # Limpieza: corre aunque algún assert haya fallado.
        client.delete(f"/establecimientos/{id_est}")


# ---------------------------------------------------------------------------
# CP02: nombre comercial duplicado -> 409 (JD04)
# Usa la fixture: ya hay un establecimiento creado y se intenta repetir su nombre.
# ---------------------------------------------------------------------------
def test_cp02_nombre_duplicado_devuelve_409(establecimiento):
    payload = payload_valido(
        nombre_comercial=establecimiento["nombre_comercial"],
        direccion="Ituzaingo 026",
        telefono="091333222",
        correo_electronico="falsosupercool@hotmail.com",
    )

    r = client.post("/establecimientos", json=payload)
    try:
        assert r.status_code == 409, r.text
    finally:
        # Si la tabla NO tuviera UNIQUE en nombre_comercial, el POST daría 201
        # y quedaría una fila de más: se borra para no ensuciar la base.
        if r.status_code == 201:
            client.delete(f"/establecimientos/{r.json()['id_establecimiento']}")


# ---------------------------------------------------------------------------
# CP03: GET con id existente -> 200 y los datos correctos (JD05)
# ---------------------------------------------------------------------------
def test_cp03_obtener_establecimiento_existente(establecimiento):
    id_est = establecimiento["id_establecimiento"]

    r = client.get(f"/establecimientos/{id_est}")

    assert r.status_code == 200
    assert r.json()["id_establecimiento"] == id_est
    assert r.json()["nombre_comercial"] == establecimiento["nombre_comercial"]


# ---------------------------------------------------------------------------
# CP04: GET con id inexistente -> 404 (JD06)
# No necesita fixture: no hay nada que preparar.
# ---------------------------------------------------------------------------
def test_cp04_obtener_establecimiento_inexistente():
    r = client.get("/establecimientos/999999")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# CP05: PUT válido -> 200 y se actualiza en la base (JD07)
# ---------------------------------------------------------------------------
def test_cp05_actualizar_establecimiento(establecimiento):
    id_est = establecimiento["id_establecimiento"]
    cambios = {"direccion": "Jose Dodera 005", "telefono": "099123123"}

    r = client.put(f"/establecimientos/{id_est}", json=cambios)
    assert r.status_code == 200, r.text
    assert r.json()["direccion"] == "Jose Dodera 005"

    # Se vuelve a consultar para confirmar que el cambio quedó persistido.
    g = client.get(f"/establecimientos/{id_est}")
    assert g.json()["direccion"] == "Jose Dodera 005"
    assert g.json()["telefono"] == "099123123"
    # Lo que no se envió no debe cambiar.
    assert g.json()["nombre_comercial"] == establecimiento["nombre_comercial"]


# ---------------------------------------------------------------------------
# CP06: DELETE de un establecimiento SIN personal -> 204 y deja de existir (JD08)
# ---------------------------------------------------------------------------
def test_cp06_eliminar_establecimiento_sin_personal(establecimiento):
    id_est = establecimiento["id_establecimiento"]

    r = client.delete(f"/establecimientos/{id_est}")
    assert r.status_code == 204

    # Ya no debe existir. (La fixture intentará borrarlo de nuevo al final
    # y recibirá un 404, que no molesta.)
    assert client.get(f"/establecimientos/{id_est}").status_code == 404


# ---------------------------------------------------------------------------
# CP07: DELETE de un establecimiento CON personal -> 409 (JD13)
# La fixture `personal` arrastra su propio establecimiento. Al terminar, pytest
# borra primero el personal y después el establecimiento (orden inverso).
# ---------------------------------------------------------------------------
def test_cp07_eliminar_establecimiento_con_personal(personal):
    id_est = personal["id_establecimiento"]

    r = client.delete(f"/establecimientos/{id_est}")
    assert r.status_code == 409, r.text

    # Y el establecimiento sigue existiendo.
    assert client.get(f"/establecimientos/{id_est}").status_code == 200


# ---------------------------------------------------------------------------
# Validaciones: un campo inválido devuelve 400 (el handler convierte 422 en 400)
# Como el POST es rechazado, no se inserta nada.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("campo, valor", [
    pytest.param("correo_electronico", "no-es-un-mail", id="mail_invalido"),
    pytest.param("horario_apertura", "25:99:00", id="hora_invalida"),
    pytest.param("nombre_comercial", "", id="nombre_vacio"),
    pytest.param("telefono", "", id="telefono_vacio"),
])
def test_crear_establecimiento_campo_invalido(campo, valor):
    r = client.post("/establecimientos", json=payload_valido(**{campo: valor}))
    try:
        assert r.status_code == 400, r.text
    finally:
        if r.status_code == 201:   # por si una validación faltara y se insertara
            client.delete(f"/establecimientos/{r.json()['id_establecimiento']}")


def test_crear_establecimiento_campo_faltante():
    payload = payload_valido()
    del payload["direccion"]

    r = client.post("/establecimientos", json=payload)
    assert r.status_code == 400, r.text