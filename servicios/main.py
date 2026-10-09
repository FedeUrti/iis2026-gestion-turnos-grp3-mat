import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
import mysql.connector

from routers import reservas, establecimientos, personal, facturas
from worker_facturas import facturar_turnos_atendidos
from worker_reservas import procesar_reservas_mqtt, procesar_reservas_pendientes

logger = logging.getLogger(__name__)
TURNOS_INTERVAL_SECONDS = int(os.getenv("TURNOS_INTERVAL_SECONDS", "60"))
if TURNOS_INTERVAL_SECONDS < 1:
    raise ValueError("TURNOS_INTERVAL_SECONDS debe ser mayor que cero.")
FACTURAS_INTERVAL_SECONDS = int(os.getenv("FACTURAS_INTERVAL_SECONDS", "300"))
if FACTURAS_INTERVAL_SECONDS < 1:
    raise ValueError("FACTURAS_INTERVAL_SECONDS debe ser mayor que cero.")


async def procesar_turnos_periodicamente():
    while True:
        await asyncio.sleep(TURNOS_INTERVAL_SECONDS)
        try:
            procesadas = await asyncio.to_thread(
                lambda: (
                    procesar_reservas_mqtt()
                    + procesar_reservas_pendientes()
                )
            )
            logger.info("Ciclo de turnos completado; reservas procesadas: %s", procesadas)
        except mysql.connector.Error:
            logger.exception("Error al procesar las reservas.")


async def facturar_turnos_periodicamente():
    while True:
        await asyncio.sleep(FACTURAS_INTERVAL_SECONDS)
        try:
            facturados = await asyncio.to_thread(facturar_turnos_atendidos)
            logger.info("Ciclo de facturación completado; turnos facturados: %s", facturados)
        except mysql.connector.Error:
            logger.exception("Error al facturar los turnos atendidos.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    tarea_turnos = asyncio.create_task(procesar_turnos_periodicamente())
    tarea_facturas = asyncio.create_task(facturar_turnos_periodicamente())
    try:
        yield
    finally:
        for tarea in (tarea_turnos, tarea_facturas):
            tarea.cancel()
        await asyncio.gather(tarea_turnos, tarea_facturas, return_exceptions=True)

app = FastAPI(
    title="API UruTurn",
    version="1.0.0",
    description="API REST de reservas, establecimientos, personal y facturas con procesamiento periódico.",
    lifespan=lifespan
)

# Registrar Routers
app.include_router(reservas.router)
app.include_router(establecimientos.router)
app.include_router(personal.router)
app.include_router(facturas.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": jsonable_encoder(exc.errors())},
    )


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    for path_item in openapi_schema["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            validation_response = responses.pop("422", None)
            if validation_response is not None:
                responses.setdefault("400", validation_response)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


@app.get("/health", tags=["sistema"])
def health():
    return {"estado": "ok"}