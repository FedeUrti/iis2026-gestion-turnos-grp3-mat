from fastapi import APIRouter, HTTPException, Query, status, Depends
from pydantic import BaseModel, EmailStr, Field
import mysql.connector
from database import get_db  # Importa el helper compartido de base de datos

router = APIRouter(prefix="/personal", tags=["personal"])

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
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    apellido: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    telefono: str | None = Field(default=None, min_length=6, max_length=50)
    cargo: str | None = Field(default=None, min_length=2, max_length=50)
    id_establecimiento: int | None = Field(default=None, gt=0)

# =========================
# Endpoints REST
# =========================

# 1. POST /personal -> HTTP 201 CREATED
@router.post("", status_code=status.HTTP_201_CREATED)
def crear_personal(personal: PersonalCreate, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        sql = """
            INSERT INTO personal (nombre, apellido, email, telefono, cargo, id_establecimiento)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            personal.nombre,
            personal.apellido,
            str(personal.email),
            personal.telefono,
            personal.cargo,
            personal.id_establecimiento,
        ))
        db.commit()
        nuevo_id = cursor.lastrowid

        cursor.execute("SELECT * FROM personal WHERE id_personal = %s", (nuevo_id,))
        nuevo = cursor.fetchone()
        cursor.close()
        return nuevo
    except mysql.connector.IntegrityError as err:
        db.rollback()
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Error de integridad: verifique si existe el id_establecimiento o el email. ({err})"
        )

# 2. GET /personal -> HTTP 200 OK (Filtros opcionales por id_establecimiento o cargo)
@router.get("")
def listar_personal(
    id_establecimiento: int | None = Query(default=None, gt=0),
    cargo: str | None = None,
    db = Depends(get_db)
):
    condiciones = []
    parametros = []

    if id_establecimiento is not None:
        condiciones.append("id_establecimiento = %s")
        parametros.append(id_establecimiento)
    if cargo is not None:
        condiciones.append("cargo = %s")
        parametros.append(cargo)

    where = f" WHERE {' AND '.join(condiciones)}" if condiciones else ""

    cursor = db.cursor(dictionary=True)
    cursor.execute(f"SELECT * FROM personal{where} ORDER BY apellido, nombre", parametros)
    resultado = cursor.fetchall()
    cursor.close()
    return resultado

# 3. GET /personal/{id_personal} -> HTTP 200 OK / 404 NOT FOUND
@router.get("/{id_personal}")
def obtener_personal(id_personal: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM personal WHERE id_personal = %s", (id_personal,))
    personal = cursor.fetchone()
    cursor.close()
    
    if not personal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal no encontrado")
    return personal

# 4. PUT /personal/{id_personal} -> HTTP 200 OK / 400 BAD REQUEST / 404 NOT FOUND
@router.put("/{id_personal}")
def actualizar_personal(id_personal: int, cambios: PersonalUpdate, db = Depends(get_db)):
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe indicar al menos un campo para actualizar")

    if "email" in valores and valores["email"] is not None:
        valores["email"] = str(valores["email"])

    columnas = ", ".join(f"{col} = %s" for col in valores.keys())
    parametros = list(valores.values()) + [id_personal]

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(f"UPDATE personal SET {columnas} WHERE id_personal = %s", parametros)
        if cursor.rowcount == 0:
            db.rollback()
            cursor.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal no encontrado")
        
        db.commit()
        cursor.execute("SELECT * FROM personal WHERE id_personal = %s", (id_personal,))
        actualizado = cursor.fetchone()
        cursor.close()
        return actualizado
    except mysql.connector.IntegrityError as err:
        db.rollback()
        cursor.close()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err))

# 5. DELETE /personal/{id_personal} -> HTTP 204 NO CONTENT / 404 / 409
@router.delete("/{id_personal}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_personal(id_personal: int, db = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM personal WHERE id_personal = %s", (id_personal,))
        if cursor.rowcount == 0:
            db.rollback()
            cursor.close()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personal no encontrado")
        db.commit()
        cursor.close()
    except mysql.connector.IntegrityError as err:
        db.rollback()
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede eliminar el personal porque tiene registros asociados (ej. reservas): {err}"
        )