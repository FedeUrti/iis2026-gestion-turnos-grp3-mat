from datetime import date, time, timedelta

import pytest
from fastapi.testclient import TestClient
from main import app
from worker_reservas import (
    _horario_dentro_de_apertura,
    procesar_reservas_pendientes,
)


client = TestClient(app)


@pytest.mark.parametrize(
    "hora, esperado",
    [
        ("08:00:00", True),
        ("17:30:00", True),
        ("07:59:00", False),
        ("17:31:00", False),
        ("22:00:00", False),
    ],
)
def test_horario_dentro_de_apertura(hora, esperado):
    assert _horario_dentro_de_apertura(
        date(2026, 11, 20),
        time.fromisoformat(hora),
        time(8, 0),
        time(18, 0),
    ) is esperado


def test_horario_mysql_timedelta():
    assert _horario_dentro_de_apertura(
        date(2026, 11, 20),
        timedelta(hours=17, minutes=30),
        timedelta(hours=8),
        timedelta(hours=18),
    )


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