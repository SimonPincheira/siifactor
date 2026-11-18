-- SIIFactor · Esquema de base de datos (PostgreSQL)
-- Ejecutar como superusuario sobre la base "siifactor".
-- Antes: CREATE USER siifactor_app WITH PASSWORD '<clave>'; CREATE DATABASE siifactor;

CREATE TABLE corredora (id serial PRIMARY KEY, nombre text NOT NULL UNIQUE);

CREATE TABLE usuario (
  id serial PRIMARY KEY, nombre text NOT NULL, correo text NOT NULL UNIQUE,
  hash_clave text NOT NULL,
  rol text NOT NULL CHECK (rol IN ('analista','administrador','supervisor')),
  corredora_id int REFERENCES corredora(id));

CREATE TABLE instrumento (
  id serial PRIMARY KEY, nemo text NOT NULL, descripcion text,
  mercado text NOT NULL, UNIQUE (mercado, nemo));

CREATE TABLE calificacion (
  id serial PRIMARY KEY,
  instrumento_id int NOT NULL REFERENCES instrumento(id),
  corredora_id int REFERENCES corredora(id),
  usuario_id int REFERENCES usuario(id),
  ejercicio int NOT NULL,
  secuencia int NOT NULL CHECK (secuencia > 10000),
  fecha_pago date NOT NULL, descripcion text,
  dividendo numeric(18,2) NOT NULL DEFAULT 0,
  isfut boolean NOT NULL DEFAULT false,
  origen text NOT NULL CHECK (origen IN ('bolsa','manual','archivo')),
  fecha_modificacion timestamptz NOT NULL DEFAULT now(),
  UNIQUE (instrumento_id, ejercicio, secuencia));

CREATE TABLE factor (
  calificacion_id int REFERENCES calificacion(id) ON DELETE CASCADE,
  columna int CHECK (columna BETWEEN 8 AND 37),
  valor numeric(10,8) NOT NULL CHECK (valor BETWEEN 0 AND 1),
  PRIMARY KEY (calificacion_id, columna));

CREATE TABLE monto (
  calificacion_id int REFERENCES calificacion(id) ON DELETE CASCADE,
  columna int CHECK (columna BETWEEN 8 AND 37),
  valor numeric(18,2) NOT NULL CHECK (valor >= 0),
  PRIMARY KEY (calificacion_id, columna));

CREATE TABLE carga_archivo (
  id serial PRIMARY KEY, usuario_id int REFERENCES usuario(id),
  nombre text, tipo text, fecha timestamptz NOT NULL DEFAULT now(),
  filas_ok int, filas_error int);

-- calificacion_id sin clave foránea a propósito: el log se conserva aunque se elimine la calificación.
CREATE TABLE log_auditoria (
  id bigserial PRIMARY KEY, fecha_hora timestamptz NOT NULL DEFAULT now(),
  usuario_id int REFERENCES usuario(id), calificacion_id int,
  operacion text NOT NULL, valor_anterior jsonb, valor_nuevo jsonb);

-- Permisos mínimos: la aplicación puede escribir en el log, pero no modificarlo ni borrarlo.
GRANT SELECT, INSERT, UPDATE, DELETE ON corredora, usuario, instrumento,
  calificacion, factor, monto, carga_archivo TO siifactor_app;
GRANT SELECT, INSERT ON log_auditoria TO siifactor_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO siifactor_app;
