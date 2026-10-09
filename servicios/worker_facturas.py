import mysql.connector

from database import db_pool


def facturar_turnos_atendidos():
    """Agrupa turnos atendidos por cliente y mes y los agrega como ítems."""
    db = db_pool.get_connection()
    facturados = 0
    try:
        cursor = db.cursor(dictionary=True)
        # Solo se procesan turnos atendidos que todavía no tienen factura.
        cursor.execute(
            """
            SELECT r.id_reserva, r.email_solicitante, r.fecha_turno,
                   p.id_personal, p.nombre, p.apellido, p.especialidad,
                   p.costo_consulta
            FROM reserva r
            JOIN personal p ON p.id_personal = r.id_personal
            WHERE r.estado_reserva = 'ATENDIDO'
            ORDER BY r.email_solicitante, r.fecha_turno, r.id_reserva
            """
        )
        turnos = cursor.fetchall()
        cursor.close()

        for turno in turnos:
            cursor = db.cursor()
            try:
                # La factura se agrupa por cliente y mes del turno.
                periodo = turno["fecha_turno"].strftime("%Y-%m")
                nombre_profesional = f'{turno["nombre"]} {turno["apellido"]}'.strip()
                precio = turno["costo_consulta"] or 0
                cursor.execute(
                    """
                    INSERT INTO factura (email_cliente, periodo)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        id_factura = LAST_INSERT_ID(id_factura)
                    """,
                    (
                        turno["email_solicitante"],
                        periodo,
                    ),
                )
                id_factura = cursor.lastrowid

                # LAST_INSERT_ID permite reutilizar la factura si ya existía.
                cursor.execute(
                    """
                    INSERT INTO factura_item (
                        id_factura, id_reserva, id_personal,
                        nombre_profesional, especialidad, descripcion,
                        precio_unitario
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE id_item = LAST_INSERT_ID(id_item)
                    """,
                    (
                        id_factura,
                        turno["id_reserva"],
                        turno["id_personal"],
                        nombre_profesional,
                        turno["especialidad"] or "General",
                        f"Consulta de {turno['especialidad'] or 'General'}",
                        precio,
                    ),
                )
                cursor.execute(
                    """
                    UPDATE factura
                    SET total = (
                        SELECT COALESCE(SUM(precio_unitario), 0)
                        FROM factura_item
                        WHERE id_factura = %s
                    )
                    WHERE id_factura = %s
                    """,
                    (id_factura, id_factura),
                )
                # El turno pasa a facturado dentro de la misma transacción.
                cursor.execute(
                    """
                    UPDATE reserva
                    SET estado_reserva = 'FACTURADO'
                    WHERE id_reserva = %s AND estado_reserva = 'ATENDIDO'
                    """,
                    (turno["id_reserva"],),
                )
                facturados += cursor.rowcount
                # Confirma juntos el ítem, el total y el nuevo estado del turno.
                db.commit()
            except mysql.connector.Error:
                # Evita dejar una factura o un turno parcialmente actualizado.
                db.rollback()
                raise
            finally:
                cursor.close()

        return facturados
    finally:
        db.close()
