Python

from fastapi import FastAPI
from contextlib import asynccontextmanager

# Importas los routers de cada módulo
from routers import reservas, establecimientos, personal

# Si manejas el ciclo de vida (lifespan) con la conexión a MySQL y MQTT:
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar pool de base de datos y MQTT aquí
    yield
    # Cerrar conexiones aquí

app = FastAPI(
    title="API UruTurn",
    version="1.0.0",
    description="API REST de Reservas, Establecimientos y Personal",
    lifespan=lifespan
)

# Incluyes los routers en la aplicación principal
app.include_router(reservas.router)
app.include_router(establecimientos.router)
app.include_router(personal.router)

@app.get("/health", tags=["sistema"])
def health():
    return {"estado": "ok"}