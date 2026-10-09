from datetime import datetime, timedelta, timezone

import mysql.connector

from database import db_pool

URUGUAY_TZ = timezone(timedelta(hours=-3))


def _inicio_minuto_actual():
    ahora = datetime.now(URUGUAY_TZ).replace(tzinfo=None)
    return ahora.replace(second=0, microsecond=0)


def _combinar_fecha_hora(fecha, hora):
    if isinstance(hora, timedelta):
        hora = (datetime.min + hora).time()
    return datetime.combine(fecha, hora)


def procesar_reservas_mqtt():
    """Valida y agenda los turnos que el consumidor MQTT guardó como RESERVADO."""
    db = db_pool.get_connection()
    procesadas = 0
    try:
        cursor = db.cursor(dictionary=True)
        # El consumidor guarda primero el turno; aquí se valida y agenda.
        cursor.execute(
            """
            SELECT id_reserva, id_establecimiento, id_personal,
                   fecha_turno, hora_turno
            FROM reserva
            WHERE estado_reserva = 'RESERVADO'
            ORDER BY fecha_reservado, id_reserva
            """
        )
        reservas = cursor.fetchall()
        cursor.close()

        for reserva in reservas:
            cursor = db.cursor(dictionary=True)
            try:
                # No se pueden agendar turnos cuya fecha ya pasó.
                fecha_hora_turno = _combinar_fecha_hora(
                    reserva["fecha_turno"], reserva["hora_turno"]
                )
                if fecha_hora_turno < _inicio_minuto_actual():
                    estado = "RECHAZADO_SOLICITUD_NO_VALIDA"
                else:
                    cursor.execute(
                        """
                        SELECT p.id_personal
                        FROM establecimiento e
                        JOIN personal p ON p.id_establecimiento = e.id_establecimiento
                        WHERE e.id_establecimiento = %s
                          AND p.id_personal = %s
                          AND p.activo = TRUE
                        """,
                        (reserva["id_establecimiento"], reserva["id_personal"]),
                    )
                    personal = cursor.fetchone()
                    if not personal:
                        estado = "RECHAZADO_SOLICITUD_NO_VALIDA"
                    else:
                        # Un horario solo está ocupado por reservas activas.
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
                                reserva["id_personal"],
                                reserva["fecha_turno"],
                                reserva["hora_turno"],
                                reserva["id_reserva"],
                            ),
                        )
                        estado = (
                            "RECHAZADO_TURNO_OCUPADO"
                            if cursor.fetchone()
                            else "AGENDADO"
                        )

                # Guarda el resultado solo si el turno aún está en RESERVADO.
                cursor.execute(
                    """
                    UPDATE reserva
                    SET estado_reserva = %s
                    WHERE id_reserva = %s AND estado_reserva = 'RESERVADO'
                    """,
                    (estado, reserva["id_reserva"]),
                )
                db.commit()
                procesadas += cursor.rowcount
            except mysql.connector.Error:
                # Revierte cambios incompletos y deja que el error se propague.
                db.rollback()
                raise
            finally:
                cursor.close()

        return procesadas
    finally:
        db.close()


def procesar_reservas_pendientes():
    """Valida reservas pendientes y actualiza turnos que ya fueron atendidos."""
    db = db_pool.get_connection()
    procesadas = 0
    try:
        cursor = db.cursor(dictionary=True)
        # Las solicitudes REST se guardan como reservas pendientes.
        cursor.execute(
            """
            SELECT id_reserva, email_solicitante, telefono_solicitante,
                   id_establecimiento, id_personal, fecha_turno, hora_turno
            FROM reserva
            WHERE estado_reserva = 'PENDIENTE'
            ORDER BY fecha_reservado, id_reserva
            """
        )
        reservas_pendientes = cursor.fetchall()
        cursor.close()

        for reserva in reservas_pendientes:
            cursor = db.cursor(dictionary=True)
            try:
                # Verifica fecha, establecimiento y profesional antes de agendar.
                fecha_hora_turno = _combinar_fecha_hora(
                    reserva["fecha_turno"], reserva["hora_turno"]
                )
                if fecha_hora_turno < _inicio_minuto_actual():
                    estado = "RECHAZADO_SOLICITUD_NO_VALIDA"
                else:
                    cursor.execute(
                        """
                        SELECT p.id_personal, p.activo
                        FROM establecimiento e
                        JOIN personal p ON p.id_establecimiento = e.id_establecimiento
                        WHERE e.id_establecimiento = %s AND p.id_personal = %s
                        """,
                        (reserva["id_establecimiento"], reserva["id_personal"]),
                    )
                    personal = cursor.fetchone()
                    if not personal or not personal["activo"]:
                        estado = "RECHAZADO_SOLICITUD_NO_VALIDA"
                    else:
                        cursor.execute(
                            """
                            SELECT id_reserva
                            FROM reserva
                            WHERE id_personal = %s
                              AND fecha_turno = %s
                              AND hora_turno = %s
                              AND estado_reserva NOT IN (
                                  'CANCELADO',
                                  'PENDIENTE',
                                  'RECHAZADO_SOLICITUD_NO_VALIDA',
                                  'RECHAZADO_TURNO_OCUPADO'
                              )
                            LIMIT 1
                            """,
                            (
                                reserva["id_personal"],
                                reserva["fecha_turno"],
                                reserva["hora_turno"],
                            ),
                        )
                        if cursor.fetchone():
                            estado = "RECHAZADO_TURNO_OCUPADO"
                        else:
                            estado = "AGENDADO"

                # Actualiza el estado en la misma fila, incluso si fue rechazada.
                cursor.execute(
                    """
                    UPDATE reserva
                    SET estado_reserva = %s
                    WHERE id_reserva = %s AND estado_reserva = 'PENDIENTE'
                    """,
                    (estado, reserva["id_reserva"]),
                )
                db.commit()
                procesadas += cursor.rowcount
            except mysql.connector.Error:
                db.rollback()
                raise
            finally:
                cursor.close()

        cursor = db.cursor()
        # Espera al siguiente minuto antes de marcar un turno como atendido.
        cursor.execute(
            """
            UPDATE reserva
            SET estado_reserva = 'ATENDIDO'
            WHERE estado_reserva = 'AGENDADO'
              AND TIMESTAMP(fecha_turno, hora_turno) < %s
            """,
            (_inicio_minuto_actual(),),
        )
        procesadas += cursor.rowcount
        db.commit()
        cursor.close()
        return procesadas
    finally:
        db.close()
