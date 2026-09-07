import os
import json
import time
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import RealDictCursor

# Configuración por variables de entorno
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'turnos/solicitudes')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'uruturn_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

def obtener_conexion_db():
    """Conecta a la BD  con reintentos para soportar la arrancada del contenedor."""
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            return conn
        except psycopg2.OperationalError as e:
            print("[WARNING] Esperando a que PostgreSQL esté listo...")
            time.sleep(3)

def validar_y_procesar_turno(datos_msg):
    """
    Valida los datos del turno y lo procesa si es válido, cumpliendo las reglas de negocio de la letra.
    """
    turno = datos_msg.get('turno', {})
    id_personal = turno.get('idPersonal')
    email = turno.get('email_cliente')
    telefono = str(turno.get('telefono_cliente'))
    fecha_str = turno.get('fecha')
    hora_str = turno.get('hora')

    if not all([id_personal, email, fecha_str, hora_str]):
        print("[RECHAZADO] Datos del turno incompletos.")
        return

    # Combinar fecha y hora
    fecha_hora_solicitada = datetime.strptime(f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M")

    conn = obtener_conexion_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Obtener datos del personal y del establecimiento
        query_personal = """
            SELECT p.id_personal, p.estado_personal, e.horario_apertura, e.horario_cierre
            FROM personal p
            JOIN establecimiento e ON p.id_establecimiento = e.id_establecimiento
            WHERE p.id_personal = %s;
        """
        cursor.execute(query_personal, (id_personal,))
        personal_info = cursor.fetchone()

        if not personal_info:
            print(f"[RECHAZADO] No existe el profesional con ID {id_personal}.")
            return

        # --- REGLA DE NEGOCIO 1: Profesional Activo ---
        if personal_info['estado_personal'].lower() != 'activo':
            print(f"[RECHAZADO] El profesional {id_personal} está INACTIVO.")
            return

        # --- REGLA DE NEGOCIO 2: Horarios dentro de la agenda del establecimiento ---
        hora_turno = fecha_hora_solicitada.time()
        apertura = personal_info['horario_apertura']
        cierre = personal_info['horario_cierre']

        if not (apertura <= hora_turno <= cierre):
            print(f"[RECHAZADO] Horario {hora_str} fuera de la agenda ({apertura} - {cierre}).")
            return

        # --- REGLA DE NEGOCIO 3: Sin solapamiento (turnos de 30 minutos) ---
        query_solapamiento = """
            SELECT id_reserva FROM reserva
            WHERE id_personal = %s 
              AND fecha_hora_turno = %s 
              AND estado_reserva = 'Reservado';
        """
        cursor.execute(query_solapamiento, (id_personal, fecha_hora_solicitada))
        existe_turno = cursor.fetchone()

        if existe_turno:
            print(f"[RECHAZADO] Solapamiento: El profesional {id_personal} ya tiene un turno reservado a las {fecha_hora_solicitada}.")
            return

        # --- SI SUPERA TODAS LAS VALIDACIONES: Guardar en DB ---
        query_insert = """
            INSERT INTO reserva (fecha_reserva, email_solicitante, telefono_solicitante, fecha_hora_turno, estado_reserva, id_personal)
            VALUES (NOW(), %s, %s, %s, 'Reservado', %s);
        """
        cursor.execute(query_insert, (email, telefono, fecha_hora_solicitada, id_personal))
        conn.commit()

        print(f"[ACEPTADO Y PERSISTIDO] Turno guardado exitosamente para {email} con el profesional {id_personal} el {fecha_hora_solicitada}.")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR DB] Error al procesar reserva: {e}")
    finally:
        cursor.close()
        conn.close()

def on_message(client, userdata, msg):
    """Callback que se dispara al recibir un mensaje por MQTT."""
    try:
        contenido = msg.payload.decode('utf-8')
        datos_msg = json.loads(contenido)
        print(f"\n[MENSAJE RECIBIDO] Tópico: {msg.topic}")
        validar_y_procesar_turno(datos_msg)
    except json.JSONDecodeError:
        print("[ERROR] Formato de JSON inválido.")
    except Exception as e:
        print(f"[ERROR UNEXPECTED]: {e}")

def main():
    client = mqtt.Client()
    client.on_message = on_message

    print(f"Conectando al broker MQTT en {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    
    # Suscribirse al tópico
    client.subscribe(MQTT_TOPIC)
    print(f"Consumidor listo. Suscrito al tópico '{MQTT_TOPIC}'...")

    try:
        # Escuchar continuamente eventos de MQTT
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Deteniendo consumidor...")
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()