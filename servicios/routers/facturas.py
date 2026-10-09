from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr

from database import get_db

router = APIRouter(prefix="/facturas", tags=["facturas"])


@router.get("", status_code=status.HTTP_200_OK)
def listar_facturas(email_cliente: EmailStr | None = None, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        if email_cliente is None:
            cursor.execute(
                """
                SELECT f.*, c.nombre
                FROM factura f
                JOIN cliente c ON c.email = f.email_cliente
                ORDER BY f.periodo DESC, f.email_cliente
                """
            )
        else:
            cursor.execute(
                """
                SELECT f.*, c.nombre
                FROM factura f
                JOIN cliente c ON c.email = f.email_cliente
                WHERE f.email_cliente = %s
                ORDER BY f.periodo DESC, f.id_factura DESC
                """,
                (str(email_cliente),),
            )
        return cursor.fetchall()
    finally:
        cursor.close()


@router.get("/{id_factura}", status_code=status.HTTP_200_OK)
def obtener_factura(id_factura: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT f.*, c.nombre
            FROM factura f
            JOIN cliente c ON c.email = f.email_cliente
            WHERE f.id_factura = %s
            """,
            (id_factura,),
        )
        factura = cursor.fetchone()
        if not factura:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Factura no encontrada",
            )

        cursor.execute(
            """
            SELECT id_item, id_reserva, id_personal, nombre_profesional,
                   especialidad, descripcion, precio_unitario
            FROM factura_item
            WHERE id_factura = %s
            ORDER BY id_item
            """,
            (id_factura,),
        )
        factura["items"] = cursor.fetchall()
        return factura
    finally:
        cursor.close()
