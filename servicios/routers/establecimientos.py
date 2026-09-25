import mysql.connector
from datetime import time
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from database import get_db

router = APIRouter(prefix="/establecimientos", tags=["establecimientos"])

# =========================
# Modelos Pydantic
# =========================
class EstablecimientoBase(BaseModel):
    nombre_comercial: str = Field(min_length=1, max_length=150)
    direccion: str = Field(min_length=1, max_length=255)
    telefono: str = Field(min_length=1, max_length=50)
    correo_electronico: EmailStr
    horario_apertura: time
    horario_cierre: time

class EstablecimientoCreate(EstablecimientoBase):
    pass

class EstablecimientoUpdate(BaseModel):
    nombre_comercial: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    correo_electronico: EmailStr | None = None
    horario_apertura: time | None = None
    horario_cierre: time | None = None

# =========================
# Endpoints REST
# =========================

# 1. POST /establecimientos -> HTTP 201 CREATED
@router.post("", status_code=status.HTTP_201_CREATED)
def crear_establecimiento(est: EstablecimientoBase, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    query = """
        INSERT INTO establecimiento (nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        cursor.execute(query, (est.nombre_comercial, est.direccion, est.telefono, est.correo_electronico, est.horario_apertura, est.horario_cierre))
        db.commit()
        nuevo_id = cursor.lastrowid
        return {"id_establecimiento": nuevo_id, **est.model_dump()}
    except mysql.connector.Error as err:
        db.rollback()
        if err.errno == 1062:  # ER_DUP_ENTRY
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe un establecimiento registrado con el nombre '{est.nombre_comercial}'"
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    finally:
        cursor.close()

# 2. GET /establecimientos -> HTTP 200 OK
@router.get("")
def listar_establecimientos(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM establecimiento ORDER BY id_establecimiento")
    res = cursor.fetchall()
    cursor.close()
    return res

# 3. GET /establecimientos/{id} -> HTTP 200 OK / 404 NOT FOUND
@router.get("/{id_establecimiento}")
def obtener_establecimiento(id_establecimiento: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM establecimiento WHERE id_establecimiento = %s", (id_establecimiento,))
    res = cursor.fetchone()
    cursor.close()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establecimiento no encontrado")
    return res

# 4. PUT /establecimientos/{id} -> HTTP 200 OK / 400 BAD REQUEST / 404 NOT FOUND
@router.put("/{id_establecimiento}")
def actualizar_establecimiento(id_establecimiento: int, cambios: EstablecimientoUpdate, db = Depends(get_db)):
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe enviar al menos un campo a actualizar")

    if "correo_electronico" in valores and valores["correo_electronico"] is not None:
        valores["correo_electronico"] = str(valores["correo_electronico"])

    columnas = ", ".join(f"{col} = %s" for col in valores.keys())
    parametros = list(valores.values()) + [id_establecimiento]

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(f"UPDATE establecimiento SET {columnas} WHERE id_establecimiento = %s", parametros)
        
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establecimiento no encontrado")
            
        db.commit()
        cursor.execute("SELECT * FROM establecimiento WHERE id_establecimiento = %s", (id_establecimiento,))
        actualizado = cursor.fetchone()
        return actualizado
    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    finally:
        cursor.close()

# 5. DELETE /establecimientos/{id} -> HTTP 204 NO CONTENT
@router.delete("/{id_establecimiento}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_establecimiento(id_establecimiento: int, db = Depends(get_db)):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM establecimiento WHERE id_establecimiento = %s", (id_establecimiento,))
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Establecimiento no encontrado")
        db.commit()
    except mysql.connector.Error as err:
        db.rollback()
        # Si un establecimiento tiene profesionales asociados, fallará por la llave foránea si no hay CASCADE
        if err.errno == 1451:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="No se puede eliminar el establecimiento porque tiene profesionales asociados."
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    finally:
        cursor.close()