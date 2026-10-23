from worker_reservas import procesar_reservas_pendientes
import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)

def estado(id_reserva):
    return client.get(f"/reservas/{id_reserva}").json()["estado_reserva"]

def test_cp19_fecha_pasada(crear_reserva):
    id_r = crear_reserva(fecha="2026-01-01")      # el POST la acepta
    procesar_reservas_pendientes()                # el worker la rechaza
    assert estado(id_r) == "RECHAZADO_SOLICITUD_NO_VALIDA"

def test_cp14_turno_ocupado(crear_reserva):
    a = crear_reserva()
    procesar_reservas_pendientes()
    assert estado(a) == "AGENDADO"

    b = crear_reserva()                           # mismo profesional, fecha y hora
    procesar_reservas_pendientes()
    assert estado(b) == "RECHAZADO_TURNO_OCUPADO"