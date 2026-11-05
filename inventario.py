#!/usr/bin/env python3
"""
inventario.py - Automatización de inventario de red con Cisco Catalyst Center.

Consulta el inventario de dispositivos mediante la REST API (HTTPS) del
sandbox de Cisco DevNet, lo procesa, lo analiza y lo exporta a
JSON, YAML, XML y CSV.

Ejemplos de uso:
    ./inventario.py                         # consulta la API y exporta todo
    ./inventario.py --familia switches      # solo switches
    ./inventario.py --formatos json,csv     # solo algunos formatos
    ./inventario.py --offline               # usa datos de muestra (sin Internet)
    ./inventario.py --analizar salidas/inventario.xml   # lee y analiza un archivo
    ./inventario.py --diagnostico           # troubleshooting de la conexión
"""

import argparse
import logging
import os
import sys

from modulos.api_client import ClienteCatalystCenter, ErrorAPI
from modulos.configuracion import cargar_config, cargar_env
from modulos.diagnostico import diagnosticar
from modulos.exportador import exportar
from modulos.procesador import analizar, filtrar, leer_archivo, normalizar

# Trabajar siempre desde la carpeta del script (rutas relativas fiables).
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def configurar_logs(ruta_log):
    """Registra en archivo (detalle) y en pantalla (solo advertencias)."""
    os.makedirs(os.path.dirname(ruta_log), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=[logging.FileHandler(ruta_log, encoding="utf-8")],
    )
    consola = logging.StreamHandler()
    consola.setLevel(logging.WARNING)
    logging.getLogger().addHandler(consola)


def leer_argumentos():
    parser = argparse.ArgumentParser(description="Inventario de red vía REST API (Catalyst Center).")
    parser.add_argument("--familia", help="Filtrar por familia (ej. 'switches', 'routers').")
    parser.add_argument("--formatos", help="Formatos de salida separados por coma (json,yaml,xml,csv).")
    parser.add_argument("--offline", action="store_true", help="Usar datos de muestra locales.")
    parser.add_argument("--analizar", metavar="ARCHIVO", help="Analizar un archivo JSON/YAML/XML/CSV.")
    parser.add_argument("--diagnostico", action="store_true", help="Diagnosticar la conexión a la API.")
    return parser.parse_args()


def imprimir_tabla(inventario):
    """Muestra el inventario como tabla en la terminal."""
    columnas = [("hostname", 24), ("ip_gestion", 16), ("plataforma", 20),
                ("version_software", 14), ("estado", 12)]
    encabezado = " ".join(f"{c.upper():<{a}}" for c, a in columnas)
    print("\n" + encabezado + "\n" + "-" * len(encabezado))
    for disp in inventario:
        print(" ".join(f"{disp.get(c, '')[:a - 1]:<{a}}" for c, a in columnas))


def imprimir_resumen(resumen):
    print(f"\nTotal de dispositivos: {resumen['total_dispositivos']}")
    print(f"Alcanzables: {resumen['alcanzables']}  |  "
          f"No alcanzables: {len(resumen['no_alcanzables'])}")
    for titulo, clave in (("Por familia", "por_familia"),
                          ("Por plataforma", "por_plataforma"),
                          ("Por versión de software", "por_version_software")):
        print(f"\n{titulo}:")
        for nombre, cantidad in sorted(resumen[clave].items(), key=lambda x: -x[1]):
            print(f"  - {nombre:<30} {cantidad}")
    if resumen["no_alcanzables"]:
        print("\n[ALERTA] Dispositivos no alcanzables: " + ", ".join(resumen["no_alcanzables"]))


def main():
    args = leer_argumentos()
    cargar_env(".env")
    config = cargar_config("config.yaml")
    configurar_logs(config["archivo_log"])
    log = logging.getLogger("inventario")

    if args.diagnostico:
        ok = diagnosticar(config["url_base"], config["usuario"], config["password"],
                          config["verificar_ssl"])
        return 0 if ok else 1

    try:
        if args.analizar:
            print(f"Leyendo inventario desde {args.analizar} ...")
            inventario = leer_archivo(args.analizar)
        elif args.offline:
            print("Modo offline: usando datos de muestra.")
            inventario = leer_archivo(config["archivo_muestra"])
        else:
            print(f"Conectando a {config['url_base']} por HTTPS ...")
            cliente = ClienteCatalystCenter(config["url_base"], config["usuario"],
                                            config["password"], config["verificar_ssl"],
                                            config["timeout"], config["reintentos"])
            inventario = normalizar(cliente.obtener_dispositivos())
    except ErrorAPI as error:
        log.error(str(error))
        print("Sugerencia: ejecuta './inventario.py --diagnostico' o usa '--offline'.")
        return 1
    except (OSError, ValueError) as error:
        log.error("No se pudo leer el archivo: %s", error)
        return 1

    inventario = filtrar(inventario, args.familia)
    resumen = analizar(inventario)
    imprimir_tabla(inventario)
    imprimir_resumen(resumen)

    if not args.analizar:
        formatos = args.formatos.split(",") if args.formatos else config["formatos_salida"]
        rutas = exportar(inventario, resumen, formatos, config["carpeta_salida"])
        print("\nArchivos generados:")
        for ruta in rutas:
            print(f"  {ruta}")
    log.info("Ejecución finalizada: %d dispositivos.", resumen["total_dispositivos"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
