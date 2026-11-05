"""
Carga de configuración del proyecto.

Buenas prácticas aplicadas:
- La configuración no sensible (URL, timeouts, formatos) vive en config.yaml.
- Las credenciales NUNCA se escriben en el código: se leen de variables de
  entorno o de un archivo .env (que está en .gitignore y tiene permisos 600).
"""

import os

import yaml


def cargar_env(ruta_env=".env"):
    """Lee un archivo .env sencillo (CLAVE=valor) y lo carga en os.environ.

    No sobrescribe variables que ya existan en el entorno, así el usuario
    puede exportarlas en la terminal si lo prefiere.
    """
    if not os.path.isfile(ruta_env):
        return
    with open(ruta_env, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def cargar_config(ruta_config="config.yaml"):
    """Devuelve la configuración del proyecto como diccionario (formato YAML)."""
    with open(ruta_config, "r", encoding="utf-8") as archivo:
        config = yaml.safe_load(archivo)

    # Las credenciales vienen del entorno, no del YAML.
    config["usuario"] = os.environ.get("DNAC_USER", "")
    config["password"] = os.environ.get("DNAC_PASSWORD", "")
    return config
