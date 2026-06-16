"""Modelos Pydantic de entrada/salida de la API."""
from __future__ import annotations
from pydantic import BaseModel


class PagoIn(BaseModel):
    servicio_id: int | None = None
    proveedor_nombre: str = ""
    empresa: str = ""
    sucursal: str = ""
    centro_costos: str = ""
    direccion: str = ""
    motivo_pago: str = ""
    folio_cfdi: str = ""
    notas_credito: float = 0
    monto_total: float = 0
    importe_letra: str = ""
    banco: str = ""
    clabe: str = ""
    no_cuenta: str = ""
    forma_pago: str = ""
    observaciones: str = ""
    mes_presupuesto: str = ""
    mes_pago: str = ""
    mes: int | None = None
    anio: int | None = None
    estatus: str = "PENDIENTE"
    fecha_proceso: str = ""
    pdf_ruta: str = ""
    analista_nombre: str = ""
    gerente_nombre: str = ""


class PagoUpdate(BaseModel):
    """Todos opcionales — solo se actualiza lo que venga."""
    proveedor_nombre: str | None = None
    empresa: str | None = None
    sucursal: str | None = None
    centro_costos: str | None = None
    direccion: str | None = None
    motivo_pago: str | None = None
    folio_cfdi: str | None = None
    notas_credito: float | None = None
    monto_total: float | None = None
    importe_letra: str | None = None
    banco: str | None = None
    clabe: str | None = None
    no_cuenta: str | None = None
    forma_pago: str | None = None
    observaciones: str | None = None
    mes_presupuesto: str | None = None
    mes_pago: str | None = None
    mes: int | None = None
    anio: int | None = None
    estatus: str | None = None
    fecha_proceso: str | None = None
    analista_nombre: str | None = None
    gerente_nombre: str | None = None


class ProveedorIn(BaseModel):
    nombre: str
    banco: str = ""
    clabe: str = ""


class BancoIn(BaseModel):
    nombre: str
    prefijo_clabe: str = ""


class GroqKeyIn(BaseModel):
    api_key: str


class NumeroLetraIn(BaseModel):
    monto: float


# Para generar PDF/Excel se reutiliza el cuerpo del pago como dict libre.
class DocumentoPagoIn(BaseModel):
    datos: dict
