from fastapi.testclient import TestClient
import uuid
from main import app  # Importa la aplicación FastAPI
client = TestClient(app)
nombre = f"Test {uuid.uuid4().hex[:8]}"  # Genera un nombre único para el establecimiento

def test_fixtures_ok(reserva):
    assert reserva["turno"]["estado_reserva"] == "PENDIENTE"