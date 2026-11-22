"""SIIFactor · API de autenticación y consulta.

Etapa 1: inicio de sesión con usuarios en PostgreSQL (administrador, supervisor y analista),
autorización por rol verificada en el servidor y segregación de datos por corredora.
"""
import hmac
import json
import os
import secrets
import datetime as dt
from functools import wraps

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

MAX_INTENTOS = 5          # intentos fallidos antes de bloquear la cuenta
BLOQUEO_MINUTOS = 5       # duración del bloqueo
LIMITE_MAX = 100          # máximo de filas por consulta

# Hash de relleno: se compara cuando el correo no existe, para que la respuesta
# tarde lo mismo y no se pueda averiguar qué correos están registrados.
_HASH_RELLENO = generate_password_hash(secrets.token_hex(8))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ["SIIFACTOR_SECRET_KEY"],           # obligatoria: sin ella no arranca
    SESSION_COOKIE_NAME="siifactor_sesion",
    SESSION_COOKIE_HTTPONLY=True,                            # no accesible desde JavaScript
    SESSION_COOKIE_SECURE=os.environ.get("SIIFACTOR_COOKIE_SECURE", "1") == "1",  # solo por HTTPS
    SESSION_COOKIE_SAMESITE="Strict",                        # no se envía desde otros sitios
    PERMANENT_SESSION_LIFETIME=dt.timedelta(minutes=30),     # vence por inactividad
    SESSION_REFRESH_EACH_REQUEST=True,
    MAX_CONTENT_LENGTH=100_000,
)


