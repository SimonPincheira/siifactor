# Backend de autenticación · SIIFactor (etapa 1)

API en Flask que agrega **inicio de sesión con usuarios en PostgreSQL**, **autorización por rol verificada en el servidor** y **segregación por corredora**. Corre detrás de Nginx (HTTPS) con gunicorn.

```
Navegador ──HTTPS──> Nginx (443) ──/api/──> gunicorn (127.0.0.1:8000) ──> PostgreSQL (127.0.0.1)
                       └── /  (archivos estáticos: src/index.html)
```

## API

| Método y ruta | Roles | Descripción |
|---|---|---|
| POST `/api/login` | público | Valida correo y contraseña; abre la sesión y entrega un token CSRF |
| POST `/api/logout` | sesión | Cierra la sesión (exige token CSRF) |
| GET `/api/me` | sesión | Datos del usuario de la sesión |
| GET `/api/calificaciones` | los tres roles | Calificaciones de la bolsa y de **la corredora de la sesión** (el cliente no elige corredora) |
| GET `/api/auditoria` | administrador, supervisor | Eventos de usuarios de la misma corredora; el analista recibe 403 |

## Medidas de seguridad

- Contraseñas guardadas con hash (scrypt, de Werkzeug); nunca en texto plano ni en el repositorio.
- Bloqueo de la cuenta por 5 minutos tras 5 intentos fallidos; mensaje idéntico para correo inexistente, clave errónea o cuenta bloqueada (no revela qué correos existen).
- Cookie de sesión `HttpOnly`, `Secure` y `SameSite=Strict`; vence a los 30 minutos de inactividad; la sesión se renueva al iniciar sesión.
- Protección CSRF: toda petición que modifica datos exige el token de la sesión (`X-CSRF-Token`).
- Roles verificados en el servidor en cada petición; los accesos denegados quedan en el log.
- Consultas SQL parametrizadas; los errores internos no se muestran al cliente.
- Inicios de sesión, cierres, fallos y accesos denegados se registran en `log_auditoria`.
- El secreto de la sesión y la clave de la base de datos viven en `/etc/siifactor.env` (permisos 600), fuera del repositorio.

## Pruebas

- **Automatizadas (18 casos)** en `backend/test_app.py`, con una base de datos simulada: `cd backend && SIIFACTOR_SECRET_KEY=prueba python -m unittest -v test_app`.
- **Extremo a extremo** en un navegador (18 comprobaciones): login correcto e incorrecto, permisos por rol, recarga, cierre de sesión, CSRF y bloqueo.
- Las consultas SQL se prueban en el servidor contra PostgreSQL (ver la sección siguiente).

## Despliegue en el servidor (resumen)

1. `sudo dnf install -y python3-pip git` y crear el usuario de sistema `siifactor`.
2. `sudo git clone https://github.com/SimonPincheira/siifactor.git /opt/siifactor`.
3. Entorno virtual en `/opt/siifactor-venv` e instalación de `backend/requirements.txt`.
4. Migración: `sudo -u postgres psql -d siifactor -f /opt/siifactor/database/migracion_login.sql`.
5. `/etc/siifactor.env` a partir de `deploy/siifactor.env.example`.
6. Crear los usuarios con `backend/crear_usuario.py` (la contraseña se pide por teclado).
7. Servicio systemd `deploy/siifactor.service`.
8. Proxy de Nginx `deploy/nginx-siifactor-ssl.conf` y `setsebool -P httpd_can_network_connect 1`.
9. Publicar `src/index.html`.

## Limitaciones de esta etapa

- La interfaz usa la sesión del servidor (identidad y rol), pero **los datos de las calificaciones siguen en el navegador**; la conexión del mantenedor con PostgreSQL es la etapa siguiente.
- Los archivos estáticos (`index.html`) se sirven sin sesión; lo protegido son los datos de la API.
- No hay límite de intentos por dirección IP ni segundo factor de autenticación.
- El certificado HTTPS es autofirmado.
