"""Crea un usuario de SIIFactor con la contraseña guardada como hash.

Uso (la contraseña se pide por teclado y no queda en el historial ni en el repositorio):
    python crear_usuario.py --correo admin@ejemplo.cl --nombre "Nombre Apellido" \\
        --rol administrador --corredora "Corredora A"
Requiere las variables SIIFACTOR_DB_* (ver deploy/siifactor.env.example).
"""
import argparse
import getpass
import os
import sys

import psycopg2
from werkzeug.security import generate_password_hash

ROLES = ("administrador", "analista", "supervisor")
LARGO_MINIMO = 12


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--correo", required=True)
    p.add_argument("--nombre", required=True)
    p.add_argument("--rol", required=True, choices=ROLES)
    p.add_argument("--corredora", required=True, help='Por ejemplo: "Corredora A"')
    a = p.parse_args()

    clave = getpass.getpass("Contraseña (mínimo %d caracteres): " % LARGO_MINIMO)
    if len(clave) < LARGO_MINIMO:
        sys.exit("La contraseña es demasiado corta.")
    if clave != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden.")

    con = psycopg2.connect(
        host=os.environ.get("SIIFACTOR_DB_HOST", "127.0.0.1"),
        dbname=os.environ.get("SIIFACTOR_DB_NAME", "siifactor"),
        user=os.environ.get("SIIFACTOR_DB_USER", "siifactor_app"),
        password=os.environ["SIIFACTOR_DB_PASSWORD"])
    try:
        with con, con.cursor() as cur:
            cur.execute(
                "INSERT INTO corredora (nombre) VALUES (%s) "
                "ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING id", (a.corredora,))
            cid = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO usuario (nombre, correo, hash_clave, rol, corredora_id) "
                "VALUES (%s, lower(%s), %s, %s, %s)",
                (a.nombre, a.correo, generate_password_hash(clave), a.rol, cid))
        print("Usuario creado: %s (%s, %s)" % (a.correo.lower(), a.rol, a.corredora))
    except psycopg2.errors.UniqueViolation:
        sys.exit("Ya existe un usuario con ese correo.")
    finally:
        con.close()


if __name__ == "__main__":
    main()
