"""Prueba local del nuevo exportar_solicitud_pdf()."""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))

from app.services.exportar import exportar_solicitud_pdf
from pathlib import Path

datos = {
    "empresa": "GOLDEN YEARS MANAGEMENT",
    "sucursal": "TELEFONOS DE MEXICO",
    "fecha_proceso": "23/06/2026",
    "centro_costos": "GYM-SISTEMAS",
    "direccion": "BLVD. MANUEL AVILA CAMACHO 2900",
    "proveedor_nombre": "TELEFONOS DE MEXICO SA DE CV",
    "motivo_pago": "SERVICIO TELEFONICO JUNIO 2026",
    "folio_cfdi": "ABC-123456-789",
    "notas_credito": "",
    "importe_letra": "DOS MIL PESOS 00/100 M.N.",
    "monto_total": 2000.00,
    "banco": "BANAMEX",
    "clabe": "002010077777777771",
    "no_cuenta": "12345678",
    "observaciones": "Sin observaciones adicionales",
    "mes_presupuesto": "JUNIO",
    "mes_pago": "JUNIO",
    "analista_nombre": "LILLY ESTEFANY ARROYO HUERTA",
    "gerente_nombre": "BRUNO CASTANEDA ROVIRA",
    "visto_bno": "DENIS TOLENTINO",
    "depto_finanzas": "PRESUPUESTOS",
    "dir_financiera": "VICTOR NUNEZ",
    "dir_general": "STEVEN MARCOVICH",
}

pdf_bytes = exportar_solicitud_pdf(datos)
out = Path(__file__).parent / "assets" / "test_output.pdf"
out.write_bytes(pdf_bytes)
print(f"PDF generado: {out} ({len(pdf_bytes)} bytes)")
print("Abriendo...")
import subprocess
subprocess.Popen(["start", "", str(out)], shell=True)
