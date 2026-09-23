import os
from datetime import time
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import MySQLCursorBufferedDict, PooledMySQLConnection
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Carga variables de entorno
load_dotenv()

# ======================================
# Configuración del APIRouter
# ======================================
router = APIRouter(
    prefix="/establecimientos",
    tags=["establecimientos"]
)

# ======================================
# Configuración de Base de Datos MySQL
# ======================================
DB_HOST = os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306")))
DB_USER = os.getenv("MYSQLUSER", os.getenv("DB_USER", "root"))
DB_PASSWORD = os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", ""))
DB_NAME = os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "reserva_canchas"))

db_pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="pool_establecimientos",
    pool_size=5,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
)


def obtener_conexion() -> PooledMySQLConnection | MySQLConnectionAbstract:
    try:
        return db_pool.get_connection()
    except mysql.connector.Error as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al conectar con la base de datos: {err}",
        )


# ======================================
# Modelos Pydantic - Establecimiento
# ======================================
class EstablecimientoBase(BaseModel):
    nombre_comercial: str = Field(min_length=1, max_length=150)
    direccion: str = Field(min_length=1, max_length=255)
    telefono: str = Field(min_length=1, max_length=50)
    correo_electronico: EmailStr = Field(max_length=100)
    horario_apertura: time
    horario_cierre: time


class EstablecimientoCreate(EstablecimientoBase):
    pass


class EstablecimientoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre_comercial: str | None = Field(default=None, min_length=1, max_length=150)
    direccion: str | None = Field(default=None, min_length=1, max_length=255)
    telefono: str | None = Field(default=None, min_length=1, max_length=50)
    correo_electronico: EmailStr | None = Field(default=None, max_length=100)
    horario_apertura: time | None = None
    horario_cierre: time | None = None


class Establecimiento(EstablecimientoBase):
    model_config = ConfigDict(from_attributes=True)

    id_establecimiento: int


# ======================================
# Endpoints REST - Establecimientos
# ======================================
@router.post(
    "",
    response_model=Establecimiento,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo establecimiento",
)
def crear_establecimiento(
    establecimiento: EstablecimientoCreate,
) -> dict[str, Any]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "INSERT INTO establecimiento "
            "(nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                establecimiento.nombre_comercial,
                establecimiento.direccion,
                establecimiento.telefono,
                str(establecimiento.correo_electronico),
                establecimiento.horario_apertura,
                establecimiento.horario_cierre,
            ),
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid

        cursor.execute(
            "SELECT id_establecimiento, nombre_comercial, direccion, telefono, "
            "correo_electronico, CAST(horario_apertura AS CHAR) AS horario_apertura, "
            "CAST(horario_cierre AS CHAR) AS horario_cierre "
            "FROM establecimiento WHERE id_establecimiento = %s",
            (nuevo_id,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conexion.close()


@router.get(
    "",
    response_model=list[Establecimiento],
    summary="Listar establecimientos",
)
def listar_establecimientos() -> list[dict[str, Any]]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_establecimiento, nombre_comercial, direccion, telefono, "
            "correo_electronico, CAST(horario_apertura AS CHAR) AS horario_apertura, "
            "CAST(horario_cierre AS CHAR) AS horario_cierre "
            "FROM establecimiento ORDER BY id_establecimiento"
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


@router.get(
    "/{id_establecimiento}",
    response_model=Establecimiento,
    summary="Obtener un establecimiento por ID",
)
def obtener_establecimiento(id_establecimiento: int) -> dict[str, Any]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_establecimiento, nombre_comercial, direccion, telefono, "
            "correo_electronico, CAST(horario_apertura AS CHAR) AS horario_apertura, "
            "CAST(horario_cierre AS CHAR) AS horario_cierre "
            "FROM establecimiento WHERE id_establecimiento = %s",
            (id_establecimiento,),
        )
        establecimiento = cursor.fetchone()
        if establecimiento is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el establecimiento solicitado",
            )
        return establecimiento
    finally:
        cursor.close()
        conexion.close()


@router.put(
    "/{id_establecimiento}",
    response_model=Establecimiento,
    summary="Actualizar un establecimiento",
)
def actualizar_establecimiento(
    id_establecimiento: int, cambios: EstablecimientoUpdate
) -> dict[str, Any]:
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar al menos un campo para actualizar",
        )

    if "correo_electronico" in valores:
        valores["correo_electronico"] = str(valores["correo_electronico"])

    columnas = ", ".join(f"{nombre} = %s" for nombre in valores)
    parametros = list(valores.values()) + [id_establecimiento]

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            f"UPDATE establecimiento SET {columnas} WHERE id_establecimiento = %s",
            parametros,
        )
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el establecimiento solicitado",
            )
        conexion.commit()

        cursor.execute(
            "SELECT id_establecimiento, nombre_comercial, direccion, telefono, "
            "correo_electronico, CAST(horario_apertura AS CHAR) AS horario_apertura, "
            "CAST(horario_cierre AS CHAR) AS horario_cierre "
            "FROM establecimiento WHERE id_establecimiento = %s",
            (id_establecimiento,),
        )
        return cursor.fetchone()
    finally:
        cursor.close()
        conexion.close()


@router.delete(
    "/{id_establecimiento}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un establecimiento",
)
def eliminar_establecimiento(id_establecimiento: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute(
            "DELETE FROM establecimiento WHERE id_establecimiento = %s",
            (id_establecimiento,),
        )
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el establecimiento solicitado",
            )
        conexion.commit()
    finally:
        cursor.close()
        conexion.close()
