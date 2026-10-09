import secrets
import mysql.connector
from datetime import date, time
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr, Field
from database import get_db

router = APIRouter(prefix="/reservas", tags=["reservas"])

class ReservaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email_solicitante: EmailStr
    telefono_solicitante: str = Field(min_length=6, max_length=50)
    id_establecimiento: int
    id_personal: int
    fecha_turno: date
    hora_turno: time

class ReservaUpdate(BaseModel):
    estado_reserva: str  # 'RESERVADO', 'CANCELADO', 'FINALIZADO'
    fecha_turno: str
    hora_turno: str

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def crear_reserva(reserva: ReservaCreate, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT e.id_establecimiento, p.id_personal,
                   p.id_establecimiento AS id_establecimiento_personal,
                   p.activo
            FROM establecimiento e
            LEFT JOIN personal p ON p.id_personal = %s
            WHERE e.id_establecimiento = %s
            """,
            (reserva.id_personal, reserva.id_establecimiento),
        )
        referencias = cursor.fetchone()
        if not referencias:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No existe el establecimiento con ID {reserva.id_establecimiento}.",
            )
        if referencias["id_personal"] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No existe el personal con ID {reserva.id_personal}.",
            )
        if referencias["id_establecimiento_personal"] != reserva.id_establecimiento:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El personal indicado no pertenece al establecimiento seleccionado.",
            )
        if not referencias["activo"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El personal indicado no está activo.",
            )

        id_reserva = None
        for _ in range(10):
            candidato = secrets.randbelow(900000) + 100000
            cursor.execute(
                """
                SELECT id_reserva FROM reserva WHERE id_reserva = %s
                """,
                (candidato,),
            )
            if not cursor.fetchone():
                id_reserva = candidato
                break

        if id_reserva is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No fue posible asignar un identificador a la solicitud. Intente nuevamente.",
            )

        cursor.execute(
            """
            INSERT INTO cliente (email, nombre, telefono)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                nombre = VALUES(nombre),
                telefono = VALUES(telefono)
            """,
            (
                str(reserva.email_solicitante),
                reserva.nombre,
                reserva.telefono_solicitante,
            ),
        )

        cursor.execute(
            """
            INSERT INTO reserva (
                id_reserva, email_solicitante, telefono_solicitante,
                id_establecimiento, id_personal, fecha_turno, hora_turno,
                estado_reserva
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDIENTE')
            """,
            (
                id_reserva,
                str(reserva.email_solicitante),
                reserva.telefono_solicitante,
                reserva.id_establecimiento,
                reserva.id_personal,
                reserva.fecha_turno,
                reserva.hora_turno,
            ),
        )
        db.commit()
        return {
            "mensaje": "Solicitud recibida. El procesamiento se realizará en el próximo ciclo.",
            "turno": {
                "id": id_reserva,
                **reserva.model_dump(),
                "estado_reserva": "PENDIENTE",
            },
        }
    except mysql.connector.Error as err:
        db.rollback()
        if err.errno == 1062:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una reserva con ese identificador.",
            )
        if err.errno == 1054 or err.errno == 1146:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="La estructura de la base de datos no coincide con la versión de la API.",
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    finally:
        cursor.close()

@router.get("", status_code=status.HTTP_200_OK)
def listar_reservas(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.id_reserva, c.nombre, r.email_solicitante,
                   r.fecha_reservado,
                   r.telefono_solicitante, r.id_personal, r.id_establecimiento,
                   r.fecha_turno, r.hora_turno, r.estado_reserva
            FROM reserva r
            JOIN cliente c ON c.email = r.email_solicitante
            ORDER BY r.fecha_turno, r.hora_turno
            """
        )
        return cursor.fetchall()
    finally:
        cursor.close()

@router.get("/{id_reserva}", status_code=status.HTTP_200_OK)
def obtener_reserva(id_reserva: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT r.*, c.nombre
            FROM reserva r
            JOIN cliente c ON c.email = r.email_solicitante
            WHERE r.id_reserva = %s
            """,
            (id_reserva,),
        )
        res = cursor.fetchone()
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
        return res
    finally:
        cursor.close()

@router.put("/{id_reserva}", status_code=status.HTTP_200_OK)
def actualizar_reserva(id_reserva: int, res_data: ReservaUpdate, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    query = """
        UPDATE reserva 
        SET estado_reserva = %s, fecha_turno = %s, hora_turno = %s
        WHERE id_reserva = %s
    """
    try:
        cursor.execute(query, (res_data.estado_reserva, res_data.fecha_turno, res_data.hora_turno, id_reserva))
        db.commit()
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada para actualizar")
        return {"id_reserva": id_reserva, **res_data.model_dump()}
    except mysql.connector.Error as err:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err))
    finally:
        cursor.close()

@router.delete("/{id_reserva}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_reserva(id_reserva: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM reserva WHERE id_reserva = %s", (id_reserva,))
    db.commit()
    
    if cursor.rowcount == 0:
        cursor.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada para eliminar")
    
    cursor.close()
    return None