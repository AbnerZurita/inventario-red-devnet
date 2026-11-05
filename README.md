# Inventario de red automatizado con Cisco Catalyst Center (DevNet)

Proyecto del curso **DevOps: fundamentos (Cisco DevNet)**. Automatiza la consulta del
inventario de dispositivos de red mediante la **REST API sobre HTTPS** del sandbox
*Always-On* de Cisco Catalyst Center, procesa los datos con Python y los exporta a
**JSON, YAML, XML y CSV**.

## Funcionalidades

- Autenticación segura (HTTPS + Basic Auth → token `X-Auth-Token`).
- Descarga paginada del inventario (`GET /dna/intent/api/v1/network-device`).
- Análisis: totales por familia, plataforma, versión de software y rol; alerta de equipos no alcanzables.
- Exportación a JSON, YAML, XML y CSV, y lectura/análisis de cualquiera de esos formatos.
- Manejo de errores REST (401, 403, 404, 429, 5xx, timeouts, SSL) con reintentos y explicación de la solución.
- Diagnóstico de conectividad por capas: DNS → TCP → TLS → HTTP → autenticación.
- Modo `--offline` con datos de muestra si el sandbox no está disponible.
- Registro de eventos en `logs/inventario.log` y pruebas unitarias.

## Estructura

```
inventario-red-devnet/
├── inventario.py          # Programa principal (CLI)
├── modulos/
│   ├── api_client.py      # Cliente HTTPS + manejo de errores
│   ├── procesador.py      # Normalización, análisis y lectura de formatos
│   ├── exportador.py      # Exportación JSON / YAML / XML / CSV
│   ├── diagnostico.py     # Troubleshooting de la conexión
│   └── configuracion.py   # Carga de config.yaml y .env
├── config.yaml            # Configuración (sin secretos)
├── .env.example           # Plantilla de credenciales
├── datos/muestra_dispositivos.json
├── tests/test_proyecto.py # Pruebas unitarias
├── docs/                  # Solución de problemas (troubleshooting)
├── setup.sh               # Preparación del entorno y permisos
└── requirements.txt
```

## Instalación (DEVASC VM)

```bash
git clone https://github.com/USUARIO/inventario-red-devnet.git
cd inventario-red-devnet
chmod +x setup.sh && ./setup.sh
source venv/bin/activate
```

## Uso

```bash
./inventario.py                          # consulta la API y exporta a todos los formatos
./inventario.py --familia switches       # filtra por familia
./inventario.py --formatos json,csv      # elige formatos
./inventario.py --analizar salidas/inventario.xml
./inventario.py --diagnostico            # prueba la conexión paso a paso
./inventario.py --offline                # usa datos de muestra
python3 -m unittest discover -s tests -v # pruebas
```

## Seguridad y buenas prácticas

- Credenciales en `.env` (permisos `600`, excluido por `.gitignore`), nunca en el código.
- Verificación del certificado TLS activada; se rechaza cualquier URL que no sea `https://`.
- Código modular (una responsabilidad por módulo), nombres descriptivos, docstrings, PEP 8 (verificado con `flake8`).
- Entorno virtual de Python y `requirements.txt` para reproducir dependencias.

## Integrantes

- Nombre Apellido 1
- Nombre Apellido 2
- Nombre Apellido 3
- Nombre Apellido 4
