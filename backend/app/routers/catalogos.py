"""Endpoints de catálogos: proveedores, bancos, empresas/sucursales/CC."""
from fastapi import APIRouter, HTTPException

from app import db
from app.schemas import ProveedorIn, BancoIn

router = APIRouter(prefix="/api/catalogos", tags=["catalogos"])


def _check_db():
    if not db.db_disponible():
        raise HTTPException(status_code=503, detail="Base de datos no configurada (DATABASE_URL)")


@router.get("/proveedores")
async def proveedores(nombres_only: bool = False):
    _check_db()
    if nombres_only:
        return db.list_nombres_proveedores()
    return db.list_proveedores()


@router.post("/proveedores", status_code=201)
async def crear_proveedor(body: ProveedorIn):
    _check_db()
    db.upsert_proveedor(body.model_dump())
    return {"ok": True}


@router.get("/bancos")
async def bancos():
    _check_db()
    return db.list_bancos()


@router.post("/bancos", status_code=201)
async def crear_banco(body: BancoIn):
    _check_db()
    db.upsert_banco(body.model_dump())
    return {"ok": True}


@router.get("/empresas")
async def empresas():
    _check_db()
    return db.list_empresas_cc()
