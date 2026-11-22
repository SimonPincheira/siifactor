# SIIFactor · Mantenedor de Calificaciones Tributarias

Proyecto Integrado (INACAP) para **nuam**. Mantenedor web para ingresar, calcular, modificar y cargar masivamente factores de calificaciones tributarias, con registro de auditoría.

## Estado actual
| Componente | Estado |
|---|---|
| Interfaz (prototipo interactivo, HTML/CSS/JS) | Implementada y desplegada en AWS |
| Servidor (EC2, Red Hat, IP elástica, Nginx con HTTPS autofirmado y cabeceras de seguridad) | Operativo |
| Base de datos PostgreSQL (8 tablas, restricciones, índices, permisos mínimos) | Implementada en el servidor |
| Inicio de sesión (administrador, supervisor y analista) y autorización por rol en el servidor | Implementado en `backend/`; despliegue en `docs/backend.md` |
| Datos del mantenedor | Aún en el navegador (`localStorage`); conectarlos a PostgreSQL es la etapa siguiente |

## Estructura del repositorio
```
src/index.html                  Interfaz (con pantalla de inicio de sesión)
backend/app.py                  API Flask: autenticación, roles, CSRF, segregación por corredora
backend/crear_usuario.py        Crea usuarios con la contraseña como hash
backend/test_app.py             Pruebas automatizadas de la API
database/schema.sql             Esquema de la base de datos
database/indices.sql            Índices
database/migracion_login.sql    Columnas para el inicio de sesión
deploy/                         Servicio systemd, configuración de Nginx y plantilla de variables de entorno
docs/despliegue-aws.md          Configuración del servidor paso a paso
docs/backend.md                 API, seguridad, pruebas y despliegue del backend
docs/plan-de-pruebas.md         Plan de pruebas y resultados
docs/seguridad.md               Medidas de seguridad y limitaciones
tests/carga_ejemplo_factores.csv    Archivo de prueba de carga masiva
```

## Funcionalidades
- Búsqueda y filtros por mercado, origen y ejercicio; grilla paginada con salto a una página exacta.
- Ingreso y modificación con cálculo de factores (monto ÷ dividendo, 8 decimales) y validación de que la suma de factores 8 a 16 no supere 1.
- Carga masiva de CSV (36 columnas, separador `;`) con previsualización, rechazo de filas inválidas y actualización por llave.
- Inicio de sesión con roles (Analista, Administrador, Supervisor), con permisos distintos.
- Log de auditoría con filtros, y log del servidor consultable según el rol.
- Segregación por corredora.

## Integrantes
| Nombre | Rol en el proyecto |
|---|---|
| Simón Antonio Pincheira de la Fuente | Proyecto individual: diseño, desarrollo, base de datos, despliegue en AWS, seguridad, pruebas y documentación |

## Limitaciones conocidas
- Los datos del mantenedor aún no se leen ni se guardan en PostgreSQL.
- Certificado HTTPS autofirmado; sin redirección de HTTP a HTTPS.
- Precedencia de la calificación de la corredora sobre la de la bolsa no implementada.
- Cifra de montos por confirmar con nuam (la historia indica 29 y el prototipo usa 30 columnas, 8 a 37).
