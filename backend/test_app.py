"""Pruebas automatizadas de la API (con una base de datos simulada en memoria).

Ejecutar:  SIIFACTOR_SECRET_KEY=prueba python -m unittest -v test_app
Validan la lógica HTTP: inicio de sesión, bloqueo, CSRF, roles y segregación.
Las consultas SQL se prueban contra PostgreSQL en el servidor (ver docs/backend.md).
"""
import os
import unittest

os.environ.setdefault("SIIFACTOR_SECRET_KEY", "clave-solo-para-pruebas")
os.environ["SIIFACTOR_COOKIE_SECURE"] = "1"

import app as api  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

URL = "https://localhost"
CLAVE = "clave-de-prueba-123"


class BaseSimulada:
    def __init__(self):
        self.usuarios = {}
        self.log = []
        self.args_calificaciones = None
        self.args_auditoria = None

    def agregar(self, uid, correo, rol, corredora_id, corredora, activo=True):
        self.usuarios[correo] = {
            "id": uid, "nombre": "Usuario " + rol, "correo": correo, "rol": rol,
            "hash_clave": generate_password_hash(CLAVE), "corredora_id": corredora_id,
            "corredora": corredora, "activo": activo, "bloqueado": False, "intentos": 0}

    def _vista(self, u):
        return dict(u) if u else None

    def buscar_usuario(self, correo):
        return self._vista(self.usuarios.get(correo))

    def usuario_por_id(self, uid):
        for u in self.usuarios.values():
            if u["id"] == uid and u["activo"]:
                return self._vista(u)
        return None

    def registrar_fallo(self, uid):
        for u in self.usuarios.values():
            if u["id"] == uid:
                u["intentos"] += 1
                if u["intentos"] >= api.MAX_INTENTOS:
                    u["intentos"], u["bloqueado"] = 0, True

    def registrar_exito(self, uid):
        for u in self.usuarios.values():
            if u["id"] == uid:
                u["intentos"], u["bloqueado"] = 0, False

    def registrar_log(self, uid, operacion, detalle=None):
        self.log.append((uid, operacion, detalle))

    def listar_calificaciones(self, corredora_id, limite, desplazamiento):
        self.args_calificaciones = (corredora_id, limite, desplazamiento)
        return []

    def listar_auditoria(self, corredora_id, usuario, desde, hasta, limite):
        self.args_auditoria = (corredora_id, usuario, desde, hasta, limite)
        return []

    def operaciones(self):
        return [op for _, op, _ in self.log]


