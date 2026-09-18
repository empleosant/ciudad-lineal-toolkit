"""
Comprueba la cascada de IA contra las APIs de verdad.

`pruebas/cascada.py` comprueba la lógica con proveedores de mentira, y eso no
puede decir si los NOMBRES de modelo de `comun/ia.py` existen todavía. Los
proveedores cierran modelos antes de la fecha que anuncian y los catálogos
gratuitos rotan: un nombre caducado no se nota en ninguna batería, solo en
producción y en forma de lentitud.

Esto es lo que lo dice. NO es una batería: habla con las APIs y, con
`--llamar`, gasta unos pocos tokens de cuota.

    ~/.venvs/sispe/bin/python scripts/comprobar_ia.py            solo el catálogo
    ~/.venvs/sispe/bin/python scripts/comprobar_ia.py --llamar   y una llamada mínima

Las claves salen del entorno o de `.streamlit/secrets.toml` (que no se
versiona). Los proveedores sin clave se saltan y se dicen, no son un fallo:
la cascada está hecha para funcionar con las que haya.

Devuelve 0 si todo lo que hay configurado existe, y 1 si algún nombre de
modelo ya no está en el catálogo de su proveedor: eso es lo que hay que
corregir en PROVEEDORES.
"""

import os
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

LLAMAR = "--llamar" in sys.argv


def carga_claves():
    """Las claves del entorno, completadas con las del secrets.toml local.

    Streamlit no está levantado, así que `st.secrets` no sirve aquí: se lee el
    archivo a mano, que para esto basta.
    """
    ruta = os.path.join(RAIZ, ".streamlit", "secrets.toml")
    if not os.path.exists(ruta):
        return
    try:
        import tomllib
        with open(ruta, "rb") as f:
            datos = tomllib.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"No he podido leer {ruta}: {type(e).__name__}: {e}")
        return
    for clave, valor in datos.items():
        if isinstance(valor, str) and clave.endswith("_API_KEY"):
            os.environ.setdefault(clave, valor)


carga_claves()

from comun import ia   # noqa: E402  después de las claves, que las lee al importar


def catalogo(prov):
    """Los nombres de modelo que ESE proveedor dice tener ahora mismo.

    Devuelve (lista, aviso). La lista vacía con aviso significa «no he podido
    preguntar», que no es lo mismo que «no tiene modelos».
    """
    cli = ia._cliente(prov)
    if cli is None:
        return [], "no he podido abrir el cliente (¿falta la librería?)"
    try:
        if prov == "gemini":
            # Vienen como "models/gemini-3.5-flash-lite": se deja el nombre a secas.
            return [m.name.split("/")[-1] for m in cli.models.list()], ""
        return [m.id for m in cli.models.list().data], ""
    except Exception as e:  # noqa: BLE001
        return [], f"{type(e).__name__}: {str(e)[:120]}"


def una_llamada(prov, modelo):
    """Una llamada mínima de verdad: (ok, detalle). Gasta unos tokens."""
    cli = ia._cliente(prov)
    try:
        r = ia._una_llamada(prov, cli, modelo, "Responde únicamente con la palabra ok.",
                            "ok", 16, False, False)
        return True, (r or "")[:30].replace("\n", " ")
    except Exception as e:  # noqa: BLE001
        etiqueta = "NO EXISTE" if ia.no_existe(e) else type(e).__name__
        return False, f"{etiqueta}: {str(e)[:100]}"


def main():
    print(f"Cascada configurada: {' → '.join(ia.ORDEN)}")
    sin_clave = [p for p in ia.ORDEN if not ia.tiene_clave(p)]
    if sin_clave:
        print(f"Sin clave (se saltan en producción): {', '.join(sin_clave)}")
    print()

    fantasmas = []      # (proveedor, modelo) configurados que ya no existen
    comprobados = 0     # proveedores cuyo catálogo se ha podido leer
    for prov in ia.ORDEN:
        if not ia.tiene_clave(prov):
            continue
        configurados = ia.PROVEEDORES[prov]["modelos"]
        disponibles, aviso = catalogo(prov)
        print(f"── {prov}")
        if aviso:
            print(f"   No he podido leer su catálogo: {aviso}")
        else:
            comprobados += 1
            print(f"   {len(disponibles)} modelos en su catálogo")

        for modelo in configurados:
            if aviso:
                estado = "sin catálogo que comparar"
            elif modelo in disponibles:
                estado = "en el catálogo"
            elif any(modelo in d or d in modelo for d in disponibles):
                # OpenRouter llama "openrouter/free" a su enrutador y hay
                # proveedores que añaden sufijos de versión al nombre.
                estado = "parecido en el catálogo, no exacto"
            else:
                estado = "NO ESTÁ EN EL CATÁLOGO"
                fantasmas.append((prov, modelo))
            linea = f"   · {modelo:32} {estado}"
            if LLAMAR:
                ok, detalle = una_llamada(prov, modelo)
                linea += f"  →  {'responde' if ok else 'falla'}: {detalle}"
                if not ok and (prov, modelo) not in fantasmas and "NO EXISTE" in detalle:
                    fantasmas.append((prov, modelo))
            print(linea)

        transcripcion = ia.PROVEEDORES[prov].get("transcripcion")
        if transcripcion:
            esta = (not aviso) and transcripcion in disponibles
            print(f"   · {transcripcion:32} "
                  f"{'en el catálogo' if esta else 'NO ESTÁ EN EL CATÁLOGO (transcripción)'}")
            if not esta and not aviso:
                fantasmas.append((prov, transcripcion))
        print()

    if not comprobados:
        # Sin esto el script decía «todos los modelos existen» sin haber
        # preguntado a nadie, que es peor que no decir nada: da por bueno
        # justo lo que se quería comprobar.
        print("NO HE COMPROBADO NADA: ningún proveedor con clave que respondiera.")
        print("Pon las claves en el entorno o en .streamlit/secrets.toml y repite.")
        return 2

    if fantasmas:
        print("HAY QUE CORREGIR `PROVEEDORES` en comun/ia.py:")
        for prov, modelo in fantasmas:
            print(f"  · {prov}: {modelo}")
        print("\nMientras no se corrija, la cascada los descarta sola en cuanto")
        print("los prueba una vez (ver `no_existe`), pero cuesta un intento por")
        print("sesión y el panel de mantenimiento lo avisa.")
        return 1

    print(f"Todos los modelos configurados existen en el catálogo de su proveedor "
          f"({comprobados} de {len(ia.ORDEN)} proveedores comprobados).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
