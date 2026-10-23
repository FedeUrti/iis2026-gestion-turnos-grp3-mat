from datetime import date
from unittest.mock import MagicMock, patch
import mysql.connector
import pytest
from worker_facturas import facturar_turnos_atendidos

def test_cp32_rollback_ante_error():
    db = MagicMock()
    cursor_lectura = MagicMock()
    cursor_lectura.fetchall.return_value = [{
        "id_reserva": 207, "email_solicitante": "cliente.error@shimail.com",
        "fecha_turno": date(2026, 10, 25), "id_personal": 1,
        "nombre": "Ana", "apellido": "Gomez",
        "especialidad": "General", "costo_consulta": 2000,
    }]
    cursor_escritura = MagicMock()
    cursor_escritura.execute.side_effect = mysql.connector.Error("falla simulada")
    db.cursor.side_effect = [cursor_lectura, cursor_escritura]

    with patch("worker_facturas.db_pool") as pool:
        pool.get_connection.return_value = db
        with pytest.raises(mysql.connector.Error):
            facturar_turnos_atendidos()

    db.rollback.assert_called_once()
    db.commit.assert_not_called()