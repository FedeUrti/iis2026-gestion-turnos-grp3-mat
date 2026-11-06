#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

usage() {
  cat <<'EOF'
Uso:
  bash scripts/consultar-bd.sh [todo|establecimientos|personal|clientes|reservas|facturas]

Consulta datos de solo lectura en MySQL usando el contenedor db de Docker Compose.
EOF
}

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 2
fi

tabla="${1:-todo}"
case "$tabla" in
  todo|establecimientos|personal|clientes|reservas|facturas) ;;
  *)
    printf 'Tabla desconocida: %s\n' "$tabla" >&2
    usage >&2
    exit 2
    ;;
esac

if ! command -v docker >/dev/null 2>&1; then
  printf 'No se encontró Docker. Instala/inicia Docker Desktop o Docker Engine.\n' >&2
  exit 1
fi

if ! docker compose ps --status running --services 2>/dev/null | grep -qx db; then
  printf 'MySQL no está iniciado. Ejecuta primero: docker compose up -d\n' >&2
  exit 1
fi

consultar() {
  local titulo="$1"
  local sql="$2"

  printf '\n=== %s ===\n' "$titulo"
  docker compose exec -T db sh -c \
    'MYSQL_PWD="$MYSQL_PASSWORD" exec mysql --user="$MYSQL_USER" "$MYSQL_DATABASE" --table -e "$1"' \
    _ "$sql"
}

case "$tabla" in
  todo)
    consultar "Establecimientos" \
      "SELECT id_establecimiento, nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre FROM establecimiento ORDER BY id_establecimiento;"
    consultar "Personal" \
      "SELECT id_personal, id_establecimiento, nombre, apellido, especialidad, costo_consulta, duracion_atencion, activo FROM personal ORDER BY id_establecimiento, apellido, nombre;"
    consultar "Clientes" \
      "SELECT email, nombre, telefono FROM cliente ORDER BY email;"
    consultar "Reservas" \
      "SELECT id_reserva, fecha_reservado, email_solicitante, telefono_solicitante, id_establecimiento, id_personal, fecha_turno, hora_turno, estado_reserva FROM reserva ORDER BY fecha_turno, hora_turno;"
    consultar "Facturas e ítems" \
      "SELECT f.id_factura, c.nombre, f.email_cliente, f.periodo, f.total, i.id_reserva, i.nombre_profesional, i.descripcion, i.precio_unitario FROM factura f JOIN cliente c ON c.email = f.email_cliente LEFT JOIN factura_item i ON i.id_factura = f.id_factura ORDER BY f.periodo, f.email_cliente, i.id_item;"
    ;;
  establecimientos)
    consultar "Establecimientos" \
      "SELECT id_establecimiento, nombre_comercial, direccion, telefono, correo_electronico, horario_apertura, horario_cierre FROM establecimiento ORDER BY id_establecimiento;"
    ;;
  personal)
    consultar "Personal" \
      "SELECT id_personal, id_establecimiento, nombre, apellido, especialidad, costo_consulta, duracion_atencion, activo FROM personal ORDER BY id_establecimiento, apellido, nombre;"
    ;;
  clientes)
    consultar "Clientes" \
      "SELECT email, nombre, telefono FROM cliente ORDER BY email;"
    ;;
  reservas)
    consultar "Reservas" \
      "SELECT id_reserva, fecha_reservado, email_solicitante, telefono_solicitante, id_establecimiento, id_personal, fecha_turno, hora_turno, estado_reserva FROM reserva ORDER BY fecha_turno, hora_turno;"
    ;;
  facturas)
    consultar "Facturas e ítems" \
      "SELECT f.id_factura, c.nombre, f.email_cliente, f.periodo, f.total, i.id_reserva, i.nombre_profesional, i.descripcion, i.precio_unitario FROM factura f JOIN cliente c ON c.email = f.email_cliente LEFT JOIN factura_item i ON i.id_factura = f.id_factura ORDER BY f.periodo, f.email_cliente, i.id_item;"
    ;;
esac
