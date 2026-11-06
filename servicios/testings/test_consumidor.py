import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests

import consumidor


def mensaje(payload, qos=1):
    return SimpleNamespace(
        topic="turnos/solicitudes",
        payload=payload,
        qos=qos,
        mid=17,
    )


def test_on_message_traduce_y_envia_la_reserva_a_la_api():
    client = MagicMock()
    mensaje_mqtt = {
        "status": "turno_creado",
        "turno": {
            "id": 123456,
            "idEstablecimiento": 2,
            "idPersonal": 4,
            "email_cliente": "cliente@example.com",
            "nombre_cliente": "Cliente",
            "telefono_cliente": 99111111,
            "fecha": "2026-11-12",
            "hora": "10:00",
        },
    }
    respuesta = MagicMock(status_code=202, text='{"turno":{"id":654321}}')

    with patch("consumidor.requests.post", return_value=respuesta) as post:
        consumidor.on_message(
            client,
            None,
            mensaje(json.dumps(mensaje_mqtt).encode()),
        )

    post.assert_called_once_with(
        f"{consumidor.API_BASE_URL}/reservas",
        json={
            "nombre": "Cliente",
            "email_solicitante": "cliente@example.com",
            "telefono_solicitante": "99111111",
            "id_establecimiento": 2,
            "id_personal": 4,
            "fecha_turno": "2026-11-12",
            "hora_turno": "10:00",
        },
        timeout=consumidor.API_TIMEOUT_SECONDS,
    )
    client.ack.assert_called_once_with(17, 1)
    client.disconnect.assert_not_called()


def test_on_message_descarta_json_invalido_y_confirma(capsys):
    client = MagicMock()

    with patch("consumidor.requests.post") as post:
        consumidor.on_message(client, None, mensaje(b"no es json"))

    assert "JSON inválido" in capsys.readouterr().out
    post.assert_not_called()
    client.ack.assert_called_once_with(17, 1)


def test_on_message_confirma_rechazo_permanente_de_la_api():
    client = MagicMock()
    respuesta = MagicMock(status_code=422, text="datos inválidos")

    with patch("consumidor.requests.post", return_value=respuesta):
        consumidor.on_message(
            client,
            None,
            mensaje(b'{"turno":{"id":123456}}'),
        )

    client.ack.assert_called_once_with(17, 1)
    client.disconnect.assert_not_called()


def test_on_message_reintenta_si_la_api_responde_conflicto():
    client = MagicMock()
    respuesta = MagicMock(status_code=409, text="conflicto")

    with patch("consumidor.requests.post", return_value=respuesta):
        consumidor.on_message(
            client,
            None,
            mensaje(b'{"turno":{"id":123456}}'),
        )

    client.ack.assert_not_called()
    client.disconnect.assert_called_once()


def test_on_message_descarta_mensaje_sin_turno(capsys):
    client = MagicMock()

    with patch("consumidor.requests.post") as post:
        consumidor.on_message(client, None, mensaje(b'{"status":"turno_creado"}'))

    assert "falta el objeto 'turno'" in capsys.readouterr().out
    post.assert_not_called()
    client.ack.assert_called_once_with(17, 1)


def test_on_message_desconecta_sin_confirmar_si_la_api_falla():
    client = MagicMock()

    with patch(
        "consumidor.requests.post",
        side_effect=requests.ConnectionError("API caída"),
    ):
        consumidor.on_message(
            client,
            None,
            mensaje(b'{"turno":{"id":123456}}'),
        )

    client.ack.assert_not_called()
    client.disconnect.assert_called_once()


def test_on_message_no_confirma_qos_cero():
    client = MagicMock()
    respuesta = MagicMock(status_code=202, text="ok")

    with patch("consumidor.requests.post", return_value=respuesta):
        consumidor.on_message(
            client,
            None,
            mensaje(b'{"turno":{"id":123456}}', qos=0),
        )

    client.ack.assert_not_called()
