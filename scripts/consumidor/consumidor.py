import os
import json
import time
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
import mysql.connector

# Configuración por variables de entorno
MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC = os.getenv('MQTT_TOPIC', 'turnos/solicitudes')

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '3306'))
DB_NAME = os.getenv('DB_NAME', 'uruturn_db')
DB_USER = os.getenv('DB_USER', 'uruturn_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'uruturn_password')

def obtener_conexion_db():
    """Conecta a MySQL con reintentos durante el arranque del contenedor."""
    while True:
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            return conn
        except mysql.connector.Error:
            print("[WARNING] Esperando a que MySQL esté listo...")
            time.sleep(3)

def validar_y_procesar_turno(datos_msg):
    """
    Valida los datos del turno y lo procesa si es válido, cumpliendo las reglas de negocio de la letra.
    """
    turno = datos_msg.get('turno', {})
    id_personal = turno.get('idPersonal')
    email = turno.get('email_cliente')
    telefono = turno.get('telefono_cliente')
    fecha_str = turno.get('fecha')
    hora_str = turno.get('hora')

    if not all([id_personal, email, fecha_str, hora_str]):
        print("[RECHAZADO] Datos del turno incompletos.")
        return

    # Combinar fecha y hora
    try:
        fecha_hora_solicitada = datetime.strptime(
            f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M"
        )
    except ValueError:
        print("[RECHAZADO] La fecha u hora no tiene un formato valido.")
        return

    conn = obtener_conexion_db()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Obtener datos del personal y del establecimiento
        query_personal = """
                 SELECT p.id_personal, p.activo,
                     TIME_FORMAT(e.horario_apertura, '%H:%i') AS horario_apertura,
                     TIME_FORMAT(e.horario_cierre, '%H:%i') AS horario_cierre
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
        if not personal_info['activo']:
            print(f"[RECHAZADO] El profesional {id_personal} está INACTIVO.")
            return

        # --- REGLA DE NEGOCIO 2: Horarios dentro de la agenda del establecimiento ---
        hora_turno = fecha_hora_solicitada.time()
        apertura = datetime.strptime(personal_info['horario_apertura'], '%H:%M').time()
        cierre = datetime.strptime(personal_info['horario_cierre'], '%H:%M').time()

        hora_fin_turno = (fecha_hora_solicitada + timedelta(minutes=30)).time()
        if not (apertura <= hora_turno and hora_fin_turno <= cierre):
            print(f"[RECHAZADO] Horario {hora_str} fuera de la agenda ({apertura} - {cierre}).")
            return

        # --- REGLA DE NEGOCIO 3: Sin solapamiento (turnos de 30 minutos) ---
        query_solapamiento = """
            SELECT id_reserva FROM reserva
            WHERE id_personal = %s 
              AND fecha_turno = %s
              AND hora_turno = %s
              AND estado_reserva = 'RESERVADO';
        """
        cursor.execute(
            query_solapamiento,
            (id_personal, fecha_hora_solicitada.date(), fecha_hora_solicitada.time()),
        )
        existe_turno = cursor.fetchone()

        if existe_turno:
            print(f"[RECHAZADO] Solapamiento: El profesional {id_personal} ya tiene un turno reservado a las {fecha_hora_solicitada}.")
            return

        # --- SI SUPERA TODAS LAS VALIDACIONES: Guardar en DB ---
        query_insert = """
            INSERT INTO reserva (
                email_solicitante, telefono_solicitante, id_personal,
                fecha_turno, hora_turno, estado_reserva
            ) VALUES (%s, %s, %s, %s, %s, 'RESERVADO');
        """
        cursor.execute(
            query_insert,
            (
                email,
                str(telefono),
                id_personal,
                fecha_hora_solicitada.date(),
                fecha_hora_solicitada.time(),
            ),
        )
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