# Backend — GestorPagosMarcovich API (FastAPI)

API que reemplaza la lógica de la app de escritorio: OCR (Groq Vision),
generación de PDF de solicitud, Excel de estado de cuenta, e historial de pagos
sobre Supabase Postgres.

## Correr en local

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows;  source .venv/bin/activate en Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Variables de entorno (en `.env` de la raíz del repo, o del sistema):

- `GROQ_API_KEY` — para el OCR.
- `DATABASE_URL` — Connection string de Supabase (los endpoints de BD lo requieren).
- `CORS_ORIGINS` — URLs del frontend separadas por coma.

Docs interactivos: http://localhost:8000/docs

## Endpoints

| Método | Ruta | Qué hace |
|--------|------|----------|
| POST | `/api/ocr/escanear` | Sube PDF/imagen → campos extraídos |
| GET  | `/api/ocr/probar` | Verifica la Groq key |
| POST | `/api/documentos/pdf` | Genera el PDF de solicitud |
| GET  | `/api/documentos/excel?mes&anio` | Excel de estado de cuenta |
| POST | `/api/documentos/numero-letra` | Importe en letra |
| GET/POST/PATCH/DELETE | `/api/pagos...` | CRUD de pagos, historial, búsqueda |
| GET  | `/api/pagos/estado-cuenta` | Totales pagado/pendiente del mes |
| GET  | `/api/pagos/proximos` | Servicios recurrentes por vencer |
| GET/POST | `/api/catalogos/...` | Proveedores, bancos, empresas |

## Deploy en Render

- **Build command:** `pip install -r requirements.txt`
- **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Variables de entorno: `GROQ_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS`.
- Para Supabase usa el **Connection Pooler** (puerto 6543) en `DATABASE_URL`.
