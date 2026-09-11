DROP TABLE IF EXISTS reserva;
DROP TABLE IF EXISTS personal;
DROP TABLE IF EXISTS establecimiento;

CREATE TABLE IF NOT EXISTS establecimiento (
    id_establecimiento INT AUTO_INCREMENT PRIMARY KEY,
    nombre_comercial VARCHAR(150) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    telefono VARCHAR(50) NOT NULL,
    correo_electronico VARCHAR(100) NOT NULL,
    horario_apertura TIME NOT NULL,
    horario_cierre TIME NOT NULL
);

CREATE TABLE IF NOT EXISTS personal (
    id_personal INT AUTO_INCREMENT PRIMARY KEY,
    id_establecimiento INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    especialidad VARCHAR(100) NOT NULL,
    costo_consulta NUMERIC(10, 2) NOT NULL,
    duracion_atencion INT NOT NULL DEFAULT 30,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_establecimiento FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento) ON DELETE CASCADE,
    CONSTRAINT ck_duracion_atencion CHECK (duracion_atencion = 30)
);

CREATE TABLE IF NOT EXISTS reserva (
    id_reserva INT AUTO_INCREMENT PRIMARY KEY,
    fecha_reservado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_solicitante VARCHAR(100) NOT NULL,
    telefono_solicitante VARCHAR(50) NOT NULL,
    id_personal INT NOT NULL,
    fecha_turno DATE NOT NULL,
    hora_turno TIME NOT NULL,
    estado_reserva ENUM('RESERVADO', 'CANCELADO', 'FINALIZADO') NOT NULL DEFAULT 'RESERVADO',
    CONSTRAINT fk_personal FOREIGN KEY (id_personal) REFERENCES personal(id_personal),
    -- Regla de negocio: No pueden existir dos turnos para el mismo profesional en la misma fecha y hora
    CONSTRAINT uk_personal_fecha_hora UNIQUE (id_personal, fecha_turno, hora_turno)
);

CREATE INDEX idx_reserva_personal_fecha ON reserva(id_personal, fecha_turno);

INSERT INTO establecimiento (
    nombre_comercial, direccion, telefono, correo_electronico,
    horario_apertura, horario_cierre
) VALUES (
    'Centro Salud Uru', 'Av. 18 de Julio 1234', '29000000',
    'contacto@centrosalud.uy', '09:00', '17:00'
);

INSERT INTO personal (
    id_establecimiento, nombre, especialidad, costo_consulta,
    duracion_atencion, activo
) VALUES
    (1, 'Ana Pereira', 'Medicina general', 1200.00, 30, TRUE),
    (1, 'Bruno Silva', 'Odontologia', 1500.00, 30, TRUE),
    (1, 'Carla Rodriguez', 'Psicologia', 1300.00, 30, TRUE),
    (1, 'Diego Mendez', 'Dermatologia', 1600.00, 30, FALSE);