class PruebasApi(unittest.TestCase):
    def setUp(self):
        self.bd = BaseSimulada()
        self.bd.agregar(1, "admin@a.cl", "administrador", 10, "Corredora A")
        self.bd.agregar(2, "super@a.cl", "supervisor", 10, "Corredora A")
        self.bd.agregar(3, "analista@a.cl", "analista", 10, "Corredora A")
        self.bd.agregar(4, "inactivo@a.cl", "analista", 10, "Corredora A", activo=False)
        for nombre in ("buscar_usuario", "usuario_por_id", "registrar_fallo", "registrar_exito",
                       "registrar_log", "listar_calificaciones", "listar_auditoria"):
            setattr(api, nombre, getattr(self.bd, nombre))
        api.app.config["TESTING"] = False
        self.c = api.app.test_client()

    def entrar(self, correo, clave=CLAVE):
        return self.c.post("/api/login", json={"correo": correo, "clave": clave}, base_url=URL)

    # ---- inicio de sesión -------------------------------------------------
    def test_login_correcto_devuelve_usuario_y_token(self):
        r = self.entrar("admin@a.cl")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual((d["rol"], d["corredora"]), ("administrador", "Corredora A"))
        self.assertGreaterEqual(len(d["csrf"]), 32)
        self.assertNotIn("hash_clave", d)
        self.assertIn("login", self.bd.operaciones())

    def test_cookie_de_sesion_es_segura(self):
        cookie = self.entrar("admin@a.cl").headers.get("Set-Cookie")
        for marca in ("HttpOnly", "Secure", "SameSite=Strict"):
            self.assertIn(marca, cookie)

    def test_clave_incorrecta_y_usuario_inexistente_dan_el_mismo_mensaje(self):
        a = self.entrar("admin@a.cl", "otra-clave-cualquiera")
        b = self.entrar("nadie@a.cl")
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        self.assertEqual(a.get_json(), b.get_json())

    def test_bloqueo_tras_cinco_intentos_fallidos(self):
        for _ in range(api.MAX_INTENTOS):
            self.assertEqual(self.entrar("admin@a.cl", "mala-clave-123").status_code, 401)
        self.assertTrue(self.bd.usuarios["admin@a.cl"]["bloqueado"])
        self.assertEqual(self.entrar("admin@a.cl").status_code, 401)   # ni la clave correcta entra
        self.assertIn("login_rechazado", self.bd.operaciones())

    def test_usuario_inactivo_no_entra(self):
        self.assertEqual(self.entrar("inactivo@a.cl").status_code, 401)

    def test_login_exige_json_y_campos(self):
        r = self.c.post("/api/login", data="correo=a&clave=b", base_url=URL)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.c.post("/api/login", json={"correo": "x"}, base_url=URL).status_code, 400)

    def test_fallos_quedan_en_el_log_sin_guardar_el_correo_desconocido(self):
        self.entrar("nadie@a.cl")
        uid, op, detalle = self.bd.log[-1]
        self.assertEqual((uid, op), (None, "login_fallido"))
        self.assertNotIn("nadie@a.cl", str(detalle))

    # ---- sesión y CSRF ----------------------------------------------------
    def test_me_requiere_sesion(self):
        self.assertEqual(self.c.get("/api/me", base_url=URL).status_code, 401)
        self.entrar("analista@a.cl")
        r = self.c.get("/api/me", base_url=URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["rol"], "analista")

    def test_logout_exige_token_csrf(self):
        token = self.entrar("admin@a.cl").get_json()["csrf"]
        self.assertEqual(self.c.post("/api/logout", base_url=URL).status_code, 403)
        self.assertEqual(self.c.post("/api/logout", headers={"X-CSRF-Token": "falso"}, base_url=URL).status_code, 403)
        self.assertEqual(self.c.post("/api/logout", headers={"X-CSRF-Token": token}, base_url=URL).status_code, 200)
        self.assertEqual(self.c.get("/api/me", base_url=URL).status_code, 401)   # sesión cerrada

    def test_usuario_desactivado_pierde_la_sesion(self):
        self.entrar("analista@a.cl")
        self.bd.usuarios["analista@a.cl"]["activo"] = False
        self.assertEqual(self.c.get("/api/me", base_url=URL).status_code, 401)

    # ---- autorización por rol ---------------------------------------------
    def test_analista_no_puede_ver_la_auditoria(self):
        self.entrar("analista@a.cl")
        self.assertEqual(self.c.get("/api/auditoria", base_url=URL).status_code, 403)
        self.assertIn("acceso_denegado", self.bd.operaciones())
        self.assertIsNone(self.bd.args_auditoria)          # la consulta ni se ejecutó

    def test_supervisor_y_administrador_ven_la_auditoria_de_su_corredora(self):
        for correo in ("super@a.cl", "admin@a.cl"):
            self.entrar(correo)
            self.assertEqual(self.c.get("/api/auditoria", base_url=URL).status_code, 200)
            self.assertEqual(self.bd.args_auditoria[0], 10)   # filtrada por la corredora del usuario

    def test_auditoria_valida_las_fechas(self):
        self.entrar("admin@a.cl")
        self.assertEqual(self.c.get("/api/auditoria?desde=2025-13-45", base_url=URL).status_code, 400)
        self.assertEqual(self.c.get("/api/auditoria?desde=2025-01-01&hasta=2025-12-31", base_url=URL).status_code, 200)

    def test_sin_sesion_no_hay_acceso_a_los_datos(self):
        self.assertEqual(self.c.get("/api/calificaciones", base_url=URL).status_code, 401)
        self.assertEqual(self.c.get("/api/auditoria", base_url=URL).status_code, 401)

    # ---- segregación por corredora ----------------------------------------
    def test_calificaciones_se_consultan_con_la_corredora_de_la_sesion(self):
        self.entrar("analista@a.cl")
        # el cliente intenta pedir otra corredora: el parámetro se ignora
        r = self.c.get("/api/calificaciones?corredora_id=99&limite=1000", base_url=URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.bd.args_calificaciones, (10, api.LIMITE_MAX, 0))

    def test_parametros_invalidos(self):
        self.entrar("admin@a.cl")
        self.assertEqual(self.c.get("/api/calificaciones?limite=abc", base_url=URL).status_code, 400)

    # ---- errores ----------------------------------------------------------
    def test_error_interno_no_expone_detalles(self):
        def falla(*_a, **_k):
            raise RuntimeError("password=secreto en la cadena de conexión")
        api.buscar_usuario = falla
        api.app.config["PROPAGATE_EXCEPTIONS"] = False
        r = self.entrar("admin@a.cl")
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("secreto", r.get_data(as_text=True))

    def test_respuestas_de_la_api_no_se_guardan_en_cache(self):
        self.assertEqual(self.c.get("/api/me", base_url=URL).headers.get("Cache-Control"), "no-store")


if __name__ == "__main__":
    unittest.main()
