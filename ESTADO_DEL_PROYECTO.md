# Estado del proyecto — GestorPagosMarcovich (Select Shop MB)

> **Documento de continuidad.** Si retomas en otra máquina o sesión, lee esto
> primero: resume arquitectura, qué está en producción, credenciales, cómo correr
> y qué falta. Es la "memoria" durable del proyecto (vive en GitHub).
>
> Última actualización: 2026-06-23.

---

## 1. Qué es

Migración de una app de **escritorio Windows** (CustomTkinter + SQLite + Outlook
COM — carpeta `v60/`, conservada solo como referencia) a una **web app**:

```
Navegador ─> Vercel (React/Vite)  ─HTTP─>  Render (FastAPI)  ─>  Supabase (Postgres)
                                                    └─> Groq Vision (OCR)
```

Gestiona pagos IT del grupo: escaneo de recibos por OCR, generación de la
Solicitud de Pago oficial en PDF, historial y alertas de vencimiento.

**Marca:** Select Shop MB (NO "Grupo Marcovich"). Tema: negro + naranja `#e8601c`.

---

## 2. Producción (URLs en vivo)

| Pieza | URL / referencia |
|-------|------------------|
| Frontend (Vercel) | https://gestor-pagos-ecru.vercel.app |
| Backend (Render)  | https://gestor-pagos-y4na.onrender.com |
| Backend health    | https://gestor-pagos-y4na.onrender.com/health |
| Repo (GitHub)     | https://github.com/LillyEAH1/Gestor_Pagos (rama `main`) |
| Base de datos     | Supabase, proyecto **gestor-pagos** (AWS us-east-2) |

> Render plan free: el backend "duerme" tras ~15 min sin uso; primer request
> tarda ~50s en despertar. Normal.

---

## 3. Variables de entorno (SECRETOS — no están en git)

Viven en `.env` (raíz, ignorado por git) en local, y en los dashboards de
Render/Vercel en producción. **Respáldalas aparte al cambiar de máquina.**

| Variable | Dónde se usa | Valor |
|----------|--------------|-------|
| `GROQ_API_KEY` | backend (OCR) | en tu `.env` local y en Render |
| `DATABASE_URL` | backend (BD) | connection string de Supabase (pooler, puerto 5432) en tu `.env` y en Render |
| `CORS_ORIGINS` | backend | `*` por ahora (sin auth). Al poner login, fijar a la URL de Vercel |
| `VITE_API_URL` | frontend | la URL de Render (configurada en Vercel) |

Plantilla: `.env.example`. Para regenerar `.env` en otra PC, copia esos valores
(o sácalos de los dashboards de Render/Supabase).

---

## 4. Cómo correr en local

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
uvicorn app.main:app --port 8000  # http://localhost:8000/docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

`.env` (raíz) debe tener `GROQ_API_KEY` y `DATABASE_URL`. El frontend usa
`VITE_API_URL` (default `http://localhost:8000`).

### Recargar datos en Supabase
```bash
cd backend
.venv\Scripts\python migrations\... # esquema: app ya creada; correr 001_schema.sql si BD nueva
.venv\Scripts\python import_excel.py "ruta\PagosIT.xlsx"   # carga/reemplaza datos reales
```
`import_excel.py` hace TRUNCATE + reload (re-ejecutable). `seed.py` es el respaldo
de catálogos (bancos) y pagos Abril/Mayo si no hubiera Excel.

---

## 5. Estructura del repo

```
backend/        API FastAPI (Render)
  app/main.py         app + CORS + routers
  app/db.py           capa Postgres (psycopg pool)
  app/services/       numero_letra, ocr_scanner, exportar (PDF/Excel)
  app/routers/        ocr, documentos, pagos, catalogos
  migrations/001_schema.sql   esquema Postgres
  seed.py / import_excel.py   carga de datos
  assets/logos/       plantilla del PDF + logos
frontend/       React + Vite (Vercel)
  src/App.jsx, pages/, api.js, store.js, styles.css
v60/            App de escritorio LEGACY (solo referencia)
render.yaml     Blueprint de Render
```

---

## 6. Estado por fases

| Fase | Estado |
|------|--------|
| 0 — Fundación (git, secretos en .env) | ✅ |
| 1 — Supabase (esquema + datos reales del Excel: **397 prov**, 35 emp/CC, 65 servicios, 175 pagos abr/may/jun 2026) | ✅ |
| 2 — Backend FastAPI (OCR, PDF, Excel, CRUD) desplegado en Render | ✅ |
| 3 — Frontend React desplegado en Vercel, look del .exe (negro+naranja) | ✅ |
| **Auth (login)** | ⬜ **PENDIENTE** — la API está abierta (CORS `*`). Es lo primero antes de blindar |
| 4 — Outlook → Microsoft Graph (recordatorios) | ⬜ |
| 5 — OCR (afinar) | 🔄 En progreso |

