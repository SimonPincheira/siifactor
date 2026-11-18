# Seguridad · SIIFactor

Resumen de las medidas de seguridad aplicadas, cómo se verificaron y qué queda pendiente. Los casos de prueba citados (SE, BD, EN) están detallados en `plan-de-pruebas.md`.

## Medidas implementadas

| Capa | Medida | Verificación |
|---|---|---|
| Red | Grupo de seguridad `sgsiifactor`: HTTP (80) y HTTPS (443) abiertos; SSH (22) solo desde la IP del administrador; PostgreSQL (5432) no expuesto | SE-03, SE-04, SE-05 |
| Transporte | HTTPS con TLS 1.2 y 1.3 (certificado autofirmado) | SE-06, SE-06b |
| Servidor web | `server_tokens off` y cabeceras `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Content-Security-Policy` | SE-07, SE-09 |
| Interfaz | Escape de todo dato mostrado en la grilla y en el log (previene XSS) | SE-01, SE-02b |
| Interfaz | Validación de cada fila de la carga masiva: mercado, ejercicio, fecha, formato del instrumento, secuencia, suma de factores y número de columnas | SE-02, CM-01 |
| Interfaz | Rechazo de instrumentos y descripciones que comienzan con `=`, `+`, `-` o `@` (inyección de fórmulas) | SE-02 |
| Interfaz | Permisos por rol (Analista, Administrador, Supervisor), comprobados también al ejecutar cada acción | RO-01 a RO-04 |
| Base de datos | Restricciones CHECK y llave única que vuelven a exigir las reglas de negocio | BD-02 a BD-06 |
| Base de datos | Cuenta de aplicación con permisos mínimos: puede leer e insertar en el log, pero no modificarlo ni borrarlo | BD-07 a BD-09 |
| Operación | Respaldo y restauración de la base de datos | EN-02 |
| Repositorio | `.gitignore` excluye claves privadas (`*.pem`) y archivos `.env`; no se versionan contraseñas | Revisión del repositorio |

## Hallazgos corregidos durante las pruebas

| Hallazgo | Causa | Corrección |
|---|---|---|
| HTML inyectado mediante el mercado de un CSV (SE-02b) | El campo no se escapaba ni se validaba | Escape de todos los campos y validación de formato |
| Fórmula aceptada en un CSV (SE-02) | No existía el filtro prometido | Validación del instrumento y rechazo de descripciones que inician con carácter de fórmula |
| Sin HTTPS (SE-06) | Puerto abierto, pero Nginx sin certificado | Certificado autofirmado y configuración del puerto 443 |
| Versión del servidor visible y sin cabeceras (SE-07) | Configuración por defecto de Nginx | Cabeceras de seguridad y ocultar la versión |

## Limitaciones conocidas

- **La autorización por rol es una simulación**: el rol se elige con un menú y no hay inicio de sesión. Sin un backend, un usuario podría saltarse la restricción, porque solo existe en el navegador.
- **El certificado HTTPS es autofirmado**: cifra el tráfico, pero el navegador no confía en él (SE-08). El puerto 80 sigue sirviendo el sitio sin cifrar.
- **La política de contenido permite `unsafe-inline`**, porque el prototipo usa scripts y estilos en línea.
- **La interfaz no usa la base de datos**: guarda los datos en el navegador, por lo que las validaciones del servidor aún no se aplican a lo que ingresa el usuario.
- **El respaldo es manual** y se guarda en el mismo servidor.

## Recomendaciones

1. Backend conectado a PostgreSQL, con consultas parametrizadas y validación en el servidor.
2. Inicio de sesión con contraseñas con hash y sesiones con vencimiento; verificar el rol en el servidor.
3. Dominio con certificado de una autoridad (por ejemplo Let's Encrypt), redirección de HTTP a HTTPS y HSTS.
4. Quitar `unsafe-inline` de la política de contenido separando scripts y estilos en archivos.
5. Automatizar los respaldos y copiarlos fuera del servidor (por ejemplo a S3).
