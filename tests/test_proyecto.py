"""
Pruebas unitarias (unittest, incluido en Python).

Ejecutar desde la raíz del proyecto:
    python3 -m unittest discover -s tests -v

Se usan "mocks" para simular respuestas de la API sin conexión a Internet,
así se prueba el manejo de errores 401/404/429 de forma repetible.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.api_client import ClienteCatalystCenter, ErrorAPI  # noqa: E402
from modulos.exportador import exportar  # noqa: E402
from modulos.procesador import analizar, filtrar, leer_archivo, normalizar  # noqa: E402

DISPOSITIVOS_API = [
    {"hostname": "sw1", "managementIpAddress": "10.0.0.1", "family": "Switches and Hubs",
     "platformId": "C9300", "softwareVersion": "17.9.4", "reachabilityStatus": "Reachable"},
    {"hostname": "rtr1", "managementIpAddress": "10.0.0.2", "family": "Routers",
     "platformId": "C8000V", "softwareVersion": "17.12.2", "reachabilityStatus": "Unreachable"},
]


def respuesta_falsa(codigo, json_data=None, headers=None):
    resp = mock.Mock()
    resp.status_code = codigo
    resp.ok = 200 <= codigo < 300
    resp.json.return_value = json_data or {}
    resp.text = str(json_data)
    resp.headers = headers or {}
    return resp


class PruebasProcesador(unittest.TestCase):

    def test_normalizar_y_analizar(self):
        inventario = normalizar(DISPOSITIVOS_API)
        resumen = analizar(inventario)
        self.assertEqual(resumen["total_dispositivos"], 2)
        self.assertEqual(resumen["no_alcanzables"], ["rtr1"])
        self.assertEqual(resumen["por_familia"]["Routers"], 1)

    def test_filtrar_familia(self):
        inventario = normalizar(DISPOSITIVOS_API)
        self.assertEqual(len(filtrar(inventario, "switch")), 1)

    def test_exportar_y_releer_todos_los_formatos(self):
        inventario = normalizar(DISPOSITIVOS_API)
        resumen = analizar(inventario)
        with tempfile.TemporaryDirectory() as carpeta:
            rutas = exportar(inventario, resumen, ["json", "yaml", "xml", "csv"], carpeta)
            for ruta in rutas:
                with self.subTest(formato=ruta):
                    self.assertEqual(leer_archivo(ruta), inventario)


class PruebasClienteAPI(unittest.TestCase):

    def setUp(self):
        self.cliente = ClienteCatalystCenter("https://ejemplo.local", "u", "p", reintentos=2)

    def test_rechaza_http_sin_cifrar(self):
        with self.assertRaises(ErrorAPI):
            ClienteCatalystCenter("http://ejemplo.local", "u", "p")

    def test_autenticacion_correcta(self):
        with mock.patch.object(self.cliente.sesion, "request",
                               return_value=respuesta_falsa(200, {"Token": "abc"})):
            self.assertEqual(self.cliente.autenticar(), "abc")
            self.assertEqual(self.cliente.sesion.headers["X-Auth-Token"], "abc")

    def test_error_401_explica_causa(self):
        with mock.patch.object(self.cliente.sesion, "request",
                               return_value=respuesta_falsa(401)):
            with self.assertRaisesRegex(ErrorAPI, "401"):
                self.cliente.autenticar()

    def test_error_404(self):
        self.cliente.token = "abc"
        with mock.patch.object(self.cliente.sesion, "request",
                               return_value=respuesta_falsa(404)):
            with self.assertRaisesRegex(ErrorAPI, "no encontrado"):
                self.cliente.obtener_dispositivos()

    @mock.patch("modulos.api_client.time.sleep")
    def test_429_reintenta_y_luego_funciona(self, _sleep):
        self.cliente.token = "abc"
        respuestas = [respuesta_falsa(429, headers={"Retry-After": "1"}),
                      respuesta_falsa(200, {"response": DISPOSITIVOS_API})]
        with mock.patch.object(self.cliente.sesion, "request", side_effect=respuestas):
            self.assertEqual(len(self.cliente.obtener_dispositivos()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
