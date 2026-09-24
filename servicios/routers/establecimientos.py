from datetime import time
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from database import get_db # Importa el helper compartido de la BD

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
def crear_establecimiento(datos: EstablecimientoCreate, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    query = """
        INSERT INTO establecimiento 
        (nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        datos.nombre_comercial, datos.direccion, datos.telefono,
        str(datos.correo_electronico), datos.horario_apertura, datos.horario_cierre
    ))
    db.commit()
    nuevo_id = cursor.lastrowid

    cursor.execute("SELECT * FROM establecimiento WHERE id_establecimiento = %s", (nuevo_id,))
    nuevo = cursor.fetchone()
    cursor.close()
    return nuevo

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
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    return res

# 4. PUT /establecimientos/{id} -> HTTP 200 OK / 400 BAD REQUEST / 404 NOT FOUND
@router.put("/{id_establecimiento}")
def actualizar_establecimiento(id_establecimiento: int, cambios: EstablecimientoUpdate, db = Depends(get_db)):
    valores = cambios.model_dump(exclude_unset=True)
    if not valores:
        raise HTTPException(status_code=400, detail="Debe enviar al menos un campo a actualizar")

    if "correo_electronico" in valores:
        valores["correo_electronico"] = str(valores["correo_electronico"])

    columnas = ", ".join(f"{col} = %s" for col in valores.keys())
    parametros = list(valores.values()) + [id_establecimiento]

    cursor = db.cursor(dictionary=True)
    cursor.execute(f"UPDATE establecimiento SET {columnas} WHERE id_establecimiento = %s", parametros)
    
    if cursor.rowcount == 0:
        db.rollback()
        cursor.close()
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
        
    db.commit()
    cursor.execute("SELECT * FROM establecimiento WHERE id_establecimiento = %s", (id_establecimiento,))
    actualizado = cursor.fetchone()
    cursor.close()
    return actualizado

# 5. DELETE /establecimientos/{id} -> HTTP 204 NO CONTENT
@router.delete("/{id_establecimiento}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_establecimiento(id_establecimiento: int, db = Depends(get_db)):
    cursor = db.cursor()
    cursor.execute("DELETE FROM establecimiento WHERE id_establecimiento = %s", (id_establecimiento,))
    if cursor.rowcount == 0:
        db.rollback()
        cursor.close()
        raise HTTPException(status_code=404, detail="Establecimiento no encontrado")
    db.commit()
    cursor.close()