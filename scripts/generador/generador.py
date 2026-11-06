import json
import os
import random
import time
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt
import requests

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "turnos/solicitudes")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "5"))
API_RETRY_SECONDS = float(os.getenv("API_RETRY_SECONDS", "3"))
MQTT_RETRY_SECONDS = float(os.getenv("MQTT_RETRY_SECONDS", "3"))
PUBLICATION_INTERVAL_SECONDS = float(
    os.getenv("PUBLICATION_INTERVAL_SECONDS", "10")
)


def obtener_datos_generacion():
    """Obtiene profesionales activos a través de la API."""
    while True:
        try:
            respuesta_personal = requests.get(
                f"{API_BASE_URL}/personal",
                timeout=API_TIMEOUT_SECONDS,
            )
            respuesta_personal.raise_for_status()

            profesionales = [
                (persona["id_establecimiento"], persona["id_personal"])
                for persona in respuesta_personal.json()
                if persona["activo"]
            ]
            if not profesionales:
                raise RuntimeError(
                    "La API no tiene profesionales activos para generar turnos."
                )
            return profesionales
        except requests.RequestException as err:
            print(f"[WARNING] API no disponible; se reintentará: {err}")
            time.sleep(API_RETRY_SECONDS)


def generador_turno_random():
    """Crea un mensaje con el formato MQTT acordado."""
    profesionales = obtener_datos_generacion()
    id_turno = random.randint(100_000, 2_000_000_000)

    id_establecimiento, id_personal = random.choice(profesionales)
    telefonos = [111111111, 222222222, 333333333, 444444444]
    emails = ["cliente1@gmail.com", "cliente2@yahoo.com", "cliente3@outlook.com"]
    nombres = ["Ana", "Bruno", "Carla", "Diego", "Lucia", "Mateo"]
    fecha_turno = datetime.now() + timedelta(days=random.randint(1, 7))
    hora_aleatoria = f"{random.randint(9, 16):02d}:{random.choice(('00', '30'))}"

    return {
        "status": "turno_creado",
        "fechaHora": datetime.now().isoformat(timespec="seconds"),
        "turno": {
            "id": id_turno,
            "email_cliente": random.choice(emails),
            "nombre_cliente": random.choice(nombres),
            "telefono_cliente": random.choice(telefonos),
            "idEstablecimiento": id_establecimiento,
            "idPersonal": id_personal,
            "fecha": fecha_turno.strftime("%Y-%m-%d"),
            "hora": hora_aleatoria,
        },
    }


def conectar_mqtt(client):
    while True:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            return
        except OSError as err:
            print(f"[WARNING] Mosquitto no disponible; se reintentará: {err}")
            time.sleep(MQTT_RETRY_SECONDS)


def main():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2
    )
    conectar_mqtt(client)
    client.loop_start()
    print(
        f"Generador activo. Publicando en '{MQTT_TOPIC}' cada "
        f"{PUBLICATION_INTERVAL_SECONDS:g} segundos..."
    )
    try:
        while True:
            datos_turno = generador_turno_random()
            payload_json = json.dumps(datos_turno)
            resultado = client.publish(MQTT_TOPIC, payload_json, qos=1)
            resultado.wait_for_publish()
            if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(
                    f"No se pudo publicar el turno: código MQTT {resultado.rc}."
                )
            print(f"[ENVIADO] {payload_json}")
            time.sleep(PUBLICATION_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupción detectada por el usuario.")
    finally:
        client.loop_stop()
        client.disconnect()
        print("Desconectado de Mosquitto.")


if __name__ == "__main__":
    main()
