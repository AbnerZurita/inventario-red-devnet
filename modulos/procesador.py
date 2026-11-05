"""
Procesamiento y análisis del inventario.

- normalizar(): se queda solo con los campos útiles y les da nombres claros.
- analizar(): calcula estadísticas (por familia, plataforma, versión, estado).
- leer_archivo(): lee un inventario desde JSON, YAML, XML o CSV.
"""

import csv
import json
import os
import xml.etree.ElementTree as ET
from collections import Counter

import yaml

# Mapeo: campo de la API -> campo de nuestro inventario
CAMPOS = {
    "hostname": "hostname",
    "managementIpAddress": "ip_gestion",
    "family": "familia",
    "platformId": "plataforma",
    "softwareType": "tipo_software",
    "softwareVersion": "version_software",
    "serialNumber": "numero_serie",
    "role": "rol",
    "reachabilityStatus": "estado",
    "upTime": "tiempo_activo",
    "macAddress": "mac",
}


def normalizar(dispositivos_api):
    """Convierte la respuesta cruda de la API en una lista de diccionarios limpia."""
    inventario = []
    for disp in dispositivos_api:
        fila = {}
        for campo_api, campo_local in CAMPOS.items():
            valor = disp.get(campo_api)
            fila[campo_local] = "" if valor is None else str(valor)
        inventario.append(fila)
    # Orden estable por hostname para que los reportes sean comparables.
    return sorted(inventario, key=lambda d: d["hostname"].lower())


def filtrar(inventario, familia=None):
    """Filtra el inventario por familia (por ejemplo: 'Switches and Hubs')."""
    if not familia:
        return inventario
    return [d for d in inventario if familia.lower() in d["familia"].lower()]


def analizar(inventario):
    """Genera un resumen estadístico del inventario."""
    no_alcanzables = [d["hostname"] for d in inventario
                      if d["estado"].lower() != "reachable"]
    return {
        "total_dispositivos": len(inventario),
        "por_familia": dict(Counter(d["familia"] or "Sin dato" for d in inventario)),
        "por_plataforma": dict(Counter(d["plataforma"] or "Sin dato" for d in inventario)),
        "por_version_software": dict(Counter(d["version_software"] or "Sin dato" for d in inventario)),
        "por_rol": dict(Counter(d["rol"] or "Sin dato" for d in inventario)),
        "alcanzables": len(inventario) - len(no_alcanzables),
        "no_alcanzables": no_alcanzables,
    }


# ---------------------------------------------------------------------- #
# Lectura de archivos en distintos formatos
# ---------------------------------------------------------------------- #
def leer_archivo(ruta):
    """Lee un inventario desde .json, .yaml/.yml, .xml o .csv."""
    extension = os.path.splitext(ruta)[1].lower()
    with open(ruta, "r", encoding="utf-8") as archivo:
        if extension == ".json":
            datos = json.load(archivo)
        elif extension in (".yaml", ".yml"):
            datos = yaml.safe_load(archivo)
        elif extension == ".csv":
            datos = list(csv.DictReader(archivo))
        elif extension == ".xml":
            raiz = ET.parse(archivo).getroot()
            datos = [{campo.tag: (campo.text or "") for campo in disp}
                     for disp in raiz.findall("dispositivo")]
        else:
            raise ValueError(f"Formato no soportado: {extension}")

    # Los JSON de la API traen {"response": [...]}; los nuestros, {"dispositivos": [...]}
    if isinstance(datos, dict):
        datos = datos.get("response") or datos.get("dispositivos") or []
    # Si son datos crudos de la API (camelCase), se normalizan.
    if datos and "managementIpAddress" in datos[0]:
        datos = normalizar(datos)
    return datos
