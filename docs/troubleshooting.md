# Solución de problemas de REST API

Cuando una llamada a la API falla, se revisa por capas, de abajo hacia arriba.
El comando `./inventario.py --diagnostico` hace estas pruebas automáticamente.

| Capa | Cómo se prueba | Síntoma | Causa probable | Solución |
|------|----------------|---------|----------------|----------|
| DNS | `nslookup sandboxdnac.cisco.com` | `Name or service not known` | Sin Internet o DNS mal configurado en la VM | Revisar adaptador de red de VirtualBox (NAT), `/etc/resolv.conf` |
| TCP | `nc -zv sandboxdnac.cisco.com 443` | `Connection timed out` | Firewall o proxy bloquea el puerto 443 | Probar otra red, configurar proxy (`HTTPS_PROXY`) |
| TLS | `openssl s_client -connect sandboxdnac.cisco.com:443` | `SSLError: CERTIFICATE_VERIFY_FAILED` | Certificados de la VM desactualizados o hora del sistema incorrecta | `sudo apt-get install --reinstall ca-certificates`, `timedatectl` |
| HTTP | `curl -i https://...` | Código 4xx / 5xx | Ver tabla de códigos | Ver tabla de códigos |

## Códigos HTTP más comunes

| Código | Significado | Qué hacer |
|--------|-------------|-----------|
| 200 | OK | Todo correcto |
| 400 | Bad Request | Revisar parámetros, cuerpo JSON y `Content-Type: application/json` |
| 401 | Unauthorized | Usuario/contraseña incorrectos o token vencido (el token de Catalyst Center dura ~60 min). Pedir un token nuevo |
| 403 | Forbidden | Credenciales válidas pero sin permiso. El sandbox always-on es de solo lectura: para POST/PUT/DELETE usar uno reservado |
| 404 | Not Found | URL o ruta del endpoint mal escrita (`/dna/intent/api/v1/network-device`) |
| 405 | Method Not Allowed | Se usó un verbo HTTP que el endpoint no acepta |
| 429 | Too Many Requests | Límite de tasa. Esperar lo que indica la cabecera `Retry-After`. El script reintenta solo |
| 500/502/503/504 | Errores del servidor | No es culpa del cliente. Reintentar más tarde; el script reintenta con espera exponencial |

## Caso real encontrado: certificado autofirmado del sandbox

Al probar con `curl -v` la conexión llegó a TCP 443, pero falló en TLS con
`SSL certificate problem: self signed certificate in certificate chain` (curl error 60).
DNS y TCP estaban bien, así que el problema estaba en la capa TLS: el sandbox usa un
certificado que no firmó ninguna autoridad de confianza del sistema.

Soluciones, de la más segura a la más simple:

1. **Confiar solo en ese certificado** (recomendado): guardarlo y apuntar `verificar_ssl` a él.
   ```bash
   mkdir -p certs
   openssl s_client -showcerts -connect sandboxdnac.cisco.com:443 </dev/null 2>/dev/null \
     | awk '/BEGIN CERT/,/END CERT/' > certs/sandboxdnac.pem
   curl --cacert certs/sandboxdnac.pem -X POST -u devnetuser:'Cisco123!' \
     https://sandboxdnac.cisco.com/dna/system/api/v1/auth/token
   ```
   Si funciona, en `config.yaml`: `verificar_ssl: "certs/sandboxdnac.pem"`.
2. **No verificar** (solo laboratorio): `curl -k ...` y `verificar_ssl: false`. El tráfico
   sigue cifrado, pero no se comprueba la identidad del servidor (riesgo de
   *man-in-the-middle*). Nunca en producción.

## Problemas comunes con el sandbox always-on

- **401 con las credenciales correctas**: el sandbox es compartido y a veces otro usuario cambia la contraseña. Revisar el foro DevNet Sandbox de la comunidad Cisco o reservar el sandbox de Catalyst Center.
- **Sandbox caído o en mantenimiento**: ejecutar `./inventario.py --offline`, que usa `datos/muestra_dispositivos.json` con el mismo formato que la API.

## Comandos útiles para depurar

```bash
# Ver el detalle de lo que hizo el script
tail -n 30 logs/inventario.log
grep ERROR logs/inventario.log

# Probar la autenticación con curl (equivalente a lo que hace el script)
curl -s -X POST -u devnetuser:'Cisco123!' \
  https://sandboxdnac.cisco.com/dna/system/api/v1/auth/token

# Probar el endpoint de inventario con el token obtenido
curl -s -H "X-Auth-Token: <TOKEN>" \
  https://sandboxdnac.cisco.com/dna/intent/api/v1/network-device | python3 -m json.tool | head -40
```
