import json
import os
import time

import paho.mqtt.client as mqtt
import requests

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "turnos/solicitudes")
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "uruturn-consumidor")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_TIMEOUT_SECONDS = float(os.getenv("API_TIMEOUT_SECONDS", "5"))
RECONNECT_SECONDS = float(os.getenv("RECONNECT_SECONDS", "3"))


def _acknowledge(client, msg):
    if msg.qos > 0:
        resultado = client.ack(msg.mid, msg.qos)
        if resultado != mqtt.MQTT_ERR_SUCCESS:
            print(f"[ERROR] No se pudo confirmar el mensaje MQTT {msg.mid}.")


def on_message(client, userdata, msg):
    """Traduce el mensaje MQTT al contrato REST genérico de reservas."""
    try:
        datos_msg = json.loads(msg.payload.decode("utf-8"))
        turno = datos_msg["turno"]
        payload = {
            "nombre": turno.get("nombre_cliente", ""),
            "email_solicitante": turno.get("email_cliente"),
            "telefono_solicitante": str(turno.get("telefono_cliente", "")),
            "id_establecimiento": turno.get("idEstablecimiento"),
            "id_personal": turno.get("idPersonal"),
            "fecha_turno": turno.get("fecha"),
            "hora_turno": turno.get("hora"),
        }
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("[ERROR] Mensaje MQTT descartado: JSON inválido.")
        _acknowledge(client, msg)
        return
    except (KeyError, AttributeError, TypeError):
        print("[ERROR] Mensaje MQTT descartado: falta el objeto 'turno'.")
        _acknowledge(client, msg)
        return

    try:
        respuesta = requests.post(
            f"{API_BASE_URL}/reservas",
            json=payload,
            timeout=API_TIMEOUT_SECONDS,
        )
    except requests.RequestException as err:
        print(f"[ERROR] API no disponible; se reintentará el mensaje: {err}")
        client.disconnect()
        return

    if respuesta.status_code == 202:
        print(f"[PROCESADO] API aceptó la solicitud: {respuesta.text}")
        _acknowledge(client, msg)
    elif respuesta.status_code == 409:
        print(
            "[ERROR] La API informó un conflicto; se reintentará el mensaje: "
            f"{respuesta.text}"
        )
        client.disconnect()
    elif 400 <= respuesta.status_code < 500:
        print(f"[RECHAZADO] API descartó el mensaje: {respuesta.text}")
        _acknowledge(client, msg)
    else:
        print(
            "[ERROR] La API no pudo procesar el mensaje "
            f"(HTTP {respuesta.status_code}); se reintentará."
        )
        client.disconnect()


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"[ERROR] Conexión MQTT rechazada: {reason_code}.")
        return

    resultado, _ = client.subscribe(MQTT_TOPIC, qos=1)
    if resultado != mqtt.MQTT_ERR_SUCCESS:
        print(f"[ERROR] No se pudo suscribir al tópico {MQTT_TOPIC}.")
        client.disconnect()
        return
    print(f"[INFO] Suscrito al tópico '{MQTT_TOPIC}'.")


def main():
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
        clean_session=False,
        manual_ack=True,
    )
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        while True:
            try:
                print(f"Conectando a Mosquitto en {MQTT_HOST}:{MQTT_PORT}...")
                client.connect(MQTT_HOST, MQTT_PORT, 60)
                client.loop_forever()
            except (OSError, mqtt.MQTTException) as err:
                print(f"[WARNING] MQTT no disponible: {err}")
            time.sleep(RECONNECT_SECONDS)
    except KeyboardInterrupt:
        print("\n[INFO] Deteniendo consumidor...")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
