import importlib.util
from pathlib import Path

# Carga la versión principal del servicio con el nombre solicitado.
_TARGET = Path(__file__).with_name("reservas/api-reserva.py")
_SPEC = importlib.util.spec_from_file_location("api_reserva_module", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"No se pudo cargar el archivo de la API: {_TARGET}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

# Reexporta la aplicación para que FastAPI/Uvicorn siga levantando la app
# con la importación histórica app:app.
app = _MODULE.app
