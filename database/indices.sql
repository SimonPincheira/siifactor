-- SIIFactor · Índices sobre las columnas de filtro y consulta más frecuentes.
-- Las claves primarias y las restricciones UNIQUE ya crean sus propios índices.
CREATE INDEX idx_calificacion_corredora   ON calificacion(corredora_id);
CREATE INDEX idx_calificacion_ejercicio   ON calificacion(ejercicio);
CREATE INDEX idx_calificacion_instrumento ON calificacion(instrumento_id);
CREATE INDEX idx_instrumento_mercado      ON instrumento(mercado);
CREATE INDEX idx_log_fecha                ON log_auditoria(fecha_hora);
CREATE INDEX idx_log_calificacion         ON log_auditoria(calificacion_id);
