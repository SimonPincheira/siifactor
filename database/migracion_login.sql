-- SIIFactor · Migración para el inicio de sesión (ejecutar como superusuario sobre la base siifactor).
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS intentos_fallidos int NOT NULL DEFAULT 0;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS bloqueado_hasta timestamptz;
ALTER TABLE usuario ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;
