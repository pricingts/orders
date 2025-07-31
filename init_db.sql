CREATE TABLE IF NOT EXISTS operaciones (
    id_operacion SERIAL PRIMARY KEY,
    no_solicitud VARCHAR(50) UNIQUE NOT NULL,   -- Identificador único del caso
    comercial VARCHAR(100),                     -- Nombre del comercial
    comentarios TEXT,                           -- Comentarios finales
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cargas (
    id_carga SERIAL PRIMARY KEY,
    id_operacion INT NOT NULL REFERENCES operaciones(id_operacion) ON DELETE CASCADE,
    bl_awb VARCHAR(100),                        -- BL/AWB
    tipo_carga VARCHAR(50) NOT NULL,            -- Contenedor o Carga suelta
    pol_aol VARCHAR(100),                       -- Puerto origen/aeropuerto origen
    pod_aod VARCHAR(100),                       -- Puerto destino/aeropuerto destino
    shipper VARCHAR(100),
    consignee VARCHAR(100),
    detalle JSONB,                              -- Contenedores o carga suelta
    unidad_medida VARCHAR(10),                  -- Para carga suelta (KG, CBM, etc.)
    cantidad_suelta DECIMAL(12, 2),
    referencia TEXT         
);

CREATE TABLE IF NOT EXISTS ventas (
    id_venta SERIAL PRIMARY KEY,
    id_operacion INT NOT NULL REFERENCES operaciones(id_operacion) ON DELETE CASCADE,
    cliente VARCHAR(100) NOT NULL,              -- Cliente asociado a la venta
    concepto VARCHAR(100) NOT NULL,             -- Concepto
    cantidad DECIMAL(12, 2) DEFAULT 0,          -- Quantity
    tarifa DECIMAL(12, 2) DEFAULT 0,            -- Rate
    monto DECIMAL(12, 2) DEFAULT 0,             -- Total (cantidad * tarifa)
    moneda VARCHAR(10) DEFAULT 'USD'   ,
    comentarios TEXT DEFAULT NULL      
);

CREATE TABLE IF NOT EXISTS costos (
    id_costo SERIAL PRIMARY KEY,
    id_operacion INT NOT NULL REFERENCES operaciones(id_operacion) ON DELETE CASCADE,
    concepto VARCHAR(100) NOT NULL,             -- Concepto del costo
    cantidad DECIMAL(12, 2) DEFAULT 0,          -- Quantity
    tarifa DECIMAL(12, 2) DEFAULT 0,            -- Rate
    monto DECIMAL(12, 2) DEFAULT 0,             -- Total (cantidad * tarifa)
    moneda VARCHAR(10) DEFAULT 'USD',
    comentarios TEXT DEFAULT NULL         
);

CREATE TABLE IF NOT EXISTS notas_credito (
    id_nc SERIAL PRIMARY KEY,
    id_operacion INT NOT NULL REFERENCES operaciones(id_operacion) ON DELETE CASCADE,
    no_factura VARCHAR(50) NOT NULL,            -- Número de factura
    tipo_nc VARCHAR(50) NOT NULL,               -- Tipo de nota crédito (Valor Parcial / Valor Total)
    valor_nc DECIMAL(12, 2) DEFAULT 0           -- Valor de la nota crédito
);