import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, time
from typing import Any

import mysql.connector
from mysql.connector import pooling
import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "uruturn_db"),
    "user": os.getenv("DB_USER", "uruturn_user"),
    "password": os.getenv("DB_PASSWORD", "uruturn_password"),
}
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "turnos/solicitudes")

# Recursos "caros" que antes se creaban y destruian en cada request.
# Se inicializan una sola vez al levantar el contenedor (ver lifespan mas abajo)
# y se reutilizan durante toda la vida del proceso.
db_pool: pooling.MySQLConnectionPool | None = None
mqtt_client: mqtt.Client | None = None


def _on_mqtt_disconnect(client, userdata, rc, *args):
    # paho reconecta solo si el loop sigue corriendo (loop_start ya lo dejamos andando).
    if rc != 0:
        print(f"[MQTT] Desconexion inesperada (rc={rc}); paho intentara reconectar.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, mqtt_client

    try:
        # Se crean una sola vez y se reutilizan mientras vive la API.
        db_pool = pooling.MySQLConnectionPool(
            pool_name="reservas_pool",
            pool_size=5,
            **DB_CONFIG,
        )

        mqtt_client = mqtt.Client()
        mqtt_client.on_disconnect = _on_mqtt_disconnect
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()

        yield
    finally:
        # El bloque se ejecuta tambien si falla el arranque o el apagado.
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
            mqtt_client = None
        db_pool = None


app = FastAPI(
    title="API de Reservas Uru Turn",
    version="1.0.0",
    description="API REST para consultar y administrar reservas de turnos.",
    lifespan=lifespan,
)


class ReservaBase(BaseModel):
    email_solicitante: EmailStr
    telefono_solicitante: str = Field(min_length=6, max_length=50)
    id_personal: int = Field(gt=0)
    fecha_turno: date
    hora_turno: time


class ReservaCreate(ReservaBase):
    pass


class ReservaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email_solicitante: EmailStr | None = None
    telefono_solicitante: str | None = Field(default=None, min_length=6, max_length=50)
    id_personal: int | None = Field(default=None, gt=0)
    fecha_turno: date | None = None
    hora_turno: time | None = None
    estado_reserva: str | None = Field(
        default=None, pattern="^(RESERVADO|CANCELADO|FINALIZADO)$"
    )


class Reserva(ReservaBase):
    model_config = ConfigDict(from_attributes=True)

    id_reserva: int
    fecha_reservado: Any
    estado_reserva: str


class TurnoPublicado(ReservaCreate):
    id: int


class SolicitudReserva(BaseModel):
    mensaje: str
    turno: TurnoPublicado


def obtener_conexion():
    """Toma una conexion prestada del pool (no abre una nueva contra MySQL)."""
    if db_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El pool de conexiones a la base de datos no esta disponible",
        )
    try:
        return db_pool.get_connection()
    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con la base de datos: {error}",
        ) from error


def publicar_solicitud(reserva: ReservaCreate, id_reserva: int) -> None:
    """Publica en el cliente MQTT que ya esta conectado (no crea uno nuevo)."""
    if mqtt_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El cliente MQTT no esta disponible",
        )
    payload = {
        "status": "turno_solicitado",
        "turno": {
            "id": id_reserva,
            "email_cliente": str(reserva.email_solicitante),
            "telefono_cliente": reserva.telefono_solicitante,
            "idPersonal": reserva.id_personal,
            "fecha": reserva.fecha_turno.isoformat(),
            "hora": reserva.hora_turno.strftime("%H:%M"),
        },
    }
    try:
        resultado = mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), qos=1)
        resultado.wait_for_publish(timeout=5)
    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudo publicar en el broker MQTT: {error}",
        ) from error

    if resultado.rc != mqtt.MQTT_ERR_SUCCESS:
        raise HTTPException(status_code=503, detail="No se pudo publicar la solicitud MQTT")


@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"estado": "ok"}


@app.post(
    "/reservas",
    response_model=SolicitudReserva,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["reservas"],
    summary="Solicitar una reserva",
)
def crear_reserva(reserva: ReservaCreate) -> SolicitudReserva:
    id_reserva = secrets.randbelow(900000) + 100000
    publicar_solicitud(reserva, id_reserva)
    return SolicitudReserva(
        mensaje="Solicitud publicada; el consumidor la procesara",
        turno=TurnoPublicado(id=id_reserva, **reserva.model_dump()),
    )


@app.get("/reservas", response_model=list[Reserva], tags=["reservas"])
def listar_reservas(
    id_personal: int | None = Query(default=None, gt=0),
    fecha_turno: date | None = None,
    estado_reserva: str | None = Query(
        default=None, pattern="^(RESERVADO|CANCELADO|FINALIZADO)$"
    ),
) -> list[dict[str, Any]]:
    condiciones = []
    parametros: list[Any] = []
    if id_personal is not None:
        condiciones.append("id_personal = %s")
        parametros.append(id_personal)
    if fecha_turno is not None:
        condiciones.append("fecha_turno = %s")
        parametros.append(fecha_turno)
    if estado_reserva is not None:
        condiciones.append("estado_reserva = %s")
        parametros.append(estado_reserva)
    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            f"SELECT id_reserva, fecha_reservado, email_solicitante, "
            f"telefono_solicitante, id_personal, fecha_turno, "
            f"CAST(hora_turno AS CHAR) AS hora_turno, estado_reserva "
            f"FROM reserva{where} ORDER BY fecha_turno, hora_turno",
            parametros,
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


@app.get("/reservas/{id_reserva}", response_model=Reserva, tags=["reservas"])
def obtener_reserva(id_reserva: int) -> dict[str, Any]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_reserva, fecha_reservado, email_solicitante, "
            "telefono_solicitante, id_personal, fecha_turno, "
            "CAST(hora_turno AS CHAR) AS hora_turno, estado_reserva "
            "FROM reserva WHERE id_reserva = %s",
            (id_reserva,),
        )
        reserva = cursor.fetchone()
        if reserva is None:
            raise HTTPException(status_code=404, detail="No existe la reserva solicitada")
        return reserva
    finally:
        cursor.close()
        conexion.close()


@app.put("/reservas/{id_reserva}", response_model=Reserva, tags=["reservas"])
def actualizar_reserva(
    id_reserva: int, cambios: ReservaUpdate
) -> dict[str, Any]:
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=400, detail="Debe indicar al menos un campo para actualizar"
        )
    columnas = ", ".join(f"{nombre} = %s" for nombre in valores)
    parametros = list(valores.values()) + [id_reserva]
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            f"UPDATE reserva SET {columnas} WHERE id_reserva = %s", parametros
        )
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(status_code=404, detail="No existe la reserva solicitada")
        conexion.commit()
        cursor.execute(
            "SELECT id_reserva, fecha_reservado, email_solicitante, "
            "telefono_solicitante, id_personal, fecha_turno, "
            "CAST(hora_turno AS CHAR) AS hora_turno, estado_reserva "
            "FROM reserva WHERE id_reserva = %s",
            (id_reserva,),
        )
        return cursor.fetchone()
    except mysql.connector.IntegrityError as error:
        conexion.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"La actualización viola una regla de la reserva: {error}",
        ) from error
    finally:
        cursor.close()
        conexion.close()


@app.delete(
    "/reservas/{id_reserva}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["reservas"],
)
def eliminar_reserva(id_reserva: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM reserva WHERE id_reserva = %s", (id_reserva,))
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(status_code=404, detail="No existe la reserva solicitada")
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()
