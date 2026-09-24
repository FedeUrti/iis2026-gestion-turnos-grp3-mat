import os, json, mysql.connector.pooling, paho.mqtt.client as mqtt

# Pool de MySQL (reutiliza conexiones en producción)
db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="uruturn_pool",
    pool_size=10,
    host=os.getenv("DB_HOST", "db"),
    port=int(os.getenv("DB_PORT", "3306")),
    database=os.getenv("DB_NAME", "uruturn_db"),
    user=os.getenv("DB_USER", "uruturn_user"),
    password=os.getenv("DB_PASSWORD", "uruturn_password"),
)

# Cliente MQTT persistente (reutiliza la misma conexión TCP)
mqtt_client = mqtt.Client()
mqtt_client.connect(os.getenv("MQTT_HOST", "mosquitto"), 1883, 60)
mqtt_client.loop_start()

def get_db():
    """Generator que entrega una conexión del pool y la devuelve automáticamente al finalizar."""
    conn = db_pool.get_connection()
    try:
        yield conn
    finally:
        conn.close() # Vuelve al pool, no se destruye

def publicar_mqtt(topic: str, payload: dict):
    """Publica usando el cliente global ya conectado."""
    mqtt_client.publish(topic, json.dumps(payload), qos=1)