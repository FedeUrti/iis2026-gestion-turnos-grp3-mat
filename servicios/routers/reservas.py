import secrets
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

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def crear_reserva(reserva: ReservaCreate):
    id_reserva = secrets.randbelow(900000) + 100000
    payload = {
        "status": "turno_solicitado",
        "turno": {"id": id_reserva, **reserva.model_dump()}
    }
    publicar_mqtt("turnos/solicitudes", payload)
    return {"mensaje": "Solicitud publicada", "turno": payload["turno"]}

@router.get("")
def listar_reservas(db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reserva ORDER BY fecha_turno")
    res = cursor.fetchall()
    cursor.close()
    return res

@router.get("/{id_reserva}")
def obtener_reserva(id_reserva: int, db = Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    res = cursor.fetchone()
    cursor.close()
    if not res:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    return res