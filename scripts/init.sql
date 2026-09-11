DROP TABLE IF EXISTS reserva;
DROP TABLE IF EXISTS personal;
DROP TABLE IF EXISTS establecimiento;
DROP TYPE IF EXISTS enum_estado_reserva;

CREATE TYPE enum_estado_reserva AS ENUM ('RESERVADO', 'CANCELADO', 'FINALIZADO');

CREATE TABLE IF NOT EXISTS establecimiento (
    id_establecimiento SERIAL PRIMARY KEY,
    nombre_comercial VARCHAR(150) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    telefono VARCHAR(50) NOT NULL,
    correo_electronico VARCHAR(100) NOT NULL,
    horario_apertura TIME NOT NULL,
    horario_cierre TIME NOT NULL
);

CREATE TABLE IF NOT EXISTS personal (
    id_personal SERIAL PRIMARY KEY,
    id_establecimiento INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    especialidad VARCHAR(100) NOT NULL,
    costo_consulta NUMERIC(10, 2) NOT NULL,
    duracion_atencion INT NOT NULL DEFAULT 30,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_establecimiento FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reserva (
    id_reserva SERIAL PRIMARY KEY,
    fecha_reservado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_solicitante VARCHAR(100) NOT NULL,
    telefono_solicitante VARCHAR(50) NOT NULL,
    id_personal INT NOT NULL,
    fecha_turno DATE NOT NULL,
    hora_turno TIME NOT NULL,
    estado_reserva enum_estado_reserva NOT NULL DEFAULT 'RESERVADO',
    CONSTRAINT fk_personal FOREIGN KEY (id_personal) REFERENCES personal(id),
    -- Regla de negocio: No pueden existir dos turnos para el mismo profesional en la misma fecha y hora
    CONSTRAINT uk_personal_fecha_hora UNIQUE (id_personal, fecha_turno, hora_turno)
);

CREATE INDEX idx_reserva_personal_fecha ON reserva(id_personal, fecha_turno);