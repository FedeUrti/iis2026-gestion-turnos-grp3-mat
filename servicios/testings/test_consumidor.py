"""Tests del consumidor MQTT (CP20 a CP26).

No necesitan broker ni base de datos real: se reemplaza obtener_conexion_db()
por una conexión falsa (MagicMock) y después se inspecciona qué intentó
ejecutar el consumidor (qué INSERT hizo y con qué estado).
"""
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import consumidor

# Una fecha siempre futura, para que el test no venza con el tiempo.
FECHA_FUTURA = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Ayudas (funciones comunes, NO son fixtures)
# ---------------------------------------------------------------------------
def turno_valido(**cambios):
    """Mensaje MQTT válido con el esquema REAL del consumidor.

    Ojo: es distinto al de la API REST (idEstablecimiento, email_cliente,
    fecha "AAAA-MM-DD" y hora "HH:MM", todo dentro de la clave "turno").
    """
    turno = {
        "id": 123456,
        "idEstablecimiento": 1,
        "idPersonal": 4,
        "email_cliente": "cliente@example.com",
        "nombre_cliente": "Cliente Test",
        "telefono_cliente": "099111111",
        "fecha": FECHA_FUTURA,
        "hora": "10:00",
    }
    turno.update(cambios)
    return {"turno": turno}


def datos_bd(**cambios):
    """Lo que devolvería MySQL para un establecimiento y profesional válidos."""
    datos = {
        "id_establecimiento": 1,
        "id_personal": 4,
        "id_establecimiento_personal": 1,
        "activo": 1,
        "horario_apertura": "08:00",
        "horario_cierre": "18:00",
    }
    datos.update(cambios)
    return datos


def procesar(datos_msg, *respuestas_fetchone):
    """Ejecuta validar_y_procesar_turno con una BD falsa.

    `respuestas_fetchone` son, en orden, lo que devuelve cada fetchone():
      1) ¿ya existe ese id de reserva?        -> None = no existe
      2) datos del establecimiento/profesional
      3) ¿hay otro turno en ese horario?      -> None = libre
    """
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    cursor.fetchone.side_effect = list(respuestas_fetchone)

    with patch("consumidor.obtener_conexion_db", return_value=conn):
        consumidor.validar_y_procesar_turno(datos_msg)
    return conn, cursor


def procesar_sin_bd(datos_msg):
    """Para rechazos que ocurren ANTES de abrir la base: verifica que ni se conecta."""
    with patch("consumidor.obtener_conexion_db") as conexion:
        consumidor.validar_y_procesar_turno(datos_msg)
    conexion.assert_not_called()


def estado_guardado(cursor):
    """Estado con el que se hizo el INSERT en reserva (None si no hubo INSERT)."""
    for llamada in cursor.execute.call_args_list:
        sql, params = llamada.args
        if "INSERT INTO reserva" in sql:
            return params[-1]
    return None


def mensaje(payload: bytes):
    """Imita el objeto que entrega paho-mqtt a on_message."""
    return SimpleNamespace(topic="turnos/solicitudes", payload=payload)


# ---------------------------------------------------------------------------
# CP20: JSON malformado -> se captura el error, se loguea y el servicio sigue
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload", [
    pytest.param(b'{ "turno": {"id": 1, "idPersonal": 4', id="JD31_json_cortado"),
    pytest.param(b"", id="JD34_vacio"),
    pytest.param(b"esto no es json", id="texto_plano"),
])
def test_cp20_json_malformado(payload, capsys):
    with patch("consumidor.validar_y_procesar_turno") as procesar_turno:
        # Si on_message dejara escapar la excepción, el test fallaría acá.
        consumidor.on_message(None, None, mensaje(payload))

    assert "Formato de JSON inválido" in capsys.readouterr().out
    procesar_turno.assert_not_called()   # no se intentó procesar nada


# ---------------------------------------------------------------------------
# CP21: falta un campo obligatorio -> se rechaza y no se toca la base (JD35-37)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("campo", [
    "id", "idEstablecimiento", "idPersonal",
    "email_cliente", "telefono_cliente", "fecha", "hora",
])
def test_cp21_campo_obligatorio_faltante(campo, capsys):
    datos = turno_valido()
    del datos["turno"][campo]

    procesar_sin_bd(datos)

    assert "incompletos" in capsys.readouterr().out