# ----------------------------------------------------------------------------
# Acceso a la base de datos (todas las consultas son parametrizadas)
# ----------------------------------------------------------------------------
def _db():
    if "db" not in g:
        import psycopg2
        import psycopg2.extras
        g.db = psycopg2.connect(
            host=os.environ.get("SIIFACTOR_DB_HOST", "127.0.0.1"),
            dbname=os.environ.get("SIIFACTOR_DB_NAME", "siifactor"),
            user=os.environ.get("SIIFACTOR_DB_USER", "siifactor_app"),
            password=os.environ["SIIFACTOR_DB_PASSWORD"],
            connect_timeout=5,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return g.db


@app.teardown_appcontext
def _cerrar_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _a_texto(fila):
    """Convierte fechas y decimales a texto para poder serializarlos como JSON."""
    return {k: (v if isinstance(v, (str, int, float, bool, dict, list)) or v is None else str(v))
            for k, v in fila.items()}


_SQL_USUARIO = """
    SELECT u.id, u.nombre, u.correo, u.hash_clave, u.rol, u.corredora_id,
           c.nombre AS corredora, u.activo,
           (u.bloqueado_hasta IS NOT NULL AND u.bloqueado_hasta > now()) AS bloqueado
    FROM usuario u LEFT JOIN corredora c ON c.id = u.corredora_id
"""


def buscar_usuario(correo):
    with _db().cursor() as cur:
        cur.execute(_SQL_USUARIO + " WHERE lower(u.correo) = %s", (correo,))
        return cur.fetchone()


def usuario_por_id(uid):
    with _db().cursor() as cur:
        cur.execute(_SQL_USUARIO + " WHERE u.id = %s AND u.activo", (uid,))
        return cur.fetchone()


def registrar_fallo(uid):
    with _db().cursor() as cur:
        cur.execute(
            """UPDATE usuario SET
                 intentos_fallidos = CASE WHEN intentos_fallidos + 1 >= %s THEN 0 ELSE intentos_fallidos + 1 END,
                 bloqueado_hasta = CASE WHEN intentos_fallidos + 1 >= %s
                                        THEN now() + make_interval(mins => %s) ELSE bloqueado_hasta END
               WHERE id = %s""",
            (MAX_INTENTOS, MAX_INTENTOS, BLOQUEO_MINUTOS, uid))
    _db().commit()


def registrar_exito(uid):
    with _db().cursor() as cur:
        cur.execute("UPDATE usuario SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = %s", (uid,))
    _db().commit()


def registrar_log(uid, operacion, detalle=None):
    with _db().cursor() as cur:
        cur.execute(
            "INSERT INTO log_auditoria (usuario_id, operacion, valor_nuevo) VALUES (%s, %s, %s::jsonb)",
            (uid, operacion, json.dumps(detalle) if detalle else None))
    _db().commit()


def listar_calificaciones(corredora_id, limite, desplazamiento):
    with _db().cursor() as cur:
        cur.execute(
            """SELECT c.id, i.mercado, i.nemo AS instrumento, c.ejercicio, c.secuencia, c.fecha_pago,
                      c.descripcion, c.dividendo, c.isfut, c.origen
               FROM calificacion c JOIN instrumento i ON i.id = c.instrumento_id
               WHERE c.corredora_id IS NULL OR c.corredora_id = %s
               ORDER BY c.ejercicio DESC, c.secuencia DESC
               LIMIT %s OFFSET %s""",
            (corredora_id, limite, desplazamiento))
        return [_a_texto(f) for f in cur.fetchall()]


def listar_auditoria(corredora_id, usuario, desde, hasta, limite):
    with _db().cursor() as cur:
        cur.execute(
            """SELECT l.id, l.fecha_hora, u.nombre AS usuario, l.operacion, l.valor_anterior, l.valor_nuevo
               FROM log_auditoria l JOIN usuario u ON u.id = l.usuario_id
               WHERE u.corredora_id = %s
                 AND (%s IS NULL OR u.nombre ILIKE '%%' || %s || '%%')
                 AND (%s IS NULL OR l.fecha_hora::date >= %s::date)
                 AND (%s IS NULL OR l.fecha_hora::date <= %s::date)
               ORDER BY l.fecha_hora DESC
               LIMIT %s""",
            (corredora_id, usuario, usuario, desde, desde, hasta, hasta, limite))
        return [_a_texto(f) for f in cur.fetchall()]


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def _error(codigo, mensaje):
    return jsonify({"error": mensaje}), codigo


def _ip():
    return request.headers.get("X-Real-IP", request.remote_addr)


def _datos_usuario(u):
    return {"id": u["id"], "nombre": u["nombre"], "correo": u["correo"],
            "rol": u["rol"], "corredora": u["corredora"]}


def _usuario_actual():
    uid = session.get("uid")
    if not uid:
        return None
    u = usuario_por_id(uid)
    if u is None:                      # usuario desactivado o eliminado
        session.clear()
    return u


def requiere_rol(*roles):
    """Exige sesión iniciada y, si se indican roles, que el usuario tenga uno de ellos."""
    def decorador(f):
        @wraps(f)
        def interno(*args, **kwargs):
            u = _usuario_actual()
            if u is None:
                return _error(401, "Sesión requerida")
            if roles and u["rol"] not in roles:
                registrar_log(u["id"], "acceso_denegado", {"ruta": request.path, "rol": u["rol"], "ip": _ip()})
                return _error(403, "No tienes permiso para esta acción")
            g.usuario = u
            return f(*args, **kwargs)
        return interno
    return decorador


# ----------------------------------------------------------------------------
# Protecciones globales
# ----------------------------------------------------------------------------
@app.before_request
def _proteger():
    """Protección CSRF: toda petición que modifica datos (salvo el login) debe traer el token de la sesión."""
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.path != "/api/login":
        esperado = session.get("csrf", "")
        enviado = request.headers.get("X-CSRF-Token", "")
        if not esperado or not hmac.compare_digest(esperado, enviado):
            return _error(403, "Token CSRF inválido")


@app.after_request
def _cabeceras(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(404)
def _no_encontrado(_e):
    return _error(404, "Recurso no encontrado")


@app.errorhandler(405)
def _metodo(_e):
    return _error(405, "Método no permitido")


@app.errorhandler(413)
def _grande(_e):
    return _error(413, "Solicitud demasiado grande")


@app.errorhandler(Exception)
def _inesperado(e):
    app.logger.exception("Error inesperado: %s", e)
    return _error(500, "Error interno")          # sin detalles internos para el cliente


# ----------------------------------------------------------------------------
# Rutas
# ----------------------------------------------------------------------------
@app.post("/api/login")
def login():
    if not request.is_json:
        return _error(400, "Se esperaba JSON")
    datos = request.get_json(silent=True) or {}
    correo = str(datos.get("correo", "")).strip().lower()
    clave = str(datos.get("clave", ""))
    if not correo or not clave or len(correo) > 254 or len(clave) > 200:
        return _error(400, "Correo y contraseña son obligatorios")

    u = buscar_usuario(correo)
    # Mismo mensaje para correo inexistente, contraseña errónea, cuenta bloqueada o inactiva.
    generico = "Credenciales inválidas o cuenta bloqueada temporalmente"
    if u is None:
        check_password_hash(_HASH_RELLENO, clave)
        registrar_log(None, "login_fallido", {"motivo": "usuario_desconocido", "ip": _ip()})
        return _error(401, generico)
    if u["bloqueado"] or not u["activo"]:
        registrar_log(u["id"], "login_rechazado", {"motivo": "bloqueado_o_inactivo", "ip": _ip()})
        return _error(401, generico)
    if not check_password_hash(u["hash_clave"], clave):
        registrar_fallo(u["id"])
        registrar_log(u["id"], "login_fallido", {"motivo": "clave_incorrecta", "ip": _ip()})
        return _error(401, generico)

    registrar_exito(u["id"])
    session.clear()                                # nueva sesión: evita fijación de sesión
    session.permanent = True
    session["uid"] = u["id"]
    session["csrf"] = secrets.token_urlsafe(32)
    registrar_log(u["id"], "login", {"ip": _ip()})
    return jsonify({**_datos_usuario(u), "csrf": session["csrf"]})


@app.post("/api/logout")
def logout():
    uid = session.get("uid")
    if uid:
        registrar_log(uid, "logout", {"ip": _ip()})
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
@requiere_rol()
def me():
    return jsonify({**_datos_usuario(g.usuario), "csrf": session["csrf"]})


@app.get("/api/calificaciones")
@requiere_rol("administrador", "analista", "supervisor")
def calificaciones():
    """Cada usuario ve las calificaciones de la bolsa y las de su propia corredora."""
    try:
        limite = min(max(int(request.args.get("limite", 25)), 1), LIMITE_MAX)
        desplazamiento = max(int(request.args.get("desplazamiento", 0)), 0)
    except ValueError:
        return _error(400, "Parámetros inválidos")
    filas = listar_calificaciones(g.usuario["corredora_id"], limite, desplazamiento)
    return jsonify({"calificaciones": filas, "limite": limite, "desplazamiento": desplazamiento})


@app.get("/api/auditoria")
@requiere_rol("administrador", "supervisor")
def auditoria():
    """El analista no tiene acceso. Se muestran solo los eventos de usuarios de la misma corredora."""
    usuario = request.args.get("usuario", "").strip()[:60] or None
    try:
        desde = dt.date.fromisoformat(request.args["desde"]).isoformat() if request.args.get("desde") else None
        hasta = dt.date.fromisoformat(request.args["hasta"]).isoformat() if request.args.get("hasta") else None
    except ValueError:
        return _error(400, "Fecha inválida (use AAAA-MM-DD)")
    filas = listar_auditoria(g.usuario["corredora_id"], usuario, desde, hasta, 200)
    return jsonify({"registros": filas})
