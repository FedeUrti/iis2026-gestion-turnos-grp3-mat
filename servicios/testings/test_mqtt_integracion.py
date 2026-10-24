import json
import os
import secrets
import time
import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from paho.mqtt import publish

from main import app


client = TestClient(app)
MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "turnos/solicitudes")


def esperar_estado_reserva(id_reserva, timeout=15):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        respuesta = client.get(f"/reservas/{id_reserva}")
        if respuesta.status_code == 200:
            return respuesta.json()["estado_reserva"]
        assert respuesta.status_code == 404, respuesta.text
        time.sleep(0.2)

    pytest.fail(f"La reserva {id_reserva} no fue procesada por MQTT en {timeout}s.")


def publicar_solicitud(turno):
    publish.single(
        MQTT_TOPIC,
        payload=json.dumps({"turno": turno}),
        qos=1,
        hostname=MQTT_HOST,
        port=MQTT_PORT,
    )


def test_cp27_turno_ocupado_a_traves_de_mqtt(personal):
    fecha_turno = (date.today() + timedelta(days=7)).isoformat()
    email_base = f"cp27.{uuid.uuid4().hex[:12]}@example.com"
    id_primera = secrets.randbelow(900000) + 100000
    id_segunda = secrets.randbelow(900000) + 100000
    while id_segunda == id_primera:
        id_segunda = secrets.randbelow(900000) + 100000

    turno_base = {
        "idEstablecimiento": personal["id_establecimiento"],
        "idPersonal": personal["id_personal"],
        "telefono_cliente": "099111111",
        "fecha": fecha_turno,
        "hora": "10:00",
    }
    primera = {
        **turno_base,
        "id": id_primera,
        "email_cliente": f"primero.{email_base}",
        "nombre_cliente": "Primer turno CP27",
    }
    duplicada = {
        **turno_base,
        "id": id_segunda,
        "email_cliente": f"segundo.{email_base}",
        "nombre_cliente": "Segundo turno CP27",
    }

    try:
        publicar_solicitud(primera)
        assert esperar_estado_reserva(id_primera) == "RESERVADO"

        publicar_solicitud(duplicada)
        assert (
            esperar_estado_reserva(id_segunda)
            == "RECHAZADO_TURNO_OCUPADO"
        )
    finally:
        client.delete(f"/reservas/{id_primera}")
        client.delete(f"/reservas/{id_segunda}")
