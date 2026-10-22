# testings/conftest.py
from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def establecimiento():
    nombre = f"Test {uuid.uuid4().hex[:8]}"
    r = client.post("/establecimientos", json={
            "nombre_comercial": f"Test {uuid.uuid4().hex[:8]}",
            "direccion": f"Calle Falsa {uuid.uuid4().hex[:8]}",
            "telefono": f"123456789{uuid.uuid4().hex[:8]}",
            "correo_electronico": f"ok{uuid.uuid4().hex[:8]}@example.com",
            "horario_apertura": "08:00:00.0000",
            "horario_cierre": "18:00:00.0000"})
    assert r.status_code == 201, r.text
    datos = r.json()
    yield datos
    client.delete(f"/establecimientos/{datos['id_establecimiento']}")

@pytest.fixture
def personal(establecimiento):          # depende de la fixture anterior
    r = client.post("/personal", json={
        "nombre": "John",
        "apellido": "Doe",
        "email": f"john.doe.{uuid.uuid4().hex[:8]}@example.com",
        "telefono": "111222333",
        "cargo": "Médico",
        "id_establecimiento": establecimiento["id_establecimiento"],
        "especialidad": "General",
        "costo_consulta": 0,
        "activo": True
    })
    assert r.status_code == 201, r.text
    datos = r.json()
    yield datos
    client.delete(f"/personal/{datos['id_personal']}")
@pytest.fixture
def reserva( personal):          # depende de las fixtures anteriores
    r = client.post("/personal", json={

        "email_solicitante": f"example{uuid.uuid4().hex[:8]}@gmail.com",
        "telefono_solicitante": f"09999999{uuid.uuid4().hex[:8]}",
        "id_establecimiento": personal["id_establecimiento"],
        "id_personal": personal["id_personal"],
        "fecha_turno": (date.today() + timedelta(days=7)).isoformat(),
        "nombre": "Exampleman",
        "hora_turno": "18:56:00.0000"
        }
    )
    assert r.status_code == 201, r.text
    datos = r.json()
    yield datos
    client.delete(f"/reservas/{datos['turno']['id']}")