---

## 7. Decisiones y "gotchas" (NO repetir errores)

- **Marca = Select Shop MB**, no "Grupo Marcovich". Tema negro + naranja `#e8601c`,
  barras de sección oscuras, look del `.exe` (al usuario le importa).
- **OCR: un prompt POR PROVEEDOR** (Telmex, Totalplay, Digital Copy… traen la info
  distinta). NO homologar la lectura. El usuario explicará el detalle del OCR.
- **OCR output (2026-06-23):** solo devuelve 9 campos al frontend: `empresa_cliente`,
  `sucursal`, `proveedor`, `motivo_pago`, `factura_no`, `monto`, `observaciones`,
  `mes_presupuesto`, `mes_pago`, `anio_factura`. Los campos internos (banco, clabe,
  no_cuenta, DV) se usan solo para construir motivo_pago y observaciones.
- **Conciliación OCR (update/create)**: idea validada (match por dígitos de cuenta
  + mes + año) pero **CONGELADA** a petición del usuario hasta tener todo en prod.
- **Producción primero**: el usuario priorizó deploy antes que features.
- **Bug heredado del OCR**: en `v60/ocr_scanner.py` `_groq_vision` no pasaba
  `texto_crudo` a `_normalizar_groq` (salvavidas regex muertos). **Ya corregido en
  `backend/app/services/ocr_scanner.py`**; sigue presente en el legacy `v60/`.
- **Backend en server (no Windows)**: PDF→imagen con PyMuPDF (no PowerShell),
  fallback regex del texto nativo (no Windows.Media.Ocr).
- **CORS abierto** (`*`, sin credenciales) mientras no haya auth. Al meter login:
  fijar `CORS_ORIGINS` a la URL de Vercel y reactivar credenciales en `main.py`.
- **Supabase**: usar el **pooler** (puerto 5432) en `DATABASE_URL`.

---

## 8. Cambios recientes (2026-06-22 / 2026-06-23)

- **Proveedores importados:** `backend/scripts/importar_proveedores.py` leyó la hoja
  BASE de *SOLICITUD DE PAGO OK (SIMULTANEO) 12.xlsm* y pobló Supabase: 14 → 397
  proveedores (nombre, beneficiario, banco, CLABE, no_cuenta, moneda).
- **OCR output reducido a 9 campos** (ver sección 7).
- **Nombre del PDF corregido:** `Solicitud_<NOM_CORTO>_<PROVEEDOR>_<DDMMYY>_<MES>.pdf`
  Ej: `Solicitud_GYM_TELEFONOS DE MEXICO_220626_JUN.pdf`. El sufijo legal
  (SAB DE CV, SAPI DE CV…) se elimina automáticamente. Lógica replicada en
  backend (`documentos.py`) y frontend (`NuevaSolicitud.jsx`).
- **Scripts de mantenimiento:** `backend/scripts/importar_proveedores.py` (re-ejecutable)
  y `backend/scripts/verificar_bd.py`.

---

## 9. Pendientes (orden sugerido)

1. **Auth / login** (Supabase Auth) — cerrar la API antes de uso real.
2. **empresas_cc:** poblar con las combinaciones empresa+sucursal+CC del Excel maestro.
   Pendiente definir si empresa y sucursal son dropdowns independientes o combinados.
3. **OCR por proveedor** — afinar prompts; el usuario indicará qué proveedores faltan.
4. **Fase 4** — recordatorios vía Microsoft Graph (reemplazo de Outlook COM).
5. Pulido: completar montos $0.00 (Digital Copy, Zona IT, Garin, COI del Excel),
   botón "+ Generar pago" desde Alertas, etc.

---

## 10. Cambio de computadora — checklist para no perder nada

- [x] **Código**: ya está todo en GitHub → en la PC nueva, `git clone` y listo.
- [ ] **`.env`** (secretos): cópialo aparte (USB / gestor de contraseñas). NO está
      en GitHub. Alternativa: re-crear desde `.env.example` con los valores de los
      dashboards de Render/Supabase.
- [ ] **Memoria de Claude** (opcional): carpeta
      `C:\Users\<usuario>\.claude\projects\C--Users-...-GestorPagosIT-v60\memory\`.
      Cópiala al `.claude` de la PC nueva si quieres que Claude auto-recuerde. Si la
      ruta del proyecto cambia (otro usuario de Windows), Claude no la auto-enlaza,
      pero **este documento ya contiene todo lo importante**.
- [ ] **venv / node_modules**: NO hace falta copiarlos; se regeneran con
      `pip install -r requirements.txt` y `npm install`.
- [x] **Producción**: sigue viva pase lo que pase (Vercel/Render/Supabase son la nube).
