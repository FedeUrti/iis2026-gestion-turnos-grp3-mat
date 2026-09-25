import os
import json
import mysql.connector.pooling
import paho.mqtt.client as mqtt

# Pool de MySQL (se reutilizan conexiones)
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="uruturn_pool",
    pool_size=10,
    host=os.getenv("DB_HOST", "db"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "uruturn_db"),
    user=os.getenv("DB_USER", "uruturn_user"),
    password=os.getenv("DB_PASSWORD", "uruturn_password"),
)

# Cliente MQTT global
mqtt_client = mqtt.Client()

def conectar_mqtt():
    """Inicia la conexión MQTT al arrancar FastAPI."""
    try:
        mqtt_client.connect(
            os.getenv("MQTT_HOST", "mosquitto"),
            int(os.getenv("MQTT_PORT", "1883")),
            keepalive=60
        )
        mqtt_client.loop_start()
    except Exception as e:
        print(f"[MQTT] Advertencia: No se pudo conectar a Mosquitto: {e}")

def desconectar_mqtt():
    """Cierra la conexión MQTT al apagar FastAPI."""
    try:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    except Exception:
        pass

def get_db():
    """Inyección de dependencia para endpoints."""
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()

def publicar_mqtt(topic: str, payload: dict):
    """Función para publicar mensajes."""
    mqtt_client.publish(topic, json.dumps(payload), qos=1)