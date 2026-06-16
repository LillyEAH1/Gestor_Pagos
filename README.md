# GestorPagosMarcovich

Gestión de pagos IT del Grupo Marcovich: escaneo de recibos por OCR (Groq Vision),
generación de solicitudes de pago en PDF con formato oficial, historial y
recordatorios de calendario.

> **En migración:** de app de escritorio Windows (CustomTkinter + SQLite) a
> **web app** (React/Vercel + FastAPI/Render + Supabase Postgres + Microsoft Graph).

## Estructura del repo

```
.
├── v60/              App de escritorio LEGACY (referencia de la lógica de negocio).
│                     OCR, generación de PDF y número-a-letra se portan desde aquí.
├── backend/          API FastAPI  (Fase 2) — pendiente
├── frontend/         UI React     (Fase 3) — pendiente
├── .env.example      Plantilla de variables de entorno
└── .gitignore
```

## Roadmap

| Fase | Estado | Descripción |
|------|--------|-------------|
| 0 — Fundación        | ✅ | git, `.gitignore`, secretos en `.env`, estructura |
| 1 — Supabase         | 🟡 | Esquema Postgres listo (`backend/migrations/001_schema.sql`); falta correr el seed en Supabase |
| 2 — Backend FastAPI  | 🟡 | API completa y probada en local; falta **auth** + deploy en Render |
| 3 — Frontend React   | ✅ | 4 secciones, upload + OCR, preview PDF; falta deploy en Vercel |
| 4 — Outlook → Graph  | ⬜ | Recordatorios vía Microsoft Graph API |
| 5 — Bugs + pulido    | ⬜ | OCR incompleto y demás fallos, uno por uno |

> **Pendiente de cuentas del usuario:** Supabase (BD), Render (backend), Vercel
> (frontend), Azure (Graph). El código corre completo en local sin ellas
> (los módulos de BD muestran avisos hasta que exista `DATABASE_URL`).

## Variables de entorno

Copia `.env.example` a `.env` y rellena los valores. **`.env` nunca se sube a git.**

## Cuentas necesarias (producción)

- **Supabase** — base de datos Postgres + auth
- **Render** — hosting del backend (API)
- **Vercel** — hosting del frontend
- **Azure** (registro de app) — para Microsoft Graph (recordatorios de Outlook)
- **Groq** — API key del OCR (ya se tiene; conviene rotarla)
