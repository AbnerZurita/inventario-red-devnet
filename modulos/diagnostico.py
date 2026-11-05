"""
Diagnóstico paso a paso de la conexión a una REST API.

Cuando una llamada falla, conviene revisar las capas en orden
(de abajo hacia arriba), igual que en redes:
  1. DNS   -> ¿el nombre se resuelve a una IP?
  2. TCP   -> ¿el puerto 443 está abierto/alcanzable?
  3. TLS   -> ¿el certificado es válido y de confianza?
  4. HTTP  -> ¿responde el servidor? ¿qué código devuelve?
  5. AUTH  -> ¿las credenciales generan un token?
"""

import socket
import ssl
from urllib.parse import urlparse

import requests
import urllib3


def _resultado(paso, ok, detalle):
    estado = "OK " if ok else "FALLA"
    print(f"  [{estado}] {paso:<6} {detalle}")
    return ok


def diagnosticar(url_base, usuario, password, verificar_ssl=True, timeout=10):
    """Ejecuta todas las pruebas y se detiene en la primera que falle.

    verificar_ssl: True (CA del sistema), ruta a un .pem, o False (sin verificar).
    """
    if verificar_ssl is False:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    host = urlparse(url_base).hostname
    puerto = urlparse(url_base).port or 443
    print(f"\nDiagnóstico de conexión a {url_base}\n")

    # 1. DNS
    try:
        ip = socket.gethostbyname(host)
        _resultado("DNS", True, f"{host} -> {ip}")
    except socket.gaierror:
        return _resultado("DNS", False, f"No se resuelve {host}. Revisa /etc/resolv.conf o la conexión.")

    # 2. TCP
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            _resultado("TCP", True, f"Puerto {puerto} alcanzable")
    except OSError as error:
        return _resultado("TCP", False, f"Puerto {puerto} no alcanzable ({error}). ¿Firewall/proxy?")

    # 3. TLS
    try:
        contexto = ssl.create_default_context()
        if isinstance(verificar_ssl, str):
            contexto.load_verify_locations(verificar_ssl)  # confiar en el .pem guardado
        with socket.create_connection((host, puerto), timeout=timeout) as sock:
            with contexto.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
                emisor = dict(x[0] for x in cert["issuer"]).get("organizationName", "?")
                _resultado("TLS", True, f"{tls.version()} | emisor: {emisor} | vence: {cert['notAfter']}")
    except (ssl.SSLError, ssl.CertificateError, OSError) as error:
        detalle = getattr(error, "reason", None) or str(error)
        if verificar_ssl is False:
            _resultado("TLS", False, f"Certificado no confiable ({detalle}). Se continúa porque "
                                     "verificar_ssl: false (solo laboratorio).")
        else:
            return _resultado("TLS", False, f"Certificado no confiable ({detalle}). El sandbox usa "
                                            "un certificado autofirmado: ver docs/troubleshooting.md.")

    # 4 y 5. HTTP + autenticación
    try:
        respuesta = requests.post(f"{url_base}/dna/system/api/v1/auth/token",
                                  auth=(usuario, password), timeout=timeout,
                                  verify=verificar_ssl)
    except requests.exceptions.RequestException as error:
        return _resultado("HTTP", False, str(error))
    _resultado("HTTP", True, f"Servidor respondió con código {respuesta.status_code}")
    if respuesta.status_code == 200 and "Token" in respuesta.json():
        return _resultado("AUTH", True, "Token obtenido correctamente")
    return _resultado("AUTH", False, f"HTTP {respuesta.status_code}: revisa usuario/contraseña en .env "
                                     "(el sandbox compartido a veces cambia la clave).")
