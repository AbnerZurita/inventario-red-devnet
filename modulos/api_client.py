"""
Cliente REST sobre HTTPS para Cisco Catalyst Center (antes DNA Center).

Flujo de la API:
  1. POST /dna/system/api/v1/auth/token   (autenticación Basic) -> token
  2. GET  /dna/intent/api/v1/network-device (cabecera X-Auth-Token) -> inventario

Incluye manejo de errores típicos de REST API (timeouts, SSL, 401, 403,
404, 429, 5xx) con mensajes que explican la causa y cómo resolverla.
"""

import logging
import time

import requests
import urllib3

log = logging.getLogger(__name__)

# Explicación de cada código HTTP y cómo resolverlo (troubleshooting).
SOLUCIONES_HTTP = {
    400: "Solicitud mal formada: revisa parámetros, cuerpo JSON y cabecera Content-Type.",
    401: ("No autenticado: usuario/contraseña incorrectos o token vencido. "
          "Verifica .env y vuelve a pedir el token."),
    403: ("Prohibido: las credenciales son válidas pero no tienen permisos "
          "(el sandbox always-on es de solo lectura)."),
    404: "Recurso no encontrado: revisa la URL base y la ruta del endpoint (/dna/intent/api/v1/...).",
    405: "Método no permitido: el endpoint no acepta ese verbo HTTP (GET/POST/PUT/DELETE).",
    429: "Demasiadas solicitudes (rate limit): espera el tiempo de 'Retry-After' y reduce la frecuencia.",
    500: "Error interno del servidor: no es culpa del cliente; reintenta más tarde.",
    502: "Bad Gateway: un proxy/balanceador no pudo contactar al servidor; reintenta más tarde.",
    503: "Servicio no disponible: el sandbox puede estar en mantenimiento; reintenta o reserva uno.",
    504: "Gateway Timeout: el servidor tardó demasiado; reintenta o aumenta el timeout.",
}

# Códigos para los que vale la pena reintentar automáticamente.
CODIGOS_REINTENTABLES = {429, 500, 502, 503, 504}


class ErrorAPI(Exception):
    """Error controlado de la API con explicación para el usuario."""


def explicar_codigo(codigo):
    """Devuelve la explicación de un código HTTP de error."""
    return SOLUCIONES_HTTP.get(codigo, "Código HTTP no esperado; revisa la documentación de la API.")


class ClienteCatalystCenter:
    """Encapsula la conexión HTTPS con Catalyst Center."""

    def __init__(self, url_base, usuario, password, verificar_ssl=True,
                 timeout=15, reintentos=3):
        if not url_base.startswith("https://"):
            # Requisito del proyecto: solo comunicación cifrada.
            raise ErrorAPI("La URL base debe usar HTTPS para proteger credenciales y datos.")
        if not usuario or not password:
            raise ErrorAPI("Faltan credenciales: define DNAC_USER y DNAC_PASSWORD en el archivo .env.")
        self.url_base = url_base.rstrip("/")
        self.usuario = usuario
        self.password = password
        # verificar_ssl puede ser: True (CA del sistema), una ruta a un .pem
        # con el certificado del servidor (recomendado para el sandbox), o
        # False (sin verificar; SOLO en laboratorio).
        self.verificar_ssl = verificar_ssl
        if verificar_ssl is False:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            log.warning("Verificación TLS desactivada (solo laboratorio): la conexión sigue "
                        "cifrada, pero no se comprueba la identidad del servidor.")
        self.timeout = timeout
        self.reintentos = reintentos
        self.token = None
        self.sesion = requests.Session()
        self.sesion.headers.update({"Accept": "application/json",
                                    "Content-Type": "application/json"})

    # ------------------------------------------------------------------ #
    def _solicitud(self, metodo, ruta, **kwargs):
        """Ejecuta una solicitud HTTPS con reintentos y manejo de errores."""
        url = f"{self.url_base}{ruta}"
        for intento in range(1, self.reintentos + 1):
            try:
                log.info("%s %s (intento %d)", metodo, url, intento)
                respuesta = self.sesion.request(metodo, url, timeout=self.timeout,
                                                verify=self.verificar_ssl, **kwargs)
            except requests.exceptions.SSLError as error:
                raise ErrorAPI("Error de certificado SSL/TLS: el certificado del servidor no es "
                               "de confianza (el sandbox usa un certificado autofirmado). "
                               "Solución segura: guarda su certificado en certs/sandboxdnac.pem y "
                               "ponlo en verificar_ssl. Solo en laboratorio: verificar_ssl: false. "
                               f"Detalle: {error}")
            except requests.exceptions.Timeout:
                log.warning("Timeout en %s", url)
                if intento == self.reintentos:
                    raise ErrorAPI(f"Timeout tras {self.reintentos} intentos: el servidor no responde. "
                                   "Revisa tu conexión o aumenta 'timeout' en config.yaml.")
                time.sleep(2 ** intento)
                continue
            except requests.exceptions.ConnectionError as error:
                raise ErrorAPI("No se pudo conectar: revisa DNS, conexión a Internet, proxy o "
                               f"firewall (puerto 443). Detalle: {error}")

            if respuesta.ok:
                return respuesta

            codigo = respuesta.status_code
            log.error("HTTP %d en %s: %s", codigo, url, respuesta.text[:200])
            if codigo in CODIGOS_REINTENTABLES and intento < self.reintentos:
                espera = int(respuesta.headers.get("Retry-After", 2 ** intento))
                log.warning("Reintentando en %d s...", espera)
                time.sleep(espera)
                continue
            raise ErrorAPI(f"HTTP {codigo}: {explicar_codigo(codigo)}")

        raise ErrorAPI("Se agotaron los reintentos.")

    # ------------------------------------------------------------------ #
    def autenticar(self):
        """Obtiene el token de acceso con autenticación Basic sobre HTTPS."""
        respuesta = self._solicitud("POST", "/dna/system/api/v1/auth/token",
                                    auth=(self.usuario, self.password))
        self.token = respuesta.json().get("Token")
        if not self.token:
            raise ErrorAPI("La respuesta de autenticación no contiene 'Token'.")
        self.sesion.headers["X-Auth-Token"] = self.token
        log.info("Autenticación correcta, token recibido.")
        return self.token

    def obtener_dispositivos(self, limite=500):
        """Descarga el inventario completo de dispositivos, página por página."""
        if not self.token:
            self.autenticar()
        dispositivos = []
        offset = 1  # Catalyst Center empieza a paginar en 1
        while True:
            respuesta = self._solicitud("GET", "/dna/intent/api/v1/network-device",
                                        params={"offset": offset, "limit": limite})
            pagina = respuesta.json().get("response", [])
            dispositivos.extend(pagina)
            if len(pagina) < limite:
                break
            offset += limite
        log.info("Se obtuvieron %d dispositivos.", len(dispositivos))
        return dispositivos
