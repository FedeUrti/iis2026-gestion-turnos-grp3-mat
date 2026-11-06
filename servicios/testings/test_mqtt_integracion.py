import json
import os
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


def esperar_reserva(email, timeout=15):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        respuesta = client.get("/reservas")
        assert respuesta.status_code == 200, respuesta.text
        for reserva in respuesta.json():
            if reserva["email_solicitante"] == email:
                return reserva
        time.sleep(0.2)

    pytest.fail(f"La reserva de {email} no llegó a la API en {timeout}s.")


def publicar_solicitud(turno):
    publish.single(
        MQTT_TOPIC,
        payload=json.dumps({"turno": turno}),
        qos=1,
        hostname=MQTT_HOST,
        port=MQTT_PORT,
    )


def test_solicitudes_mqtt_se_registran_a_traves_de_la_api(personal):
    fecha_turno = (date.today() + timedelta(days=7)).isoformat()
    email_base = f"cp27.{uuid.uuid4().hex[:12]}@example.com"
    email_primera = f"primero.{email_base}"
    email_segunda = f"segundo.{email_base}"

    turno_base = {
        "idEstablecimiento": personal["id_establecimiento"],
        "idPersonal": personal["id_personal"],
        "telefono_cliente": "099111111",
        "fecha": fecha_turno,
        "hora": "10:00",
    }
    primera = {
        **turno_base,
        "id": 123456,
        "email_cliente": email_primera,
        "nombre_cliente": "Primer turno CP27",
    }
    duplicada = {
        **turno_base,
        "id": 123457,
        "email_cliente": email_segunda,
        "nombre_cliente": "Segundo turno CP27",
    }
    ids_reservas = []

    try:
        publicar_solicitud(primera)
        reserva_primera = esperar_reserva(email_primera)
        ids_reservas.append(reserva_primera["id_reserva"])
        assert reserva_primera["nombre"] == "Primer turno CP27"

        publicar_solicitud(duplicada)
        reserva_segunda = esperar_reserva(email_segunda)
        ids_reservas.append(reserva_segunda["id_reserva"])
        assert reserva_segunda["nombre"] == "Segundo turno CP27"
        assert reserva_primera["id_reserva"] != reserva_segunda["id_reserva"]
    finally:
        for id_reserva in ids_reservas:
            client.delete(f"/reservas/{id_reserva}")
