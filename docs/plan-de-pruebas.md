# Plan de pruebas y resultados · SIIFactor

Sistema probado: prototipo desplegado en `https://50.19.144.152` (y `http://`), servidor EC2 con Red Hat Enterprise Linux 10.2, Nginx y PostgreSQL.
Las pruebas de interfaz se hicieron en una ventana privada del navegador, con una captura por prueba. Los resultados se registran tal como se observaron; las discrepancias se conservaron junto con su corrección.

**Estados:** Cumple · Discrepancia (corregida o aceptada) · Limitación conocida.

## Resumen de casos (55)

| Grupo | Casos | Cubre |
|---|---|---|
| Funcionales (PF) | 12 | Ingreso, cálculo, validaciones, modificación, eliminación, filtros, segregación, persistencia |
| Roles (RO) | 4 | Permisos de Analista, Administrador y Supervisor |
| Log (LG) | 4 | Filtros por instrumento, usuario y fecha |
| Paginación (PG) | 3 | Salto a página, primera y última |
| Interfaz (UI) | 3 | Adaptabilidad, tema y teclado |
| Carga masiva (CM) | 4 | Previsualización, confirmación, actualización por llave, entrada vacía |
| Base de datos (BD) | 9 | Restricciones, llave única y permisos del log |
| Rendimiento (RE) | 3 | Volumen de 10.000 filas, solicitudes secuenciales y concurrentes |
| Seguridad (SE) | 11 | Inyección, red, acceso SSH, HTTPS, cabeceras y política de contenido |
| Entorno (EN) | 2 | Reinicio del servidor y respaldo con restauración |

## Carga masiva (`tests/carga_ejemplo_factores.csv`)

| ID | Caso | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| CM-01 | Previsualizar el archivo de ejemplo (10 filas) | 6 válidas (1 actualiza, 5 nuevas) y 4 rechazadas con su motivo | 6 válidas y 4 rechazadas con los motivos esperados | Cumple |
| CM-02 | Confirmar carga | Se cargan solo las válidas; un registro de carga en el log | El mantenedor pasó de 3 a 8 calificaciones; el log registró «Carga masiva (6 filas), 5 nuevas, 1 actualizadas» | Cumple |
| CM-03 | Repetir la misma carga | Las filas figuran como actualización | Las 6 válidas figuran como «Actualiza registro existente» | Cumple |
| CM-04 | Previsualizar con entrada vacía | Sin filas válidas | «0 de 0 filas válidas» y botón Confirmar carga deshabilitado | Cumple |

## Base de datos (cuenta de la aplicación)

| ID | Caso | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| BD-01 | Insertar un instrumento | Inserción correcta | INSERT 0 1 | Cumple |
| BD-02 | Calificación con secuencia 9.500 | Rechazo por restricción | Error de `calificacion_secuencia_check` | Cumple |
| BD-03 | Calificación con secuencia 10.800 | Inserción correcta | INSERT 0 1 | Cumple |
| BD-04 | Misma llave dos veces | Rechazo por llave única | Error de clave duplicada (instrumento, ejercicio, secuencia) | Cumple |
| BD-05 | Factor 1,5 | Rechazo | Error de `factor_valor_check` | Cumple |
| BD-06 | Columna 7 | Rechazo | Error de `factor_columna_check` | Cumple |
| BD-07 | Insertar en el log | Permitido | INSERT 0 1 | Cumple |
| BD-08 | Modificar el log | Denegado | permission denied for table log_auditoria | Cumple |
| BD-09 | Borrar del log | Denegado | permission denied for table log_auditoria | Cumple |

## Rendimiento

| ID | Caso | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| RE-01 (inicial) | Cargar un archivo de 10.000 filas | Menos de 30 s y sin errores | Las filas se cargaron, pero la página dejó de responder | Discrepancia |
| RE-01 (corregida) | Misma carga tras la corrección | Sin congelamiento | La carga y la navegación funcionaron correctamente | Cumple |
| RE-02 | 100 solicitudes secuenciales | Todas responden sin error | 15,31 s en total (unos 153 ms por solicitud), sin errores | Cumple |
| RE-03 | 20 clientes simultáneos, 500 solicitudes | Sin errores | 500 de 500 con respuesta 200; 23,12 s en total | Cumple |

RE-02 y RE-03 miden el servidor web (Nginx) sirviendo el prototipo estático; no miden una aplicación con backend.

## Seguridad

| ID | Caso | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| SE-01 | HTML en la descripción | Se muestra como texto | Se muestra como texto, sin alerta | Cumple |
| SE-02b (inicial) | Mercado con HTML en un CSV | Texto o rechazo | El HTML se interpretó | Discrepancia |
| SE-02 (inicial) | Instrumento con fórmula en un CSV | Rechazo o neutralización | Se aceptó tal cual | Discrepancia |
| SE-02/02b (corregidas) | Mismo archivo tras la corrección | Ambas filas rechazadas | Mercado no válido; instrumento con caracteres no permitidos | Cumple |
| SE-03 | SSH desde otra red | Tiempo de espera agotado | Connection timed out tras 15 s con otra IP pública | Cumple |
| SE-04 | Puerto 5432 desde fuera | Cerrado | TcpTestSucceeded: False | Cumple |
| SE-05 | Puerto 80 desde fuera | Abierto | TcpTestSucceeded: True | Cumple |
| SE-06 (inicial) | Puerto 443 | HTTPS disponible | TcpTestSucceeded: False | Discrepancia |
| SE-06 (corregida) | Puerto 443 y respuesta HTTPS | HTTPS disponible | TcpTestSucceeded: True; 200 OK por HTTPS | Cumple |
| SE-06b / SE-08 | Navegador por HTTPS | Certificado de confianza | Advertencia ERR_CERT_AUTHORITY_INVALID (certificado autofirmado) | Limitación conocida |
| SE-07 (inicial) | Cabeceras y versión oculta | Presentes | `Server: nginx/1.26.3` visible; sin cabeceras de seguridad | Discrepancia |
| SE-07 (corregida) | Mismas cabeceras tras la corrección | Presentes | Server sin versión; presentes las cuatro cabeceras | Cumple |
| SE-09 | Conexión a un origen externo | Bloqueada por la política de contenido | Bloqueada: viola `default-src 'self'` | Cumple |

## Entorno

| ID | Caso | Esperado | Obtenido | Estado |
|---|---|---|---|---|
| EN-01 | Reiniciar el servidor | Los servicios arrancan solos; el sitio responde con la misma IP | Tras el reinicio: nginx y postgresql en estado active, 8 tablas presentes, 200 OK por HTTP y HTTPS | Cumple |
| EN-02 | Respaldar, eliminar un dato y restaurar en una base aparte | El dato se recupera | El instrumento RESTORE-TEST reapareció en la base restaurada | Cumple |

Limitación de EN-02: el respaldo se hizo a mano y se guardó en el mismo servidor; la restauración se probó en una base aparte.

## Pruebas de interfaz, roles, log, paginación y diseño

PF-01 a PF-12, RO-01 a RO-04, LG-01 a LG-04, PG-01 a PG-03 y UI-01 a UI-03 se ejecutaron sobre el sistema desplegado y cumplieron lo esperado. Sus capturas se agregan en `docs/capturas/`.
