# SIIFactor · Mantenedor de Calificaciones Tributarias

Proyecto Integrado (INACAP) para **nuam**. Mantenedor web para ingresar, calcular, modificar y cargar
masivamente factores de calificaciones tributarias, con registro de auditoría.

## Estado actual
| Componente | Estado |
|---|---|
| Interfaz (prototipo interactivo, HTML/CSS/JS) | Implementada y desplegada en AWS |
| Base de datos PostgreSQL (8 tablas, restricciones, índices, permisos mínimos) | Implementada en el servidor; **aún no conectada** a la interfaz |
| Servidor (EC2, Red Hat, IP elástica, Nginx) | Operativo |
| Backend / API | Pendiente |
| Inicio de sesión y HTTPS | Pendientes |

El prototipo guarda sus datos en el navegador (`localStorage`). Los roles son una simulación: en producción
el rol vendría del inicio de sesión y se verificaría en el servidor.

## Estructura del repositorio
```
src/index.html                 Prototipo de la interfaz
database/schema.sql            Esquema de la base de datos
database/indices.sql           Índices
docs/despliegue-aws.md         Configuración del entorno paso a paso
tests/carga_ejemplo_factores.csv   Archivo de prueba de carga masiva (6 válidas, 4 rechazadas)
```

## Funcionalidades del prototipo
- Búsqueda y filtros por mercado, origen y ejercicio; grilla paginada con salto a una página exacta.
- Ingreso y modificación con cálculo de factores (monto ÷ dividendo, 8 decimales) y validación de que la
  suma de factores 8 a 16 no supere 1.
- Eliminación con confirmación.
- Carga masiva de CSV (36 columnas, separador `;`) con previsualización, rechazo de filas inválidas y
  actualización por llave (mercado + ejercicio + instrumento + secuencia).
- Roles (Analista, Administrador, Supervisor) con permisos distintos.
- Log de auditoría de solo lectura, con filtros por instrumento, usuario y fecha.
- Segregación por corredora.

## Cómo ejecutarlo
- Local: abrir `src/index.html` en un navegador.
- En el servidor: ver `docs/despliegue-aws.md`.

## Integrantes
| Nombre | Rol en el proyecto |
|---|---|
| Simón Antonio Pincheira de la Fuente | Proyecto individual: diseño, desarrollo, base de datos, despliegue en AWS, seguridad, pruebas y documentación |

## Limitaciones conocidas
- Datos solo en el navegador; la interfaz no consulta PostgreSQL.
- Sin autenticación real ni HTTPS.
- Precedencia de la calificación de la corredora sobre la de la bolsa no implementada.
- Cifra de montos por confirmar con nuam (la historia indica 29 y el prototipo usa 30 columnas, 8 a 37).
