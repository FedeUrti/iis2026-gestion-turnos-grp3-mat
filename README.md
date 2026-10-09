# UruTurn! - Plataforma de gestión de turnos

Proyecto de gestión de turnos construido con FastAPI, MySQL, MQTT y Docker. La API registra reservas pendientes y un proceso periódico integrado en FastAPI las valida y actualiza sus estados. Los servicios generador y consumidor MQTT de la parte anterior se mantienen disponibles.

## ¿Qué incluye el proyecto?

- API REST en FastAPI para administrar:
  - `/establecimientos`
  - `/personal`
  - `/reservas`
  - `/facturas`
- Base de datos MySQL con clientes, reservas y facturación mensual en [db/init-completo.sql](db/init-completo.sql)
- Cuatro establecimientos de ejemplo, con tres profesionales activos por establecimiento
- Broker MQTT con Eclipse Mosquitto para la cola de mensajes de turnos
- Servicios auxiliares en Python para publicar y consumir eventos MQTT
- Procesamiento periódico de las reservas pendientes recibidas por la API
- Panel de administración de MySQL con phpMyAdmin

## Arquitectura

El entorno levantado por Docker Compose incluye estos componentes principales:

- `mosquitto`: broker MQTT para el canal `turnos/solicitudes`
- `db`: base de datos MySQL con clientes, establecimientos, profesionales, reservas y facturas
- `phpmyadmin`: interfaz web para inspeccionar la base de datos en `http://localhost:8080`
- `generador`: publicador de mensajes de ejemplo para simular la creación de turnos
- `consumidor`: suscriptor que valida y persiste reservas en la base de datos
- `reservas-api`: API FastAPI y proceso periódico de reservas

## Requisitos

- Docker
- Docker Compose

## Levantar el entorno

```bash
docker compose up -d --build
```

Esto inicia la infraestructura completa del proyecto, incluyendo broker, base de datos, API y servicios asociados.

## API REST

La API queda disponible en:

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI: `http://localhost:8000/openapi.json`
- Health check: `http://localhost:8000/health`

### Endpoints principales

- `GET /establecimientos`, `POST /establecimientos`, `PUT /establecimientos/{id}`, `DELETE /establecimientos/{id}`
- `GET /personal`, `POST /personal`, `PUT /personal/{id}`, `DELETE /personal/{id}`
- `GET /reservas`, `POST /reservas`, `PUT /reservas/{id}`, `DELETE /reservas/{id}`
- `GET /facturas?email_cliente=...` y `GET /facturas/{id_factura}`

El contrato de la API está definido en [parte3-api.yaml](parte3-api.yaml).

## Flujo de reservas por la API

1. `POST /reservas` comprueba que el establecimiento y el profesional existan, que el profesional esté activo y pertenezca al establecimiento. Si alguna comprobación falla, responde `400` sin registrar cliente ni reserva.
2. Si los IDs son válidos, registra o actualiza el cliente (email como clave primaria, nombre y teléfono) y guarda la reserva directamente en `reserva` con estado `PENDIENTE`.
3. FastAPI ejecuta un ciclo cada 60 segundos y valida que la fecha y la hora no hayan pasado y que el horario siga disponible. Se acepta el minuto actual como margen; una reserva de minutos anteriores se rechaza.
4. Si el turno está ocupado, la reserva queda como `RECHAZADO_TURNO_OCUPADO`. Si su fecha y hora ya pasaron antes del minuto actual, queda como `RECHAZADO_SOLICITUD_NO_VALIDA`.
5. Si el turno está libre, esa misma fila pasa a `AGENDADO`. Cuando pasa la fecha y hora del turno, otro ciclo la cambia a `ATENDIDO`.
6. `GET /reservas` permite consultar todas las reservas, incluidas las pendientes y rechazadas.

El intervalo puede configurarse con `TURNOS_INTERVAL_SECONDS` (por defecto, 60 segundos). El generador y el consumidor MQTT siguen funcionando por separado para las pruebas de la parte anterior; `POST /reservas` ya no depende de Mosquitto.

## Facturación mensual

Cada 5 minutos, el proceso de FastAPI recorre los turnos con estado `ATENDIDO`. Agrupa los turnos por cliente (email) y mes de la fecha del turno: cada pareja cliente/mes tiene una única factura vinculada al cliente, con un ítem por turno. El precio de cada ítem es el `costo_consulta` del profesional que atendió ese turno; se guarda como valor histórico y se suma al total de la factura. Cuando el ítem se registra, el turno cambia a `FACTURADO`.

Por eso una factura mensual puede contener turnos de varios profesionales, incluso si sus costos son distintos. La tarea puede configurarse con `FACTURAS_INTERVAL_SECONDS` (por defecto, 300 segundos). Consultar facturas con `GET /facturas` o filtrar por cliente con `GET /facturas?email_cliente=paciente@correo.com`; `GET /facturas/{id_factura}` también devuelve sus ítems.

## Scripts de ejemplo

### Escuchar eventos MQTT

```bash
./scripts/suscribirse-turnos.sh
```

### Publicar un mensaje de prueba

```bash
./scripts/publicar-turno.sh
```

### Ejecutar la prueba completa de alta y consulta de reservas por API

```bash
bash scripts/test-reservas.sh
```

Este script hace una solicitud de ejemplo a `POST /reservas`, espera el siguiente ciclo de FastAPI y consulta el resultado en la API y en MySQL.

## Inicializar o actualizar la base de datos

`db/init-completo.sql` es el único init que Docker monta y ejecuta al inicializar
un volumen MySQL vacío. Incluye todas las tablas y datos de ejemplo, por lo que
una instalación nueva no necesita ejecutar archivos `migrate-*.sql`.

Si el volumen ya existe, MySQL no vuelve a ejecutar el init. Para recrear la base
con el esquema completo, se puede usar el script interactivo:

```powershell
.\scripts\reiniciar-bd.ps1
```

Este proceso elimina las reservas y facturas existentes. No lo ejecutes si
necesitás conservar esos datos.

Los scripts `migrate-*.sql` son históricos y están archivados junto con el init
anterior en `db/.deprecated/`, carpeta ignorada por Git. Para una base existente
que necesite conservar datos y todavía no tenga el esquema actual, no ejecutes
un reinicio: prepara una migración específica para esa base. El init completo
está destinado a instalaciones nuevas o a reinicializar una base descartable.

### Reiniciar la base de datos para pruebas

`docker compose down` conserva el volumen MySQL y sus datos. Para recrear solo la
base desde cero, usa el comando de `.\scripts\reiniciar-bd.ps1` indicado arriba.
El script pide escribir `BORRAR` antes de continuar, elimina únicamente el
volumen MySQL y vuelve a levantar el entorno. Se pierden las reservas y facturas existentes; los volúmenes de Mosquitto y phpMyAdmin se
conservan.

## Autores

- Benjamín Gordillo
- Federico Urtiberea
- Santiago Lemos
- Ignacio Porcal
