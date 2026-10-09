import os
import time
import json
import random
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import mysql.connector

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "turnos/solicitudes")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "uruturn_db")
DB_USER = os.getenv("DB_USER", "uruturn_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "uruturn_password")


def obtener_datos_generacion():
    """Obtiene profesionales válidos e IDs ya ocupados para nuevos eventos."""
    while True:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
            )
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id_establecimiento, id_personal
                    FROM personal
                    WHERE activo = TRUE
                    ORDER BY id_establecimiento, id_personal
                    """
                )
                profesionales = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT id_reserva FROM reserva
                    """
                )
                ids_ocupados = {row[0] for row in cursor.fetchall()}
                cursor.close()
            finally:
                conn.close()

            if not profesionales:
                raise RuntimeError("No hay profesionales activos para generar turnos.")
            return profesionales, ids_ocupados
        except mysql.connector.Error as err:
            print(f"[WARNING] Esperando a que MySQL esté listo: {err}")
            time.sleep(3)


def generador_turno_random():
    """
    Crea un diccionar Python respetando la estructura JSON del Anexo.
    Está separada en una función para poder ser llamada desde otro script.
    """
    profesionales, ids_ocupados = obtener_datos_generacion()
    id_turno = random.randint(100_000, 2_000_000_000)
    while id_turno in ids_ocupados:
        id_turno = random.randint(100_000, 2_000_000_000)
    id_establecimiento, id_personal = random.choice(profesionales)
    telefonos = [111111111, 222222222, 333333333, 444444444]
    emails = ["cliente1@gmail.com", "cliente2@yahoo.com", "cliente3@outlook.com"]
    dias_futuros = random.randint(1,7)
    fecha_turno = datetime.now() + timedelta(days = dias_futuros)

    hora_aleatoria = f"{random.randint(9, 16):02d}:{random.choice(('00', '30'))}"
    return {
        "status":"turno_creado",
        "fechaHora": datetime.now().isoformat(timespec='seconds'),
        "turno":{
            "id": id_turno,
            "email_cliente": random.choice(emails),
            "telefono_cliente": random.choice(telefonos),
            "idEstablecimiento": id_establecimiento,
            "idPersonal": id_personal,
            "fecha": fecha_turno.strftime("%Y-%m-%d"),
            "hora": hora_aleatoria
        }
    }

def main():
    #conectarse a MQTT
    client = mqtt.Client()
    print(f"Conectando al broker MQTT en {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    print (f"Generador de turnos activo. Publicando en '{MQTT_TOPIC}' cada 10 segundos...")
    try:
        #Bucle enviando datos cada 10s
        while True:
            datos_turno = generador_turno_random()
            payload_json = json.dumps(datos_turno)
            #Publicar en el topic MQTT
            client.publish(MQTT_TOPIC, payload_json, qos=1)
            print(f"[ENVIADO] {payload_json}")
            #esperar 10 segundos
            time.sleep(10)

    except KeyboardInterrupt:
            print("\n[INFO] Interrupción detectada por el usuario.")

    finally:
            # Este bloque SIEMPRE se ejecuta al salir del try/while
            client.loop_stop()
            client.disconnect()
            print("Desconectado del broker MQTT. Saliendo del programa...")


if __name__ == "__main__":
    main()

