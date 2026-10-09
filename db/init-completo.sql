-- Esquema inicial completo. MySQL lo ejecuta al inicializar un volumen vacio.

CREATE TABLE IF NOT EXISTS establecimiento (
    id_establecimiento INT AUTO_INCREMENT PRIMARY KEY,
    nombre_comercial VARCHAR(150) NOT NULL,
    direccion VARCHAR(255) NOT NULL,
    telefono VARCHAR(50) NOT NULL,
    correo_electronico VARCHAR(100) NOT NULL,
    horario_apertura TIME NOT NULL,
    horario_cierre TIME NOT NULL,
    -- Impide duplicar el nombre comercial
    CONSTRAINT uk_establecimiento_nombre UNIQUE (nombre_comercial)
);

CREATE TABLE IF NOT EXISTS personal (
    id_personal INT AUTO_INCREMENT PRIMARY KEY,
    id_establecimiento INT NOT NULL,
    nombre VARCHAR(150) NOT NULL,
    apellido VARCHAR(150) NOT NULL DEFAULT '', -- DEFAULT '' evita NULL para que UNIQUE aplique
    email VARCHAR(100),
    telefono VARCHAR(50),
    cargo VARCHAR(100),
    especialidad VARCHAR(100) DEFAULT 'General',
    costo_consulta NUMERIC(10, 2) DEFAULT 0.00,
    duracion_atencion INT NOT NULL DEFAULT 30,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_establecimiento FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento) ON DELETE CASCADE,
    CONSTRAINT ck_duracion_atencion CHECK (duracion_atencion = 30),
    -- Impide duplicar la combinación de nombre y apellido
    CONSTRAINT uk_personal_nombre_apellido UNIQUE (nombre, apellido)
);

CREATE TABLE IF NOT EXISTS cliente (
    email VARCHAR(100) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL DEFAULT '',
    telefono VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS reserva (
    id_reserva INT PRIMARY KEY,
    fecha_reservado TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_solicitante VARCHAR(100) NOT NULL,
    telefono_solicitante VARCHAR(50) NOT NULL,
    id_personal INT NOT NULL,
    id_establecimiento INT NOT NULL,
    fecha_turno DATE NOT NULL,
    hora_turno TIME NOT NULL,
    estado_reserva ENUM(
        'RESERVADO', 'CANCELADO', 'FINALIZADO', 'PENDIENTE',
        'RECHAZADO_SOLICITUD_NO_VALIDA', 'AGENDADO',
        'RECHAZADO_TURNO_OCUPADO', 'ATENDIDO', 'FACTURADO'
    ) NOT NULL DEFAULT 'RESERVADO',
    id_personal_ocupado INT GENERATED ALWAYS AS (
        CASE
            WHEN estado_reserva IN ('RESERVADO', 'FINALIZADO', 'AGENDADO', 'ATENDIDO', 'FACTURADO')
            THEN id_personal
            ELSE NULL
        END
    ) STORED,
    CONSTRAINT fk_reserva_cliente FOREIGN KEY (email_solicitante) REFERENCES cliente(email),
    CONSTRAINT fk_personal FOREIGN KEY (id_personal) REFERENCES personal(id_personal),
    CONSTRAINT fk_reserva_establecimiento FOREIGN KEY (id_establecimiento) REFERENCES establecimiento(id_establecimiento),
    CONSTRAINT uk_personal_fecha_hora_activa UNIQUE (id_personal_ocupado, fecha_turno, hora_turno)
);

CREATE INDEX idx_reserva_personal_fecha ON reserva(id_personal, fecha_turno);

CREATE TABLE IF NOT EXISTS factura (
    id_factura INT AUTO_INCREMENT PRIMARY KEY,
    email_cliente VARCHAR(100) NOT NULL,
    periodo CHAR(7) NOT NULL,
    fecha_emision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_factura_cliente FOREIGN KEY (email_cliente) REFERENCES cliente(email),
    CONSTRAINT uk_factura_cliente_periodo UNIQUE (email_cliente, periodo)
);

CREATE TABLE IF NOT EXISTS factura_item (
    id_item INT AUTO_INCREMENT PRIMARY KEY,
    id_factura INT NOT NULL,
    id_reserva INT NOT NULL,
    id_personal INT NOT NULL,
    nombre_profesional VARCHAR(301) NOT NULL,
    especialidad VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255) NOT NULL,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    CONSTRAINT uk_factura_item_reserva UNIQUE (id_reserva),
    CONSTRAINT fk_factura_item_factura
        FOREIGN KEY (id_factura) REFERENCES factura(id_factura) ON DELETE CASCADE,
    CONSTRAINT fk_factura_item_reserva
        FOREIGN KEY (id_reserva) REFERENCES reserva(id_reserva),
    CONSTRAINT fk_factura_item_personal
        FOREIGN KEY (id_personal) REFERENCES personal(id_personal)
);

