import uuid
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ---------------------------------------------------------------------------
# CP08: Creación de personal con múltiples juegos de datos (JD09 a JD12)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("datos", [
    pytest.param({
        "nombre": "John",
        "apellido": "Tack",
        "email": "john.tack@hotmail.com",
        "telefono": "099666999",
        "cargo": "Psicólogo",
        "especialidad": "Psicología",
        "costo_consulta": 2200,
        "duracion_atencion": 30,
        "activo": True
    }, id="JD09"),
    pytest.param({
        "nombre": "David",
        "apellido": "Martinez",
        "email": "randomchoom77@gmail.com",
        "telefono": "099277277",
        "cargo": "Médico",
        "especialidad": "Medicina general",
        "costo_consulta": 2077,
        "duracion_atencion": 30,
        "activo": True
    }, id="JD10"),
    pytest.param({
        "nombre": "Sal",
        "apellido": "Fisher",
        "email": "sallyface@gmail.com",
        "telefono": "099666666",
        "cargo": "Psicólogo",
        "especialidad": "Psicología",
        "costo_consulta": 1800,
        "duracion_atencion": 30,
        "activo": False
    }, id="JD11"),
    pytest.param({
        "nombre": "Edward",
        "apellido": "Scissorhands",
        "email": "j0venm4n0sdetijer4@gmail.com",
        "telefono": "099121121",
        "cargo": "Peluquero",
        "especialidad": "Peluquería",
        "costo_consulta": 600,
        "duracion_atencion": 30,
        "activo": True
    }, id="JD12"),
])
def test_cp08_crear_personal(establecimiento, datos):
    payload = {
        **datos,
        "id_establecimiento": establecimiento["id_establecimiento"],
        "email": f"{uuid.uuid4().hex[:6]}_{datos['email']}"
    }

    r = client.post("/personal", json=payload)
    assert r.status_code == 201, r.text

    creado = r.json()
    assert creado["nombre"] == datos["nombre"]
    assert creado["apellido"] == datos["apellido"]
    assert creado["id_establecimiento"] == establecimiento["id_establecimiento"]
    assert creado["activo"] == datos["activo"]

    client.delete(f"/personal/{creado['id_personal']}")


# ---------------------------------------------------------------------------
# CP09: Filtrar personal por establecimiento
# ---------------------------------------------------------------------------
def test_cp09_filtrar_por_establecimiento(personal):
    id_est = personal["id_establecimiento"]

    r = client.get("/personal", params={"id_establecimiento": id_est})
    assert r.status_code == 200

    lista = r.json()
    assert all(p["id_establecimiento"] == id_est for p in lista)


# ---------------------------------------------------------------------------
# CP09: Filtrar personal por cargo
# ---------------------------------------------------------------------------
def test_cp09_filtrar_por_cargo(personal):
    cargo_buscado = personal["cargo"]

    r = client.get("/personal", params={"cargo": cargo_buscado})
    assert r.status_code == 200

    lista = r.json()
    assert all(p["cargo"] == cargo_buscado for p in lista)