# Despliegue en AWS (Learner Lab)

Guía paso a paso de cómo se configuró el entorno, para poder repetirlo.

## Resumen del entorno
| Elemento | Valor |
|---|---|
| Región | us-east-1 (Norte de Virginia) |
| Instancia | EC2 `siifactor-servidor`, tipo t2.small, 20 GiB gp3 |
| Sistema operativo | Red Hat Enterprise Linux 10.2 |
| Par de claves | vockey (archivo `labsuser.pem`, no se versiona) |
| Grupo de seguridad | `sgsiifactor` |
| IP elástica | 50.19.144.152 |
| Servidor web | Nginx |
| Base de datos | PostgreSQL |

## 1. Grupo de seguridad
EC2 → Red y seguridad → Security Groups → Crear. Nombre `sgsiifactor`, VPC por defecto.
Reglas de entrada:
- HTTP (80) desde 0.0.0.0/0
- HTTPS (443) desde 0.0.0.0/0
- SSH (22) solo desde la IP del administrador ("Mi IP")

Reglas de salida: las predeterminadas. El puerto 5432 (PostgreSQL) **no** se abre.

## 2. Instancia EC2
Lanzar instancia con nombre `siifactor-servidor`, imagen Red Hat Enterprise Linux, tipo t2.small,
par de claves **vockey**, grupo de seguridad existente `sgsiifactor` y 20 GiB de almacenamiento.
(Un primer intento se lanzó sin par de claves; no se puede agregar después, por lo que se terminó
la instancia y se lanzó otra.)

## 3. IP elástica
EC2 → Direcciones IP elásticas → Asignar → Asociar a `siifactor-servidor`.
Evita que la dirección cambie al detener e iniciar el laboratorio.

## 4. Conexión SSH (desde PowerShell del computador local)
```
ssh -i "C:\ruta\labsuser.pem" ec2-user@<IP_ELASTICA>
```

## 5. Instalación de paquetes (en el servidor)
```bash
sudo dnf update -y
sudo dnf install -y git nginx postgresql-server postgresql
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
sudo systemctl enable --now nginx
systemctl is-active postgresql nginx      # debe responder: active, active
```

## 6. Base de datos
```bash
sudo sed -i 's/ident$/scram-sha-256/' /var/lib/pgsql/data/pg_hba.conf
sudo systemctl restart postgresql
sudo -u postgres psql -c "CREATE USER siifactor_app WITH PASSWORD '<CLAVE>';"
sudo -u postgres psql -c "CREATE DATABASE siifactor;"
sudo -u postgres psql -d siifactor -f database/schema.sql
sudo -u postgres psql -d siifactor -f database/indices.sql
PGPASSWORD='<CLAVE>' psql -h 127.0.0.1 -U siifactor_app -d siifactor -c '\dt'   # lista 8 tablas
```
PostgreSQL escucha solo en el propio servidor.

## 7. Publicar el prototipo
Desde el computador local:
```
scp -i "C:\ruta\labsuser.pem" src\index.html ec2-user@<IP_ELASTICA>:/tmp/prototipo_siifactor.html
```
En el servidor:
```bash
sudo cp /tmp/prototipo_siifactor.html /usr/share/nginx/html/index.html
sudo chmod 644 /usr/share/nginx/html/index.html
```
Abrir `http://<IP_ELASTICA>`.

## Notas
- Las instancias se detienen al terminar la sesión del laboratorio; la IP elástica se conserva.
- Todavía no hay HTTPS: el prototipo se sirve por HTTP.
- Las contraseñas y el archivo `.pem` no se suben al repositorio.
