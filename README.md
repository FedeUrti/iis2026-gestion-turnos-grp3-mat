# UruTurn!

Aplicación de gestión de turnos con FastAPI, MySQL, MQTT y Docker.

## Iniciar

```bash
docker compose up -d --build
```

La API está disponible en `http://localhost:8000/docs`. phpMyAdmin está en
`http://localhost:8080`.

Para conocer los requisitos previos y los pasos de instalación, consultar la
[guía de instalación](/documentacion/Manual_de_instalacion.pdf).

## Funcionalidades

- Administración de establecimientos, profesionales y reservas.
- Validación de reservas en segundo plano y detección de horarios ocupados.
- Registro de clientes al crear una reserva.
- Facturación mensual por cliente para los turnos atendidos.
- Integración MQTT para publicar y recibir solicitudes de turnos.
- La [integración MQTT](/documentacion/Manual_de_Especificacion_MQTT.pdf) documenta el formato de mensajes y el
  flujo entre generador, broker, consumidor y API.

## Pruebas

Con la API y MySQL levantados:

```bash
bash scripts/test-reservas.sh
bash scripts/test-facturas.sh
```

Las pruebas crean datos temporales y los eliminan al finalizar. Requieren Bash,
`curl` y Docker Compose. `test-reservas.sh` ejecuta el worker sobre todas las
reservas pendientes, no solo las de prueba.

## Documentación de la API

El contrato está en [parte3-api.yaml](parte3-api.yaml).

## Scripts de ayuda

- [Guía de instalación y scripts curl/consulta de BD](/documentacion/Manual_de_instalacion.pdf)
- Invocador para cualquier endpoint: `bash scripts/api-curl.sh`
- Consultas de solo lectura a MySQL: `bash scripts/consultar-bd.sh`

## Manual de usuario

Consultar el [manual de usuario](/documentacion/Manual_de_Usuario_UruTurn!.pdf) para iniciar el sistema,
solicitar turnos y consultar su estado y las facturas.

## Arquitectura

Ver el [diagrama de componentes](/documentacion/Diagrama_de_componentes.pdf).
Ver el [diagrama de arquitectura del sistema](/documentacion/diagrama_de_arquitectura.pdf).

