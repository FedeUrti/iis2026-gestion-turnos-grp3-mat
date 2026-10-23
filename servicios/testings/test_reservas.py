import uuid
import pytest
from fastapi.testclient import TestClient

from main import app
from worker_reservas import procesar_reservas_pendientes

client = TestClient(app)

# ---------------------------------------------------------------------------
# Juegos de datos base (sin IDs fijos)
# ---------------------------------------------------------------------------
JD16 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-11-05", "nombre": "Fulano", "hora_turno": "14:00:00"}
JD17 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-12-02", "nombre": "Fulano", "hora_turno": "08:30:00"}
JD18 = {"email_solicitante": "solicitante@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-12-05", "nombre": "Fulano", "hora_turno": "12:00:00"}
JD19 = {"email_solicitante": "solicitante2@gmail.com", "telefono_solicitante": "099222222", "fecha_turno": "2026-11-05", "nombre": "Mengano", "hora_turno": "15:00:00"}
JD20 = {"email_solicitante": "solicitante3@gmail.com", "telefono_solicitante": "099333333", "fecha_turno": "2026-11-24", "nombre": "Sultano", "hora_turno": "06:00:00"}

JD25 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-11-05", "nombre": "Fulano", "hora_turno": "15:00:00"}
JD26 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-11-20", "nombre": "Fulano", "hora_turno": "10:00:00"}
JD27 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-11-20", "nombre": "Fulano", "hora_turno": "22:00:00"}
JD28 = {"estado_reserva": "CANCELADO", "fecha_turno": "2026-11-24", "hora_turno": "06:00:00"}
JD29 = {"email_solicitante": "solicitante2@gmail.com", "telefono_solicitante": "099222222", "fecha_turno": "2026-11-24", "nombre": "Mengano", "hora_turno": "06:00:00"}
JD30 = {"email_solicitante": "solicitante1@gmail.com", "telefono_solicitante": "099111111", "fecha_turno": "2026-01-01", "nombre": "Fulano", "hora_turno": "16:00:00"}


def armar_payload(datos, personal):
    """Construye el payload completo uniendo el juego de datos con los IDs dinámicos."""
    return {
        **datos,
        "id_establecimiento": personal["id_establecimiento"],
        "id_personal": personal["id_personal"]
    }

def crear(datos, personal):
    payload = armar_payload(datos, personal)
    r = client.post("/reservas", json=payload)
    assert r.status_code == 202, r.text
    return r.json()["turno"]["id"]

def estado(id_reserva):
    return client.get(f"/reservas/{id_reserva}").json()["estado_reserva"]

def borrar(*ids):
    for id_reserva in ids:
        client.delete(f"/reservas/{id_reserva}")


# ---------------------------------------------------------------------------
# CP10: POST válido
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("datos", [JD16, JD17, JD18, JD19, JD20])
def test_cp10_reserva_valida(personal, datos):
    payload = armar_payload(datos, personal)
    r = client.post("/reservas", json=payload)
    assert r.status_code == 202, r.text

    turno = r.json()["turno"]
    try:
        assert turno["estado_reserva"] == "PENDIENTE"
        assert turno["id_personal"] == personal["id_personal"]
    finally:
        borrar(turno["id"])


# ---------------------------------------------------------------------------
# CP11, CP12, CP13: rechazos con 400
# ---------------------------------------------------------------------------
def test_cp11_profesional_inexistente(personal):
    payload = armar_payload(JD16, personal)
    payload["id_personal"] = 999999
    r = client.post("/reservas", json=payload)
    assert r.status_code == 400
    assert "No existe el personal" in str(r.json()["detail"])

def test_cp12_otro_establecimiento(personal, establecimiento):
    payload = armar_payload(JD16, personal)
    # Se pasa un ID de establecimiento diferente al del personal
    payload["id_establecimiento"] = establecimiento["id_establecimiento"] + 999
    r = client.post("/reservas", json=payload)
    assert r.status_code == 400

def test_cp13_profesional_inactivo(establecimiento):
    # Crear un personal inactivo
    r_pers = client.post("/personal", json={
        "nombre": "Inactivo", "apellido": "User", "email": f"inactivo_{uuid.uuid4().hex[:6]}@test.com",
        "telefono": "099000000", "cargo": "Médico", "id_establecimiento": establecimiento["id_establecimiento"],
        "especialidad": "General", "costo_consulta": 1000, "activo": False
    })
    pers_inactivo = r_pers.json()
    
    try:
        payload = armar_payload(JD16, pers_inactivo)
        r = client.post("/reservas", json=payload)
        assert r.status_code == 400
        assert "no está activo" in str(r.json()["detail"])
    finally:
        client.delete(f"/personal/{pers_inactivo['id_personal']}")


# ---------------------------------------------------------------------------
# CP14 a CP19
# ---------------------------------------------------------------------------
def test_cp14_turno_ocupado(personal):
    ids = []
    try:
        primera = crear(JD19, personal)
        ids.append(primera)
        procesar_reservas_pendientes()
        assert estado(primera) == "AGENDADO"

        segunda = crear(JD25, personal)
        ids.append(segunda)
        procesar_reservas_pendientes()
        assert estado(segunda) == "RECHAZADO_TURNO_OCUPADO"
    finally:
        borrar(*ids)

@pytest.mark.parametrize("datos", [JD26, JD27])
def test_cp15_fuera_de_horario(personal, datos):
    ids = []
    try:
        id_reserva = crear(datos, personal)
        ids.append(id_reserva)
        
        # ⚠️ AQUÍ ESTÁ EL SECRETO: 
        # Forzamos al worker a procesar la cola antes de consultar el estado
        procesar_reservas_pendientes() 
        
        assert estado(id_reserva) == "AGENDADO" if datos == JD26 else "RECHAZADO_TURNO_OCUPADO"
    finally:
        borrar(*ids)

def test_cp17_cancelar_reserva(personal):
    ids = []
    try:
        id_reserva = crear(JD20, personal)
        ids.append(id_reserva)

        r = client.put(f"/reservas/{id_reserva}", json=JD28)
        assert r.status_code == 200, r.text
        assert estado(id_reserva) == "CANCELADO"
    finally:
        borrar(*ids)

def test_cp18_cancelado_no_bloquea_el_horario(personal):
    ids = []
    try:
        primera = crear(JD20, personal)
        ids.append(primera)
        procesar_reservas_pendientes()
        assert estado(primera) == "AGENDADO"

        r = client.put(f"/reservas/{primera}", json=JD28)
        assert r.status_code == 200, r.text

        segunda = crear(JD29, personal)
        ids.append(segunda)
        procesar_reservas_pendientes()
        assert estado(segunda) == "AGENDADO"
    finally:
        borrar(*ids)

def test_cp19_fecha_pasada(personal):
    ids = []
    try:
        id_reserva = crear(JD30, personal)
        ids.append(id_reserva)
        procesar_reservas_pendientes()
        assert estado(id_reserva) == "RECHAZADO_SOLICITUD_NO_VALIDA"
    finally:
        borrar(*ids)