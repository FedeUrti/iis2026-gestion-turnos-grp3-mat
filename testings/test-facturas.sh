#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-common.sh"

SUFFIX="$(date +%s)-$$"
EMAIL_TEST="test.facturas.$SUFFIX@example.com"
NOMBRE_TEST="Prueba Facturas $SUFFIX"
FECHA_1="${FECHA_1:-$(date_next_month 0)}"
FECHA_2="${FECHA_2:-$(date_next_month 1)}"
ID_RESERVA_1=""
ID_RESERVA_2=""

cleanup() {
  db_scalar "
    DELETE FROM factura_item
    WHERE id_reserva IN (
      SELECT id_reserva FROM reserva WHERE email_solicitante='$EMAIL_TEST'
    );
    DELETE FROM factura WHERE email_cliente='$EMAIL_TEST';
    DELETE FROM reserva WHERE email_solicitante='$EMAIL_TEST';
    DELETE FROM cliente WHERE email='$EMAIL_TEST';
  " >/dev/null || true
}
trap cleanup EXIT

require_test_environment

printf '[1/5] Crear dos reservas del mismo cliente y período\n'
create_reservation "$EMAIL_TEST" "$NOMBRE_TEST" "$FECHA_1" "10:00:00" 1 1
[[ "$API_STATUS" == "202" ]] || fail "Primer POST devolvió HTTP $API_STATUS: $API_BODY"
ID_RESERVA_1="$(json_value "$API_BODY" 'turno.id')"

create_reservation "$EMAIL_TEST" "$NOMBRE_TEST" "$FECHA_2" "11:00:00" 1 2
[[ "$API_STATUS" == "202" ]] || fail "Segundo POST devolvió HTTP $API_STATUS: $API_BODY"
ID_RESERVA_2="$(json_value "$API_BODY" 'turno.id')"
printf '  OK: reservas %s y %s\n' "$ID_RESERVA_1" "$ID_RESERVA_2"

printf '[2/5] Preparar ambas reservas como atendidas y ejecutar el worker\n'
db_scalar "
  UPDATE reserva
  SET estado_reserva='ATENDIDO'
  WHERE id_reserva IN ($ID_RESERVA_1,$ID_RESERVA_2);
  SELECT ROW_COUNT();
" >/dev/null
process_invoice_worker >/dev/null
FACTURADO="$(db_scalar "
  SELECT COUNT(*) FROM reserva
  WHERE id_reserva IN ($ID_RESERVA_1,$ID_RESERVA_2)
    AND estado_reserva='FACTURADO';
")"
[[ "$FACTURADO" == "2" ]] || fail "El worker facturó $FACTURADO de las 2 reservas."
printf '  OK: ambas reservas pasaron a FACTURADO\n'

printf '[3/5] Verificar una factura mensual con dos ítems\n'
api_request GET "$BASE_URL/facturas?email_cliente=$EMAIL_TEST"
[[ "$API_STATUS" == "200" ]] || fail "GET /facturas devolvió HTTP $API_STATUS."
NUM_FACTURAS="$(json_value "$API_BODY" 'length')"
[[ "$NUM_FACTURAS" == "1" ]] || fail "Se esperaba una factura del período; hay $NUM_FACTURAS."
ID_FACTURA="$(json_value "$API_BODY" '0.id_factura')"
api_request GET "$BASE_URL/facturas/$ID_FACTURA"
[[ "$API_STATUS" == "200" ]] || fail "GET detalle de factura devolvió HTTP $API_STATUS."
ITEMS="$(json_value "$API_BODY" 'items.length')"
[[ "$ITEMS" == "2" ]] || fail "Se esperaban 2 ítems y se obtuvieron $ITEMS."

printf '%s' "$API_BODY" | docker compose exec -T reservas-api python -c '
import json
import sys
from decimal import Decimal

invoice = json.load(sys.stdin)
items = invoice["items"]
assert invoice["email_cliente"].startswith("test.facturas.")
assert len(items) == 2
assert {item["id_reserva"] for item in items} == {int(sys.argv[1]), int(sys.argv[2])}
assert all("subtotal" not in item for item in items)
total_items = sum(Decimal(str(item["precio_unitario"])) for item in items)
assert Decimal(str(invoice["total"])) == total_items, (
    "total factura {} != suma items {}".format(invoice["total"], total_items)
)
' "$ID_RESERVA_1" "$ID_RESERVA_2" || fail "Los ítems o el total de la factura no coinciden."
printf '  OK: factura %s con 2 ítems y total consistente\n' "$ID_FACTURA"

printf '[4/5] Verificar filtro por correo de cliente\n'
api_request GET "$BASE_URL/facturas?email_cliente=$EMAIL_TEST"
[[ "$API_STATUS" == "200" ]] || fail "El filtro de factura devolvió HTTP $API_STATUS."
[[ "$(json_value "$API_BODY" '0.email_cliente')" == "$EMAIL_TEST" ]] \
  || fail "El filtro por email devolvió otra factura."
printf '  OK: factura asociada al correo del cliente\n'

printf '[5/5] Verificar que volver a ejecutar el worker no duplica ítems\n'
process_invoice_worker >/dev/null
ITEMS_FINALES="$(db_scalar "SELECT COUNT(*) FROM factura_item WHERE id_factura=$ID_FACTURA;")"
[[ "$ITEMS_FINALES" == "2" ]] || fail "Se duplicaron o perdieron ítems al repetir el worker."
printf '  OK: siguen existiendo exactamente 2 ítems\n'

printf '\nPruebas de facturación finalizadas correctamente.\n'
