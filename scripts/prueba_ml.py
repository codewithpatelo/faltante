"""Prueba de acceso a datos de Mercado Libre con token (T2 de la prueba mínima).

Corre en tu computadora. Solo usa la biblioteca estándar de Python.
La clave secreta y el token NO se guardan ni se muestran: el resultado que genera
(resultado_ml.json) solo tiene códigos de respuesta y conteos.

Uso:
    python prueba_ml.py
"""

import getpass
import json
import statistics
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone

API = "https://api.mercadolibre.com"
AUTH = "https://auth.mercadolibre.com.ar/authorization"
REDIRECT_DEFAULT = "https://github.com/codewithpatelo"

# Mezcla: productos de rankings courier publicados en prensa, complementos y controles obvios.
PRODUCTOS = [
    "termo stanley classic 1.2",
    "dji mic mini",
    "roku streaming stick",
    "sports research omega 3",
    "cepillo lateral roborock",
    "filtro purificador xiaomi",
    "capsulas recargables nespresso",
    "maquina leche vegetal",
    "freidora de aire",          # control: debería tener muchísima oferta
    "nut milk maker",            # control: nombre en inglés de un producto poco común
]
CATEGORIAS_HIGHLIGHTS = ["MLA1574", "MLA1000"]  # Hogar, Electrónica


def pedir(url, token=None, datos=None):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if datos is not None:
        body = urllib.parse.urlencode(datos).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            cuerpo = json.loads(e.read() or b"{}")
        except Exception:
            cuerpo = {}
        return e.code, cuerpo
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}


def main():
    print("\n=== Prueba de datos de Mercado Libre ===\n")
    client_id = input("1. Pegá el Client ID (App ID): ").strip()
    redirect = input(f"2. Redirect URI [Enter = {REDIRECT_DEFAULT}]: ").strip() or REDIRECT_DEFAULT

    url = f"{AUTH}?" + urllib.parse.urlencode(
        {"response_type": "code", "client_id": client_id, "redirect_uri": redirect})
    print("\n3. Se abre el navegador para autorizar la app. Si no se abre, copiá este link:\n")
    print("   " + url + "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("   Después de autorizar vas a terminar en tu redirect URI.")
    print("   Copiá lo que viene después de 'code=' en la barra de direcciones (empieza con TG-).\n")
    code = input("4. Pegá el code (vence en pocos minutos y sirve una sola vez): ").strip()
    if "code=" in code:  # por si pegan la URL entera
        code = urllib.parse.parse_qs(urllib.parse.urlparse(code).query).get("code", [code])[0]
    secret = getpass.getpass("5. Pegá la Secret Key (no se ve mientras escribís): ").strip()

    estado, tok = pedir(f"{API}/oauth/token", datos={
        "grant_type": "authorization_code", "client_id": client_id,
        "client_secret": secret, "code": code, "redirect_uri": redirect})
    if estado != 200 or "access_token" not in tok:
        print(f"\nNo se pudo obtener el token (HTTP {estado}): {tok.get('message') or tok.get('error') or tok}")
        print("Causas típicas: el code ya se usó o venció, o el redirect URI no coincide exactamente.")
        return
    token = tok["access_token"]
    print("\nToken obtenido. Corriendo pruebas...\n")

    resultado = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "token_ok": True,
        "scope": tok.get("scope"),
        "busqueda": [],
        "highlights": [],
    }

    st, me = pedir(f"{API}/users/me", token)
    resultado["users_me_status"] = st

    for q in PRODUCTOS:
        st, d = pedir(f"{API}/sites/MLA/search?" + urllib.parse.urlencode({"q": q, "limit": 50}), token)
        fila = {"producto": q, "status": st}
        if st == 200:
            res = d.get("results", [])
            precios = [r["price"] for r in res if isinstance(r.get("price"), (int, float))]
            fila.update({
                "total_publicaciones": d.get("paging", {}).get("total"),
                "resultados_recibidos": len(res),
                "vendedores_distintos_top50": len({(r.get("seller") or {}).get("id") for r in res} - {None}),
                "precio_mediana_ars": statistics.median(precios) if precios else None,
                "campo_sold_quantity_presente": any("sold_quantity" in r for r in res),
                "titulos_ejemplo": [r.get("title") for r in res[:3]],
            })
        else:
            fila["error"] = d.get("message") or d.get("error")
        resultado["busqueda"].append(fila)
        print(f"  {q:<34} HTTP {st}  total={fila.get('total_publicaciones')}  "
              f"vendedores={fila.get('vendedores_distintos_top50')}")

    for cat in CATEGORIAS_HIGHLIGHTS:
        st, d = pedir(f"{API}/highlights/MLA/category/{cat}", token)
        fila = {"categoria": cat, "status": st}
        if st == 200:
            contenido = d.get("content", [])
            fila.update({"items": len(contenido), "tipos": sorted({c.get("type") for c in contenido}),
                         "ids_ejemplo": [c.get("id") for c in contenido[:5]]})
        else:
            fila["error"] = d.get("message") or d.get("error")
        resultado["highlights"].append(fila)
        print(f"  highlights {cat:<23} HTTP {st}  items={fila.get('items')}")

    with open("resultado_ml.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    print("\nListo. Subí el archivo resultado_ml.json al chat (no tiene ni la clave ni el token).")


if __name__ == "__main__":
    main()
