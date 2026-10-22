import uuid
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# CP08: prueba el POST, así que NO usa la fixture `personal`.
# Sí necesita un establecimiento existente, así que pide `establecimiento`.
def test_cp08_crear_personal(establecimiento):
    r = client.post("/personal", json={
        "nombre": "Ana",
        "apellido": "Pérez",
        "email": f"ana.{uuid.uuid4().hex[:8]}@example.com",
        "telefono": "099123456",
        "cargo": "Médico",
        "id_establecimiento": establecimiento["id_establecimiento"],
        "especialidad": "General",
        "costo_consulta": 500,
        "activo": True,
    })
    assert r.status_code == 201, r.text

    creado = r.json()
    assert creado["nombre"] == "Ana"
    assert creado["id_establecimiento"] == establecimiento["id_establecimiento"]

    # limpieza: el personal tiene que borrarse ANTES que el establecimiento.
    # La fixture `establecimiento` limpia después de este bloque, así que el orden es correcto.
    client.delete(f"/personal/{creado['id_personal']}")


# CP09: necesita un personal ya creado, así que usa la fixture `personal`.
def test_cp09_filtrar_por_establecimiento(personal):
    id_est = personal["id_establecimiento"]

    r = client.get("/personal", params={"id_establecimiento": id_est})
    assert r.status_code == 200

    lista = r.json()
    # 1. el nuestro está en la lista
    assert any(p["id_personal"] == personal["id_personal"] for p in lista)
    # 2. y NO hay nadie de otro establecimiento
    assert all(p["id_establecimiento"] == id_est for p in lista)


def test_cp09_filtrar_por_cargo(personal):
    r = client.get("/personal", params={"cargo": personal["cargo"]})
    assert r.status_code == 200

    lista = r.json()
    assert any(p["id_personal"] == personal["id_personal"] for p in lista)
    assert all(p["cargo"] == personal["cargo"] for p in lista)