def test_cp21_mensaje_sin_clave_turno(capsys):
    procesar_sin_bd({})
    assert "incompletos" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CP22: tipos o formatos inválidos -> se captura el ValueError (JD33, JD38, JD39)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cambios", [
    pytest.param({"idPersonal": "abc"}, id="JD38_idPersonal_texto"),
    pytest.param({"idEstablecimiento": "cuatro"}, id="JD39_idEstablecimiento_texto"),
    pytest.param({"fecha": "2026/10/09"}, id="fecha_con_barras"),
    pytest.param({"hora": "18:56:00.0000"}, id="hora_con_segundos"),
    pytest.param({"idPersonal": -1}, id="id_negativo"),
])
def test_cp22_tipos_o_formatos_invalidos(cambios, capsys):
    procesar_sin_bd(turno_valido(**cambios))

    assert "formato" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# CP23: establecimiento o profesional inexistente -> no se guarda (JD40-43)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("respuestas", [
    # 1) no hay reserva repetida, 2) el establecimiento no existe
    pytest.param([None, None], id="establecimiento_inexistente"),
    # el establecimiento existe pero el LEFT JOIN no encontró al profesional
    pytest.param([None, datos_bd(id_personal=None)], id="profesional_inexistente"),
])
def test_cp23_ids_inexistentes(respuestas, capsys):
    conn, cursor = procesar(turno_valido(idEstablecimiento=99, idPersonal=99), *respuestas)

    assert "No existe el establecimiento o profesional" in capsys.readouterr().out
    assert estado_guardado(cursor) is None   # no hubo INSERT en reserva
    conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# CP24: profesional de otro establecimiento o inactivo -> se guarda como
#       RECHAZADO_SOLICITUD_NO_VALIDA (JD44, JD45)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bd", [
    pytest.param(datos_bd(id_establecimiento_personal=2), id="JD44_otro_establecimiento"),
    pytest.param(datos_bd(activo=0), id="JD45_inactivo"),
])
def test_cp24_profesional_no_valido(bd):
    conn, cursor = procesar(turno_valido(), None, bd)

    assert estado_guardado(cursor) == "RECHAZADO_SOLICITUD_NO_VALIDA"
    conn.commit.assert_called_once()   # acá SÍ se persiste, con el estado de rechazo


# ---------------------------------------------------------------------------
# CP25: fecha pasada u horario fuera de apertura/cierre (JD46, JD47, JD48)
# El establecimiento del test abre 08:00 y cierra 18:00; cada turno dura 30 min.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cambios", [
    pytest.param({"fecha": "2025-05-10"}, id="JD46_fecha_pasada"),
    pytest.param({"hora": "07:00"}, id="JD47_antes_de_apertura"),
    pytest.param({"hora": "23:30"}, id="JD48_despues_de_cierre"),
    pytest.param({"hora": "17:45"}, id="termina_despues_del_cierre"),
])
def test_cp25_fecha_pasada_u_horario_fuera_de_rango(cambios):
    conn, cursor = procesar(turno_valido(**cambios), None, datos_bd())

    assert estado_guardado(cursor) == "RECHAZADO_SOLICITUD_NO_VALIDA"
    conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# CP26: solicitud válida -> cliente insertado/actualizado y reserva RESERVADO
# (JD49, JD50, JD51). Incluye los dos extremos del horario permitido.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("hora", [
    pytest.param("10:00", id="mitad_del_dia"),
    pytest.param("08:00", id="justo_a_la_apertura"),
    pytest.param("17:30", id="termina_justo_al_cierre"),
])
def test_cp26_reserva_valida(hora):
    # 1) sin id repetido  2) datos válidos  3) horario libre
    conn, cursor = procesar(turno_valido(hora=hora), None, datos_bd(), None)

    assert estado_guardado(cursor) == "RESERVADO"

    sentencias = [llamada.args[0] for llamada in cursor.execute.call_args_list]
    assert any("INSERT INTO cliente" in sql for sql in sentencias)
    conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Extra (doble reserva por MQTT): horario ya ocupado por otra reserva activa
# ---------------------------------------------------------------------------
def test_turno_ocupado_por_mqtt():
    # el tercer fetchone devuelve una reserva existente en ese horario
    conn, cursor = procesar(turno_valido(), None, datos_bd(), {"id_reserva": 1})

    assert estado_guardado(cursor) == "RECHAZADO_TURNO_OCUPADO"