INSERT IGNORE INTO establecimiento (
    nombre_comercial, direccion, telefono, correo_electronico,
    horario_apertura, horario_cierre
) VALUES
    ('Centro Salud Uru', 'Av. 18 de Julio 1234', '29000000',
     'contacto@centrosalud.uy', '09:00', '17:00'),
    ('Clinica Norte Salud', 'Av. Rivera 2450', '24870001',
     'contacto@nortesalud.uy', '08:00', '18:00'),
    ('Clinica Sur Salud', 'Bulevar Artigas 1820', '24870002',
     'contacto@sursalud.uy', '08:00', '18:00'),
    ('Clinica Este Salud', 'Av. Italia 3260', '24870003',
     'contacto@estesalud.uy', '09:00', '19:00');

INSERT IGNORE INTO personal (
    id_establecimiento, nombre, apellido, email, telefono, cargo, especialidad, costo_consulta, duracion_atencion, activo
) VALUES
    (1, 'Ana', 'Pereira', 'ana@centrosalud.uy', '099111222', 'Médica', 'Medicina general', 1200.00, 30, TRUE),
    (1, 'Bruno', 'Silva', 'bruno@centrosalud.uy', '099222333', 'Odontólogo', 'Odontologia', 1500.00, 30, TRUE),
    (1, 'Carla', 'Rodriguez', 'carla@centrosalud.uy', '099333444', 'Psicóloga', 'Psicologia', 1300.00, 30, TRUE),
    (2, 'Marcos', 'Lopez', 'marcos@nortesalud.uy', '099555111', 'Médico', 'Medicina general', 1250.00, 30, TRUE),
    (2, 'Valentina', 'Castro', 'valentina@nortesalud.uy', '099555222', 'Odontóloga', 'Odontologia', 1550.00, 30, TRUE),
    (2, 'Martin', 'Suarez', 'martin@nortesalud.uy', '099555333', 'Psicólogo', 'Psicologia', 1350.00, 30, TRUE),
    (3, 'Sofia', 'Fernandez', 'sofia@sursalud.uy', '099666111', 'Médica', 'Medicina general', 1300.00, 30, TRUE),
    (3, 'Nicolas', 'Mendez', 'nicolas@sursalud.uy', '099666222', 'Dermatólogo', 'Dermatologia', 1650.00, 30, TRUE),
    (3, 'Lucia', 'Cabrera', 'lucia@sursalud.uy', '099666333', 'Psicóloga', 'Psicologia', 1400.00, 30, TRUE),
    (4, 'Camila', 'Torres', 'camila@estesalud.uy', '099777111', 'Médica', 'Medicina general', 1350.00, 30, TRUE),
    (4, 'Santiago', 'Nunez', 'santiago@estesalud.uy', '099777222', 'Odontólogo', 'Odontologia', 1600.00, 30, TRUE),
    (4, 'Julieta', 'Acosta', 'julieta@estesalud.uy', '099777333', 'Dermatóloga', 'Dermatologia', 1700.00, 30, TRUE);