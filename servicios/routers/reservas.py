import secrets
import mysql.connector
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from database import get_db, publicar_mqtt

router = APIRouter(prefix="/reservas", tags=["reservas"])

class ReservaCreate(BaseModel):
    email_solicitante: str
    telefono_solicitante: str
    id_personal: int
    fecha_turno: str
    hora_turno: str

class ReservaUpdate(BaseModel):
    estado_reserva: str  # 'RESERVADO', 'CANCELADO', 'FINALIZADO'
    fecha_turno: str
    hora_turno: str

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def crear_reserva(reserva: ReservaCreate, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # 1. Validación Síncrona: Verificar si el profesional existe y está activo
    cursor.execute("SELECT id_personal, activo FROM personal WHERE id_personal = %s", (reserva.id_personal,))
    profesional = cursor.fetchone()

    if not profesional:
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Error: El profesional con ID {reserva.id_personal} no existe en la base de datos."
        )
    
    if not profesional['activo']:
        cursor.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Error: El profesional con ID {reserva.id_personal} se encuentra inactivo."
        )

    # 2. Validación Síncrona: Verificar si el turno ya está ocupado
    query_check = """
        SELECT id_reserva FROM reserva 
        WHERE id_personal = %s AND fecha_turno = %s AND hora_turno = %s
    """
    cursor.execute(query_check, (reserva.id_personal, reserva.fecha_turno, reserva.hora_turno))
    reserva_existente = cursor.fetchone()
    cursor.close()

    if reserva_existente:
        id_existente = reserva_existente["id_reserva"]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Reserva: {id_existente} ya existe en ese horario. Elimine y reinserte o modifique dicha reserva."
        )

    # 3. Si pasa las validaciones, generar ID y enviar a MQTT
    id_reserva = secrets.randbelow(900000) + 100000
    
    payload_mqtt = {
        "status": "turno_solicitado",
        "turno": {
            "id": id_reserva,
            "idPersonal": reserva.id_personal,
            "email_cliente": reserva.email_solicitante,
            "telefono_cliente": reserva.telefono_solicitante,
            "fecha": reserva.fecha_turno,
            "hora": reserva.hora_turno[:5],
            "estado_reserva": "RESERVADO"
        }
    }
    
    publicar_mqtt("turnos/solicitudes", payload_mqtt)
    
    return {
        "mensaje": "Solicitud validada y enviada a MQTT exitosamente.",
        "turno": {
            "id": id_reserva,
            **reserva.model_dump(),
            "estado_reserva": "RESERVADO"
        }
    }

@router.get("", status_code=status.HTTP_200_OK)
def listar_reservas(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reserva ORDER BY fecha_turno, hora_turno")
    res = cursor.fetchall()
    cursor.close()
    return res

@router.get("/{id_reserva}", status_code=status.HTTP_200_OK)
def obtener_reserva(id_reserva: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    res = cursor.fetchone()
    cursor.close()
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reserva no encontrada")
    return res

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