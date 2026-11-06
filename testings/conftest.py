# testings/conftest.py
from datetime import date, timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture
def establecimiento():
    """Crea un establecimiento dinámico para un único test y lo borra al terminar."""
    r = client.post("/establecimientos", json={
        "nombre_comercial": f"Test {uuid.uuid4().hex[:8]}",
        "direccion": f"Calle Falsa {uuid.uuid4().hex[:8]}",
        "telefono": f"099{uuid.uuid4().hex[:6]}",
        "correo_electronico": f"ok{uuid.uuid4().hex[:8]}@example.com",
        "horario_apertura": "08:00:00",
        "horario_cierre": "18:00:00"
    })
    assert r.status_code == 201, r.text
    datos = r.json()
    yield datos
    client.delete(f"/establecimientos/{datos['id_establecimiento']}")


@pytest.fixture
def personal(establecimiento):
    """Crea un personal asociado al establecimiento del test."""
    r = client.post("/personal", json={
        "nombre": "John",
        "apellido": "Doe",
        "email": f"john.doe.{uuid.uuid4().hex[:8]}@example.com",
        "telefono": "099111222",
        "cargo": "Médico",
        "id_establecimiento": establecimiento["id_establecimiento"],
        "especialidad": "General",
        "costo_consulta": 1500,
        "activo": True
    })
    assert r.status_code == 201, r.text
    datos = r.json()
    yield datos
    client.delete(f"/personal/{datos['id_personal']}")


@pytest.fixture
def crear_reserva(personal):
    """Factory fixture para crear reservas dinámicas asociadas al personal actual."""
    ids = []

    def _crear(fecha=None, hora="10:00:00", email=None):
        fecha = fecha or (date.today() + timedelta(days=7)).isoformat()
        email = email or f"t{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/reservas", json={
            "nombre": "Cliente Test",
            "email_solicitante": email,
            "telefono_solicitante": "099999999",
            "id_establecimiento": personal["id_establecimiento"],
            "id_personal": personal["id_personal"],
            "fecha_turno": fecha,
            "hora_turno": hora,
        })
        assert r.status_code == 202, r.text
        id_reserva = r.json()["turno"]["id"]
        ids.append(id_reserva)
        return id_reserva

    yield _crear
    for i in ids:
        client.delete(f"/reservas/{i}")