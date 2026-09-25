from fastapi import FastAPI
from contextlib import asynccontextmanager

from database import conectar_mqtt, desconectar_mqtt
from routers import reservas, establecimientos, personal

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Al arrancar la aplicación
    conectar_mqtt()
    yield
    # Al apagar la aplicación
    desconectar_mqtt()

app = FastAPI(
    title="API UruTurn",
    version="1.0.0",
    description="API REST de Reservas, Establecimientos y Personal",
    lifespan=lifespan
)

# Registrar Routers
app.include_router(reservas.router)
app.include_router(establecimientos.router)
app.include_router(personal.router)

@app.get("/health", tags=["sistema"])
def health():
    return {"estado": "ok"}