import os
from contextlib import asynccontextmanager
from typing import Any

# Conexión a MySQL usando el driver oficial de Connector/Python.
import mysql.connector
from mysql.connector import pooling

# Framework web para exponer los endpoints REST y validar request/response models.
from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field


# =========================
# Configuración del servicio
# =========================
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "uruturn_db"),
    "user": os.getenv("DB_USER", "uruturn_user"),
    "password": os.getenv("DB_PASSWORD", "uruturn_password"),
}

db_pool: pooling.MySQLConnectionPool | None = None


# ======================================
# Gestión del ciclo de vida de la API
# ======================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="personal_pool",
            pool_size=5,
            **DB_CONFIG,
        )
        yield
    finally:
        db_pool = None


# =========================
# App principal de FastAPI
# =========================
app = FastAPI(
    title="API de Personal Uru Turn",
    version="1.0.0",
    description="API REST para la gestión y consulta de personal.",
    lifespan=lifespan,
)


# =========================
# Modelos Pydantic
# =========================
class PersonalBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellido: str = Field(min_length=2, max_length=100)
    email: EmailStr
    telefono: str = Field(min_length=6, max_length=50)
    cargo: str = Field(min_length=2, max_length=50)
    id_establecimiento: int = Field(gt=0)


class PersonalCreate(PersonalBase):
    pass


class PersonalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    apellido: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, min_length=6, max_length=50)
    cargo: str | None = Field(default=None, min_length=2, max_length=50)
    id_establecimiento: int | None = Field(default=None, gt=0)


class Personal(PersonalBase):
    model_config = ConfigDict(from_attributes=True)

    id_personal: int


# ======================================
# Helpers para base de datos
# ======================================
def obtener_conexion():
    """Toma una conexión prestada del pool."""
    if db_pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El pool de conexiones a la base de datos no está disponible",
        )
    try:
        return db_pool.get_connection()
    except mysql.connector.Error as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo conectar con la base de datos: {error}",
        ) from error


# =========================
# Endpoints REST
# =========================
@app.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"estado": "ok"}


@app.post(
    "/personal",
    response_model=Personal,
    status_code=status.HTTP_201_CREATED,
    tags=["personal"],
    summary="Crear un nuevo miembro del personal",
)
def crear_personal(personal: PersonalCreate) -> dict[str, Any]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        sql = """
            INSERT INTO personal (nombre, apellido, email, telefono, cargo, id_establecimiento)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(
            sql,
            (
                personal.nombre,
                personal.apellido,
                str(personal.email),
                personal.telefono,
                personal.cargo,
                personal.id_establecimiento,
            ),
        )
        conexion.commit()
        nuevo_id = cursor.lastrowid

        cursor.execute(
            "SELECT id_personal, nombre, apellido, email, telefono, cargo, id_establecimiento "
            "FROM personal WHERE id_personal = %s",
            (nuevo_id,),
        )
        return cursor.fetchone()
    except mysql.connector.IntegrityError as error:
        conexion.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Error de integridad en los datos (verifique id_establecimiento o email): {error}",
        ) from error
    finally:
        cursor.close()
        conexion.close()


@app.get("/personal", response_model=list[Personal], tags=["personal"])
def listar_personal(
    id_establecimiento: int | None = Query(default=None, gt=0),
    cargo: str | None = None,
) -> list[dict[str, Any]]:
    condiciones = []
    parametros: list[Any] = []

    if id_establecimiento is not None:
        condiciones.append("id_establecimiento = %s")
        parametros.append(id_establecimiento)
    if cargo is not None:
        condiciones.append("cargo = %s")
        parametros.append(cargo)

    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            f"SELECT id_personal, nombre, apellido, email, telefono, cargo, id_establecimiento "
            f"FROM personal{where} ORDER BY apellido, nombre",
            parametros,
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conexion.close()


@app.get("/personal/{id_personal}", response_model=Personal, tags=["personal"])
def obtener_personal(id_personal: int) -> dict[str, Any]:
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id_personal, nombre, apellido, email, telefono, cargo, id_establecimiento "
            "FROM personal WHERE id_personal = %s",
            (id_personal,),
        )
        personal = cursor.fetchone()
        if personal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el miembro del personal solicitado",
            )
        return personal
    finally:
        cursor.close()
        conexion.close()


@app.put("/personal/{id_personal}", response_model=Personal, tags=["personal"])
def actualizar_personal(
    id_personal: int, cambios: PersonalUpdate
) -> dict[str, Any]:
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe indicar al menos un campo para actualizar",
        )

    # Si se actualiza el email, convertirlo a string explícitamente para MySQL
    if "email" in valores and valores["email"] is not None:
        valores["email"] = str(valores["email"])

    columnas = ", ".join(f"{nombre} = %s" for nombre in valores)
    parametros = list(valores.values()) + [id_personal]

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    try:
        cursor.execute(
            f"UPDATE personal SET {columnas} WHERE id_personal = %s", parametros
        )
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el miembro del personal solicitado",
            )
        conexion.commit()

        cursor.execute(
            "SELECT id_personal, nombre, apellido, email, telefono, cargo, id_establecimiento "
            "FROM personal WHERE id_personal = %s",
            (id_personal,),
        )
        return cursor.fetchone()
    except mysql.connector.IntegrityError as error:
        conexion.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La actualización viola una regla de la base de datos: {error}",
        ) from error
    finally:
        cursor.close()
        conexion.close()


@app.delete(
    "/personal/{id_personal}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["personal"],
)
def eliminar_personal(id_personal: int) -> None:
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM personal WHERE id_personal = %s", (id_personal,))
        if cursor.rowcount == 0:
            conexion.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No existe el miembro del personal solicitado",
            )
        conexion.commit()
    except mysql.connector.IntegrityError as error:
        conexion.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar el personal porque tiene registros asociados (ej. reservas): {error}",
        ) from error
    finally:
        cursor.close()
        conexion.close()