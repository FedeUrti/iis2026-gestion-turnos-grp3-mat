#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-common.sh"

SUFFIX="$(date +%s)-$$"
EMAIL_OK="test.reservas.$SUFFIX@example.com"
EMAIL_DUP="test.reservas.duplicada.$SUFFIX@example.com"
EMAIL_OK_2="test.reservas.valida2.$SUFFIX@example.com"
EMAIL_OK_3="test.reservas.valida3.$SUFFIX@example.com"
EMAIL_INVALID="test.reservas.invalida.$SUFFIX@example.com"
EMAIL_BADREF="test.reservas.referencia.$SUFFIX@example.com"
FECHA_HORA_OK="$(datetime_minutes_from_now 2)"
FECHA_OK="${FECHA_HORA_OK% *}"
HORA_OK="${FECHA_HORA_OK#* }"
FECHA_HORA_OK_2="$(datetime_minutes_from_now 3)"
FECHA_OK_2="${FECHA_HORA_OK_2% *}"
HORA_OK_2="${FECHA_HORA_OK_2#* }"
FECHA_HORA_OK_3="$(datetime_minutes_from_now 4)"
FECHA_OK_3="${FECHA_HORA_OK_3% *}"
HORA_OK_3="${FECHA_HORA_OK_3#* }"

cleanup() {
  local email_list
  email_list="'$EMAIL_OK','$EMAIL_DUP','$EMAIL_OK_2','$EMAIL_OK_3','$EMAIL_INVALID','$EMAIL_BADREF'"
  db_scalar "DELETE FROM reserva WHERE email_solicitante IN ($email_list); DELETE FROM cliente WHERE email IN ($email_list);" \
    >/dev/null || true
}
trap cleanup EXIT

require_test_environment

NOMBRE_EN_RESERVA="$(db_scalar "
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema=DATABASE() AND table_name='reserva' AND column_name='nombre';
")"
[[ "$NOMBRE_EN_RESERVA" == "0" ]] || fail "La reserva no debe almacenar el nombre del cliente."

assert_customer_saved() {
  local email="$1"
  local name="$2"
  local count

  count="$(db_scalar "SELECT COUNT(*) FROM cliente WHERE email='$email' AND nombre='$name';")"
  [[ "$count" == "1" ]] || fail "El nombre del cliente no quedó guardado en cliente para $email."
}

printf '[1/6] Reserva válida, al menos dos minutos en el futuro\n'
create_reservation "$EMAIL_OK" "Prueba Reservas $SUFFIX" "$FECHA_OK" "$HORA_OK"
[[ "$API_STATUS" == "202" ]] || fail "POST válido devolvió HTTP $API_STATUS: $API_BODY"
ID_OK="$(json_value "$API_BODY" 'turno.id')"
assert_customer_saved "$EMAIL_OK" "Prueba Reservas $SUFFIX"
process_reservation_worker
api_request GET "$BASE_URL/reservas/$ID_OK"
[[ "$API_STATUS" == "200" ]] || fail "GET de reserva devolvió HTTP $API_STATUS."
ESTADO="$(json_value "$API_BODY" 'estado_reserva')"
[[ "$ESTADO" == "AGENDADO" ]] || fail "Se esperaba AGENDADO y se obtuvo $ESTADO."
printf '  OK: reserva %s -> %s\n' "$ID_OK" "$ESTADO"

printf '[2/6] Un horario duplicado se rechaza\n'
create_reservation "$EMAIL_DUP" "Prueba Duplicada $SUFFIX" "$FECHA_OK" "$HORA_OK"
[[ "$API_STATUS" == "202" ]] || fail "POST duplicado devolvió HTTP $API_STATUS."
ID_DUP="$(json_value "$API_BODY" 'turno.id')"
assert_customer_saved "$EMAIL_DUP" "Prueba Duplicada $SUFFIX"
process_reservation_worker
api_request GET "$BASE_URL/reservas/$ID_DUP"
ESTADO_DUP="$(json_value "$API_BODY" 'estado_reserva')"
[[ "$ESTADO_DUP" == "RECHAZADO_TURNO_OCUPADO" ]] \
  || fail "Se esperaba RECHAZADO_TURNO_OCUPADO y se obtuvo $ESTADO_DUP."
printf '  OK: reserva %s -> %s\n' "$ID_DUP" "$ESTADO_DUP"

