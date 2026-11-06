from unittest.mock import MagicMock, patch

import generador


def test_obtener_datos_generacion_usa_api_y_solo_profesionales_activos():
    respuesta = MagicMock()
    respuesta.json.return_value = [
        {"id_establecimiento": 2, "id_personal": 4, "activo": True},
        {"id_establecimiento": 3, "id_personal": 5, "activo": False},
    ]

    with patch("generador.requests.get", return_value=respuesta) as get:
        profesionales = generador.obtener_datos_generacion()

    assert profesionales == [(2, 4)]
    get.assert_called_once_with(
        f"{generador.API_BASE_URL}/personal",
        timeout=generador.API_TIMEOUT_SECONDS,
    )
    respuesta.raise_for_status.assert_called_once()


def test_generador_crea_evento_sin_consultar_ni_escribir_en_base():
    with patch("generador.obtener_datos_generacion", return_value=[(2, 4)]):
        mensaje = generador.generador_turno_random()

    assert mensaje["status"] == "turno_creado"
    assert mensaje["turno"]["idEstablecimiento"] == 2
    assert mensaje["turno"]["idPersonal"] == 4
    assert mensaje["turno"]["id"] > 0
