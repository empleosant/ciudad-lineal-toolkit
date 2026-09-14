"""El commit que está corriendo, para saber qué versión hay desplegada."""

import os
import subprocess

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def commit():
    """Hash corto del commit, o "desconocida" si no hay repositorio a mano."""
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_RAIZ,
            capture_output=True, text=True, timeout=5, check=True,
        )
        return salida.stdout.strip() or "desconocida"
    except Exception:  # noqa: BLE001
        return "desconocida"