printf '[3/6] Segunda reserva válida con otro profesional\n'
create_reservation "$EMAIL_OK_2" "Prueba Reservas 2 $SUFFIX" "$FECHA_OK_2" "$HORA_OK_2" 1 2
[[ "$API_STATUS" == "202" ]] || fail "POST de segunda reserva válida devolvió HTTP $API_STATUS."
ID_OK_2="$(json_value "$API_BODY" 'turno.id')"
assert_customer_saved "$EMAIL_OK_2" "Prueba Reservas 2 $SUFFIX"
process_reservation_worker
api_request GET "$BASE_URL/reservas/$ID_OK_2"
ESTADO_OK_2="$(json_value "$API_BODY" 'estado_reserva')"
[[ "$ESTADO_OK_2" == "AGENDADO" ]] || fail "Se esperaba AGENDADO y se obtuvo $ESTADO_OK_2."
printf '  OK: reserva %s -> %s\n' "$ID_OK_2" "$ESTADO_OK_2"

printf '[4/6] Tercera reserva válida con otro profesional\n'
create_reservation "$EMAIL_OK_3" "Prueba Reservas 3 $SUFFIX" "$FECHA_OK_3" "$HORA_OK_3" 1 3
[[ "$API_STATUS" == "202" ]] || fail "POST de tercera reserva válida devolvió HTTP $API_STATUS."
ID_OK_3="$(json_value "$API_BODY" 'turno.id')"
assert_customer_saved "$EMAIL_OK_3" "Prueba Reservas 3 $SUFFIX"
process_reservation_worker
api_request GET "$BASE_URL/reservas/$ID_OK_3"
ESTADO_OK_3="$(json_value "$API_BODY" 'estado_reserva')"
[[ "$ESTADO_OK_3" == "AGENDADO" ]] || fail "Se esperaba AGENDADO y se obtuvo $ESTADO_OK_3."
printf '  OK: reserva %s -> %s\n' "$ID_OK_3" "$ESTADO_OK_3"

printf '[5/6] Fecha y hora pasadas se rechazan\n'
PASADO="$(datetime_minutes_ago 5)"
FECHA_PASADA="${PASADO% *}"
HORA_PASADA="${PASADO#* }"
create_reservation "$EMAIL_INVALID" "Prueba Pasada $SUFFIX" "$FECHA_PASADA" "$HORA_PASADA"
[[ "$API_STATUS" == "202" ]] || fail "POST de turno pasado devolvió HTTP $API_STATUS."
ID_PASADO="$(json_value "$API_BODY" 'turno.id')"
assert_customer_saved "$EMAIL_INVALID" "Prueba Pasada $SUFFIX"
process_reservation_worker
api_request GET "$BASE_URL/reservas/$ID_PASADO"
ESTADO_PASADO="$(json_value "$API_BODY" 'estado_reserva')"
[[ "$ESTADO_PASADO" == "RECHAZADO_SOLICITUD_NO_VALIDA" ]] \
  || fail "Se esperaba RECHAZADO_SOLICITUD_NO_VALIDA y se obtuvo $ESTADO_PASADO."
printf '  OK: reserva %s -> %s\n' "$ID_PASADO" "$ESTADO_PASADO"

RESERVAS_CREADAS="$(db_scalar "SELECT COUNT(*) FROM reserva WHERE email_solicitante IN ('$EMAIL_OK','$EMAIL_DUP','$EMAIL_OK_2','$EMAIL_OK_3','$EMAIL_INVALID');")"
[[ "$RESERVAS_CREADAS" == "5" ]] || fail "Se esperaban 5 reservas insertadas y hay $RESERVAS_CREADAS."

printf '[6/6] Referencias inválidas devuelven 400 sin crear cliente ni reserva\n'
create_reservation "$EMAIL_BADREF" "Cliente No Valido" "$FECHA_OK" "$HORA_OK" 999999 999999
[[ "$API_STATUS" == "400" ]] || fail "Se esperaba HTTP 400 y se obtuvo $API_STATUS."
CLIENTE_CREADO="$(db_scalar "SELECT COUNT(*) FROM cliente WHERE email='$EMAIL_BADREF';")"
[[ "$CLIENTE_CREADO" == "0" ]] || fail "Una referencia inválida dejó un cliente guardado."
RESERVAS_INVALIDAS="$(db_scalar "SELECT COUNT(*) FROM reserva WHERE email_solicitante='$EMAIL_BADREF';")"
[[ "$RESERVAS_INVALIDAS" == "0" ]] || fail "La referencia inválida insertó una reserva."
printf '  OK: HTTP 400, no se insertaron cliente ni reserva\n'

printf '\nPruebas de reservas finalizadas correctamente.\n'
