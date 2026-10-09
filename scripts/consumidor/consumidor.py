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
    id_reserva = turno.get('id')
    id_establecimiento = turno.get('idEstablecimiento')
    id_personal = turno.get('idPersonal')
    email = turno.get('email_cliente')
    telefono = turno.get('telefono_cliente')
    fecha_str = turno.get('fecha')
    hora_str = turno.get('hora')

    if not all([
        id_reserva, id_establecimiento, id_personal, email,
        telefono, fecha_str, hora_str
    ]):
        print("[RECHAZADO] Datos del turno incompletos.")
        return

    try:
        id_reserva = int(id_reserva)
        id_establecimiento = int(id_establecimiento)
        id_personal = int(id_personal)
        if min(id_reserva, id_establecimiento, id_personal) < 1:
            raise ValueError("Los identificadores deben ser positivos.")
        fecha_hora_solicitada = datetime.strptime(
            f"{fecha_str} {hora_str}", "%Y-%m-%d %H:%M"
        )
    except ValueError:
        print("[RECHAZADO] La fecha u hora no tiene un formato valido.")
        return

    conn = obtener_conexion_db()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id_reserva FROM reserva WHERE id_reserva = %s
            """,
            (id_reserva,),
        )
        if cursor.fetchone():
            print(f"[IGNORADO] El turno con ID {id_reserva} ya fue recibido.")
            return

        cursor.execute(
            """
            SELECT e.id_establecimiento,
                   p.id_personal,
                   p.id_establecimiento AS id_establecimiento_personal,
                   p.activo,
                   TIME_FORMAT(e.horario_apertura, '%H:%i') AS horario_apertura,
                   TIME_FORMAT(e.horario_cierre, '%H:%i') AS horario_cierre
            FROM establecimiento e
            LEFT JOIN personal p ON p.id_personal = %s
            WHERE e.id_establecimiento = %s
            """,
            (id_personal, id_establecimiento),
        )
        datos_validacion = cursor.fetchone()
        if not datos_validacion or not datos_validacion["id_personal"]:
            print("[RECHAZADO] No existe el establecimiento o profesional indicado.")
            return

        estado_reserva = "RESERVADO"
        if (
            datos_validacion["id_establecimiento_personal"] != id_establecimiento
            or not datos_validacion["activo"]
            or fecha_hora_solicitada.date() < datetime.now().date()
        ):
            estado_reserva = "RECHAZADO_SOLICITUD_NO_VALIDA"
        else:
            apertura = datetime.strptime(
                datos_validacion["horario_apertura"], "%H:%M"
            ).time()
            cierre = datetime.strptime(
                datos_validacion["horario_cierre"], "%H:%M"
            ).time()
            fin_turno = fecha_hora_solicitada + timedelta(minutes=30)
            if not (
                apertura <= fecha_hora_solicitada.time()
                and fin_turno.time() <= cierre
                and fin_turno.date() == fecha_hora_solicitada.date()
            ):
                estado_reserva = "RECHAZADO_SOLICITUD_NO_VALIDA"
            else:
                cursor.execute(
                    """
                    SELECT id_reserva
                    FROM reserva
                    WHERE id_personal = %s
                      AND fecha_turno = %s
                      AND hora_turno = %s
                      AND id_reserva != %s
                      AND estado_reserva NOT IN (
                          'CANCELADO',
                          'RECHAZADO_SOLICITUD_NO_VALIDA',
                          'RECHAZADO_TURNO_OCUPADO'
                      )
                    LIMIT 1
                    """,
                    (
                        id_personal,
                        fecha_hora_solicitada.date(),
                        fecha_hora_solicitada.time(),
                        id_reserva,
                    ),
                )
                if cursor.fetchone():
                    estado_reserva = "RECHAZADO_TURNO_OCUPADO"

        cursor.execute(
            """
            INSERT INTO cliente (email, telefono)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE telefono = VALUES(telefono)
            """,
            (email, str(telefono)),
        )
        cursor.execute(
            """
            INSERT INTO reserva (
                id_reserva, email_solicitante, telefono_solicitante,
                id_establecimiento, id_personal, fecha_turno,
                hora_turno, estado_reserva
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                id_reserva,
                email,
                str(telefono),
                id_establecimiento,
                id_personal,
                fecha_hora_solicitada.date(),
                fecha_hora_solicitada.time(),
                estado_reserva,
            ),
        )
        conn.commit()
        print(
            f"[PERSISTIDO] Turno {id_reserva}: {estado_reserva}, "
            f"establecimiento {id_establecimiento}, profesional {id_personal}."
        )
    except mysql.connector.Error as e:
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