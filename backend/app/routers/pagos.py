"""Endpoints CRUD de pagos + estado de cuenta + servicios próximos."""
from fastapi import APIRouter, HTTPException, Query

from app import db
from app.schemas import PagoIn, PagoUpdate

router = APIRouter(prefix="/api/pagos", tags=["pagos"])


def _check_db():
    if not db.db_disponible():
        raise HTTPException(status_code=503, detail="Base de datos no configurada (DATABASE_URL)")


@router.get("")
async def listar(mes: int = Query(...), anio: int = Query(...)):
    _check_db()
    return db.get_pagos_mes(mes, anio)


@router.get("/buscar")
async def buscar(q: str = Query(..., min_length=1)):
    _check_db()
    return db.buscar_pagos(q)


@router.get("/estado-cuenta")
async def estado_cuenta(mes: int = Query(...), anio: int = Query(...)):
    _check_db()
    return db.estado_cuenta_mes(mes, anio)


@router.get("/proximos")
async def proximos(dias: int = 30):
    _check_db()
    return db.servicios_proximos(dias)


@router.get("/{pago_id}")
async def obtener(pago_id: int):
    _check_db()
    pago = db.get_pago(pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago


@router.post("", status_code=201)
async def crear(body: PagoIn):
    _check_db()
    new_id = db.crear_pago(body.model_dump())
    return {"id": new_id}


@router.patch("/{pago_id}")
async def actualizar(pago_id: int, body: PagoUpdate):
    _check_db()
    if not db.get_pago(pago_id):
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    db.actualizar_pago(pago_id, body.model_dump(exclude_none=True))
    return db.get_pago(pago_id)


@router.delete("/{pago_id}", status_code=204)
async def eliminar(pago_id: int):
    _check_db()
    db.eliminar_pago(pago_id)
