# Frontend — GestorPagosMarcovich (React + Vite)

UI web que reemplaza la interfaz de escritorio (CustomTkinter). 4 secciones:
Nueva Solicitud (OCR + PDF), Historial, Alertas/Calendario, Configuración.

## Correr en local

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Requiere el backend corriendo (por defecto en `http://localhost:8000`).

## Variables de entorno

- `VITE_API_URL` — URL del backend. En local: `http://localhost:8000`.
  En producción: la URL pública del servicio de Render.

Copia `.env.example` a `.env` y ajusta si hace falta.

## Deploy en Vercel

- **Framework preset:** Vite
- **Root directory:** `frontend`
- **Build command:** `npm run build`  ·  **Output:** `dist`
- Variable de entorno: `VITE_API_URL` = URL del backend en Render.

## Notas

- Sin librería de router (navegación por estado) para mantener deps mínimas.
- Los firmantes se guardan en `localStorage` del navegador (persisten entre sesiones).
- Las secciones que dependen de BD muestran un aviso si el backend no tiene
  `DATABASE_URL` configurada todavía.
