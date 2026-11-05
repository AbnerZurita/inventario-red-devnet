"""
Exportación del inventario a JSON, YAML, XML y CSV.

Cada formato tiene un uso típico:
- JSON: intercambio con otras APIs y aplicaciones web.
- YAML: legible por humanos; usado por Ansible y archivos de configuración.
- XML : usado por NETCONF/RESTCONF y sistemas heredados.
- CSV : se abre en Excel para reportes al área de gestión.
"""

import csv
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

import yaml


def _ruta(carpeta, nombre, extension):
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, f"{nombre}.{extension}")


def exportar_json(inventario, resumen, carpeta, nombre):
    ruta = _ruta(carpeta, nombre, "json")
    contenido = {"generado": datetime.now().isoformat(timespec="seconds"),
                 "resumen": resumen, "dispositivos": inventario}
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, indent=4, ensure_ascii=False)
    return ruta


def exportar_yaml(inventario, resumen, carpeta, nombre):
    ruta = _ruta(carpeta, nombre, "yaml")
    with open(ruta, "w", encoding="utf-8") as archivo:
        yaml.safe_dump({"resumen": resumen, "dispositivos": inventario}, archivo,
                       allow_unicode=True, sort_keys=False)
    return ruta


def exportar_xml(inventario, resumen, carpeta, nombre):
    ruta = _ruta(carpeta, nombre, "xml")
    raiz = ET.Element("inventario", total=str(resumen["total_dispositivos"]))
    for disp in inventario:
        nodo = ET.SubElement(raiz, "dispositivo")
        for clave, valor in disp.items():
            ET.SubElement(nodo, clave).text = valor
    arbol = ET.ElementTree(raiz)
    if hasattr(ET, "indent"):  # Python 3.9+; en 3.8 se guarda sin sangría
        ET.indent(arbol)
    arbol.write(ruta, encoding="utf-8", xml_declaration=True)
    return ruta


def exportar_csv(inventario, resumen, carpeta, nombre):
    ruta = _ruta(carpeta, nombre, "csv")
    if not inventario:
        open(ruta, "w").close()
        return ruta
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(inventario[0].keys()))
        escritor.writeheader()
        escritor.writerows(inventario)
    return ruta


EXPORTADORES = {
    "json": exportar_json,
    "yaml": exportar_yaml,
    "xml": exportar_xml,
    "csv": exportar_csv,
}


def exportar(inventario, resumen, formatos, carpeta, nombre="inventario"):
    """Exporta a todos los formatos pedidos y devuelve las rutas generadas."""
    rutas = []
    for formato in formatos:
        funcion = EXPORTADORES.get(formato.strip().lower())
        if funcion is None:
            raise ValueError(f"Formato de salida no soportado: {formato}")
        rutas.append(funcion(inventario, resumen, carpeta, nombre))
    return rutas
