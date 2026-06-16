"""
GestorPagosIT — app.py v60
Cambios vs v25:
- Pestaña "Catálogos" eliminada del sidebar (los bancos son un ComboBox en el formulario)
- Campo Banco en formulario: ahora es ComboBox con los bancos de la BD (autoinfiere de CLABE)
- Botón Eliminar: limpiar campos inmediatamente sin confirmación si no hay registro en BD
- OCR v26: extrae los 11 campos con patrones específicos por proveedor
- Servicios recurrentes: poblado con 33 servicios reales del PDF entregado (Telmex/Totalplay/Telcel)
- BD limpia de pagos de prueba; pagos de historial se piden al usuario que los introduzca
- _limpiar() también resetea el ComboBox de banco
- Cambios vs v24:
- OCR NUNCA llena firmantes (analista/gerente siempre son manuales)
- _limpiar() y botón Eliminar: dejan campos COMPLETAMENTE vacíos (overlay visible, modo reset)
- BD limpia al arrancar: la app ya no muestra datos de la sesión anterior
- Vista previa PDF: ventana Toplevel emergente (NO abre navegador)
- Pantalla config: autodetecta ruta OneDrive como SUGERENCIA editable; nombre de usuario es MANUAL
- Logo sidebar: más ancho (hasta 170px), "Pagos corporativos" en blanco
- ICO del .exe: solo el símbolo naranja del logo (sin el texto "selectshop")
- Tabla bancos en BD con CRUD en pantalla "Catálogos" (sidebar)
- Tabla plantillas_observaciones con CRUD en pantalla "Catálogos"
- Al generar PDF, guarda TODOS los campos incluyendo dirección y firmantes en la BD
- BD regenerada con 398 proveedores, 21 bancos, 11 plantillas de observaciones
- OCR completa 11 campos (folio + banco desde CLABE, sin tocar firmantes)
- Banco se autoinfiere del prefijo CLABE cuando el OCR no lo detecta explícitamente
"""
import threading, os, sys, subprocess, tempfile
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date
from pathlib import Path
from PIL import Image

import config
from database import Database
from exportar import exportar_solicitud_pdf, exportar_estado_cuenta_xlsx
from outlook_alertas import crear_recordatorios_lote, verificar_outlook, purgar_citas_outlook, eliminar_eventos_prueba
from ocr_scanner import escanear_recibo, probar_groq_conexion
from numero_letra import numero_a_letra

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ── Paleta SelectShop (negro sidebar, naranja acento, fondo blanco) ──────────
SIDEBAR_BG  = "#1A1A1A"
FONDO       = "#F5F5F5"
BLANCO      = "#FFFFFF"
BORDE       = "#E0E0E0"
TEXTO_SB    = "#FFFFFF"
TEXTO       = "#1A1A1A"
MUTED       = "#777777"
AZUL_DARK   = "#1A1A1A"
AZUL_MED    = "#E85D04"
ACENTO      = "#E85D04"
ACENTO_HOV  = "#C74E02"
ACENTO2     = "#E85D04"
SB_ACTIVE   = "#E85D04"
SB_HOVER    = "#333333"
VERDE       = "#2D6A4F"
VERDE_BG    = "#D8F3DC"
ROJO        = "#922B21"
ROJO_BG     = "#FADBD8"
AMBAR       = "#7D6608"
AMBAR_BG    = "#FEF9E7"

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

EMPRESAS = [
    "BH. BE HEALTHY COMERCIALIZADORA","BH SOLAR","BLOOM & BLUSH",
    "COMERCIALIZADORA DE MARCAS JSB","COMERCIALIZADORA ONLINE NH",
    "ENFERMERAS UNIDAS PLUS","GOLDEN YEARS MANAGEMENT",
    "MB COMERCIALIZADORA EN LINEA","MOSAIC CARE & HEALTH",
    "SELECT SHOP MB","SM DISTRIBUIDORA DIGITAL","INMOBILIARIA EISHEL",
    "ALEGARAT","ZONA ZELU","DONKERTECH","MW MED SUPPLY MEDICAL",
]
EMPRESAS_ALIAS = {
    "MW MED SUPPLY MEDICAL":        "MW MED SUPPLY MEDICAL",
    "MW MED":                       "MW MED SUPPLY MEDICAL",
    "BLOOM & BLUSH":                "BLOOM & BLUSH",
    "BLOOM AND BLUSH":              "BLOOM & BLUSH",
    "BH BE HEALTHY":                "BH. BE HEALTHY COMERCIALIZADORA",
    "BH SOLAR":                     "BH SOLAR",
    "ENFERMERAS UNIDAS PLUS":       "ENFERMERAS UNIDAS PLUS",
    "ENFERMERAS UNIDAS":            "ENFERMERAS UNIDAS PLUS",
    "GOLDEN YEARS MANAGEMENT":      "GOLDEN YEARS MANAGEMENT",
    "GOLDEN YEARS":                 "GOLDEN YEARS MANAGEMENT",
    "MB COMERCIALIZADORA EN LINEA": "MB COMERCIALIZADORA EN LINEA",
    "MB COMERCIALIZADORA":          "MB COMERCIALIZADORA EN LINEA",
    "COMERCIALIZADORA DE MARCAS":   "COMERCIALIZADORA DE MARCAS JSB",
    "COMERCIALIZADORA ONLINE":      "COMERCIALIZADORA ONLINE NH",
    "SELECT SHOP MB":               "SELECT SHOP MB",
    "SELECT SHOP":                  "SELECT SHOP MB",
    "SM DISTRIBUIDORA DIGITAL":     "SM DISTRIBUIDORA DIGITAL",
    "SM DISTRIBUIDORA":             "SM DISTRIBUIDORA DIGITAL",
    "MOSAIC CARE":                  "MOSAIC CARE & HEALTH",
    "INMOBILIARIA EISHEL":          "INMOBILIARIA EISHEL",
    "ALEGARAT":                     "ALEGARAT",
    "ZONA ZELU":                    "ZONA ZELU",
    "DONKERTECH":                   "DONKERTECH",
}
SUCURSALES = [
    "CORPORATIVO POLANCO PISO 13","CORPORATIVO POLANCO PISO 16",
    "TEPOTZOTLAN II","TEPOTZOTLAN III","IZTAPALAPA","CISNES",
    "NAUCALPAN BH BE HEALTHY","NAUCALPAN BH SOLAR","HORACIO 1840",
    "NEBRASKA","T. POLANCO","T. ARAGON","T. CUERNAVACA",
]
CENTROS = [
    "SISTEMAS","FINANZAS","LOGISTICA","ADMINISTRACION","CONTABILIDAD",
    "RECURSOS HUMANOS","JURIDICO","ECOMMERCE PLATAFORMAS",
    "CUSTOMER SERVICE","DIRECCION GENERAL","MANTENIMIENTO","COCINA",
    "SUBDIRECCION DE ADMINISTRACION LOGISTICA",
    "SUBDIRECCION DE OPERACION LOGISTICAS",
]
ESTATUS_CFG = {
    "PENDIENTE": (AMBAR_BG, AMBAR),
    "PAGADO":    (VERDE_BG,  VERDE),
}

def _logo_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "logos", "selectshop_logo.png")

def _ico_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "logos", "selectshop.ico")


class GestorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Pagos — Grupo Marcovich")
        self.geometry("1200x840")
        self.minsize(1000, 700)
        self.configure(fg_color=FONDO)
        try:
            ico = _ico_path()
            if os.path.exists(ico): self.iconbitmap(ico)
        except Exception: pass

        self.db: Database | None = None
        self._pago_editando: int | None = None
        self._modo: str | None = None
        self._outlook_ok = False
        self._datos_ocr: dict = {}

        cfg = config.cargar()
        if not config.configurado():
            self._pantalla_config()
        else:
            self._init_db(cfg["db_path"])
            self._build_ui()
            self._check_outlook()

    def _init_db(self, ruta):
        try:
            self.db = Database(ruta)
            try: self.db.seed_datos_fijos()
            except Exception: pass
            # Refrescar UI con datos de BD
            self.after(100, self._recargar_bancos)
            self.after(150, self._recargar_proveedores)
            self.after(200, self._recargar_listas_combo)
            try: self.after(300, self._load_historial)
            except Exception: pass
        except Exception as e: messagebox.showerror("Error BD", str(e))

    def _pantalla_config(self):
        for w in self.winfo_children(): w.destroy()
        f = ctk.CTkFrame(self, fg_color=FONDO)
        f.pack(expand=True, fill="both", padx=60, pady=60)
        ctk.CTkLabel(f, text="Gestor de Pagos — Configuración inicial",
                     font=ctk.CTkFont("Georgia", 18, "bold"),
                     text_color=AZUL_DARK).pack(pady=(0, 24))

        # Ruta pagos.db
        ctk.CTkLabel(f, text="Ruta a pagos.db (archivo de base de datos):",
                     font=ctk.CTkFont(size=12)).pack(anchor="w")
        row = ctk.CTkFrame(f, fg_color="transparent"); row.pack(fill="x", pady=(4, 6))
        self._ent_db = ctk.CTkEntry(row, width=480, font=ctk.CTkFont(size=12))
        self._ent_db.pack(side="left", padx=(0, 8))
        ctk.CTkButton(row, text="Seleccionar…", fg_color=ACENTO,
                      command=self._pick_db).pack(side="left")

        # Sugerir ruta OneDrive automáticamente
        sugerida = config.sugerir_ruta_db()
        if sugerida:
            self._ent_db.insert(0, sugerida)
            ctk.CTkLabel(f, text="↑ Ruta detectada automáticamente en OneDrive (puedes cambiarla)",
                         font=ctk.CTkFont(size=10), text_color=VERDE).pack(anchor="w", pady=(0, 12))
        else:
            ctk.CTkLabel(f, text="Elige la carpeta de OneDrive donde se guardará el archivo pagos.db",
                         font=ctk.CTkFont(size=10), text_color=MUTED).pack(anchor="w", pady=(0, 12))

        # Nombre de usuario MANUAL
        ctk.CTkLabel(f, text="Tu nombre (como aparecerá en las solicitudes):",
                     font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(8, 0))
        self._ent_nombre = ctk.CTkEntry(f, width=300, font=ctk.CTkFont(size=12),
                                         placeholder_text="Ej: Lilly Arroyo / Denis Tolentino")
        self._ent_nombre.pack(anchor="w", pady=(4, 16))

        ctk.CTkButton(f, text="Guardar y continuar", fg_color=ACENTO, text_color="white",
                      font=ctk.CTkFont(size=13, weight="bold"), height=44,
                      command=self._save_cfg).pack(pady=(8, 0))

    def _pick_db(self):
        ruta = filedialog.asksaveasfilename(title="Elige dónde guardar pagos.db",
            defaultextension=".db", filetypes=[("Base de datos","*.db")])
        if ruta: self._ent_db.delete(0,"end"); self._ent_db.insert(0, ruta)

    def _save_cfg(self):
        ruta = self._ent_db.get().strip()
        if not ruta: messagebox.showwarning("Campo requerido","Selecciona la ruta de la BD."); return
        nombre = self._ent_nombre.get().strip() if hasattr(self, '_ent_nombre') else ""
        cfg = config.cargar()
        cfg["db_path"] = ruta
        if nombre:
            cfg["analista_nombre"] = nombre
        config.guardar(cfg)
        self._init_db(ruta); self._build_ui(); self._check_outlook()

    def _build_ui(self):
        for w in self.winfo_children(): w.destroy()
        root = ctk.CTkFrame(self, fg_color=FONDO, corner_radius=0)
        root.pack(fill="both", expand=True)

        sb = ctk.CTkFrame(root, fg_color=SIDEBAR_BG, width=190, corner_radius=0)
        sb.pack(side="left", fill="y"); sb.pack_propagate(False)

        logo_frame = ctk.CTkFrame(sb, fg_color=SIDEBAR_BG)
        logo_frame.pack(fill="x", padx=12, pady=(16, 4))
        try:
            img = Image.open(_logo_path()).convert("RGBA")
            # Compositar sobre fondo negro
            bg_n = Image.new("RGBA", img.size, (26, 26, 26, 255))
            bg_n.paste(img, mask=img.split()[3])
            img = bg_n.convert("RGB")
            w_i, h_i = img.size
            ratio = min(170/w_i, 50/h_i)
            nw, nh = int(w_i*ratio), int(h_i*ratio)
            img = img.resize((nw, nh), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(nw, nh))
            ctk.CTkLabel(logo_frame, image=ctk_img, text="", fg_color=SIDEBAR_BG).pack(anchor="w")
        except Exception:
            ctk.CTkLabel(logo_frame, text="Grupo Marcovich",
                         font=ctk.CTkFont("Georgia", 16, "bold"), text_color=ACENTO).pack(anchor="w")

        ctk.CTkLabel(sb, text="Pagos corporativos",
                     font=ctk.CTkFont(size=10), text_color="#FFFFFF"
                     ).pack(anchor="w", padx=16, pady=(0, 10))

        self._sb_div(sb)
        self._sb_cat(sb, "PRINCIPAL")
        self._sbtn = {}
        self._sbtn["nueva"]      = self._sb_btn(sb, "+ Nuevo pago",   self._nav_nueva)
        self._sbtn["historial"]  = self._sb_btn(sb, "Historial",      self._nav_historial)
        self._sb_div(sb)
        self._sb_cat(sb, "CALENDARIO")
        self._sbtn["calendario"] = self._sb_btn(sb, "Alertas Outlook", self._nav_calendario)
        self._sb_div(sb)
        self._sb_cat(sb, "AJUSTES")
        self._sbtn["configuracion"] = self._sb_btn(sb, "⚙ Configuración", self._nav_configuracion)
        self._sb_div(sb, bottom=True)

        self.lbl_ol_sb = ctk.CTkLabel(sb, text="● Verificando…",
                                       font=ctk.CTkFont(size=10), text_color="#AAAAAA")
        self.lbl_ol_sb.pack(side="bottom", padx=16, pady=(0, 8), anchor="w")

        cfg = config.cargar()
        user = cfg.get("analista_nombre","") or "Usuario"
        initials = "".join(p[0].upper() for p in user.split()[:2]) or "U"
        user_row = ctk.CTkFrame(sb, fg_color=SIDEBAR_BG)
        user_row.pack(side="bottom", fill="x", padx=10, pady=6)
        av = ctk.CTkFrame(user_row, fg_color=ACENTO, width=30, height=30, corner_radius=15)
        av.pack(side="left", padx=(0,6)); av.pack_propagate(False)
        ctk.CTkLabel(av, text=initials, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="white").place(relx=.5, rely=.5, anchor="center")
        ctk.CTkLabel(user_row, text=user[:20],
                     font=ctk.CTkFont(size=11), text_color="#CCCCCC").pack(side="left")

        self.main = ctk.CTkFrame(root, fg_color=FONDO, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        self.screens = {}
        self._build_nueva()
        self._build_historial()
        self._build_calendario()
        self._build_configuracion()
        self._nav_nueva()

    def _sb_div(self, parent, bottom=False):
        f = ctk.CTkFrame(parent, fg_color="#333333", height=1)
        if bottom: f.pack(side="bottom", fill="x", padx=14)
        else:      f.pack(fill="x", padx=14, pady=8)

    def _sb_cat(self, parent, txt):
        ctk.CTkLabel(parent, text=txt, font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#888888").pack(padx=20, anchor="w", pady=(0, 3))

    def _sb_btn(self, parent, txt, cmd):
        b = ctk.CTkButton(parent, text=txt, anchor="w",
                          fg_color="transparent", hover_color=SB_HOVER,
                          text_color=TEXTO_SB, font=ctk.CTkFont(size=13),
                          height=38, corner_radius=6, command=cmd)
        b.pack(fill="x", padx=10, pady=2); return b

    def _set_nav(self, key):
        for k, b in self._sbtn.items():
            b.configure(fg_color=SB_ACTIVE if k==key else "transparent", text_color="white")
        for k, s in self.screens.items(): s.pack_forget()
        self.screens[key].pack(fill="both", expand=True)

    def _nav_nueva(self):       self._set_nav("nueva")
    def _nav_historial(self):   self._set_nav("historial"); self.after(50, self._load_historial)
    def _nav_calendario(self):  self._set_nav("calendario"); self._load_calendario()
    def _nav_configuracion(self): self._set_nav("configuracion"); self._load_configuracion()

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA: NUEVA SOLICITUD
    # ════════════════════════════════════════════════════════════════════════
    def _build_nueva(self):
        sc = ctk.CTkFrame(self.main, fg_color=FONDO, corner_radius=0)
        self.screens["nueva"] = sc

        hdr = ctk.CTkFrame(sc, fg_color=BLANCO, corner_radius=0, height=58,
                           border_color=BORDE, border_width=1)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Nueva solicitud de pago",
                     font=ctk.CTkFont("Georgia", 15, "bold"),
                     text_color=AZUL_DARK).pack(side="left", padx=20)
        self.btn_eliminar_hdr = ctk.CTkButton(hdr,
            text="Eliminar registro", fg_color=ROJO_BG, text_color=ROJO,
            hover_color="#FED7D7", font=ctk.CTkFont(size=11),
            height=32, width=150, command=self._eliminar_editando)
        self.btn_eliminar_hdr.pack(side="right", padx=(0,8), pady=12)
        self.btn_eliminar_hdr.pack_forget()

        modo_card = ctk.CTkFrame(sc, fg_color=BLANCO, corner_radius=12,
                                  border_color=BORDE, border_width=1)
        modo_card.pack(fill="x", padx=16, pady=(12, 0))

        # ── Selector tipo de documento ─────────────────────────────────────
        tipo_row = ctk.CTkFrame(modo_card, fg_color="#F5F5F5", corner_radius=0)
        tipo_row.pack(fill="x", padx=0, pady=0)
        ctk.CTkLabel(tipo_row, text="Tipo de documento:",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=AZUL_DARK).pack(side="left", padx=14, pady=8)
        self._tipo_doc = ctk.StringVar(value="recibo")
        ctk.CTkRadioButton(tipo_row, text="Recibo de servicio",
                           variable=self._tipo_doc, value="recibo",
                           font=ctk.CTkFont(size=11), fg_color=ACENTO,
                           text_color=TEXTO).pack(side="left", padx=10, pady=8)
        ctk.CTkRadioButton(tipo_row, text="Factura CFDI",
                           variable=self._tipo_doc, value="factura",
                           font=ctk.CTkFont(size=11), fg_color="#555555",
                           text_color=TEXTO).pack(side="left", padx=10, pady=8)
        ctk.CTkFrame(modo_card, fg_color=BORDE, height=1).pack(fill="x")

        mc = ctk.CTkFrame(modo_card, fg_color="transparent")
        mc.pack(padx=16, pady=14, anchor="w")

        ctk.CTkLabel(mc, text="¿Cómo vas a llenar la solicitud?",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXTO).pack(anchor="w", pady=(0, 10))
        btns = ctk.CTkFrame(mc, fg_color="transparent"); btns.pack(anchor="w")

        self.btn_modo_pdf = ctk.CTkButton(btns,
            text="Subir recibo del proveedor (PDF/imagen)",
            fg_color=ACENTO, hover_color=ACENTO_HOV,
            text_color="white", font=ctk.CTkFont(size=12, weight="bold"),
            height=40, width=300, command=self._modo_ocr)
        self.btn_modo_pdf.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(btns, text="o", font=ctk.CTkFont(size=12),
                     text_color=MUTED).pack(side="left", padx=(0, 12))

        self.btn_modo_manual = ctk.CTkButton(btns,
            text="Llenado manual", fg_color=BORDE, text_color=TEXTO,
            hover_color="#D0D0D0", font=ctk.CTkFont(size=12),
            height=40, width=150, command=self._modo_manual)
        self.btn_modo_manual.pack(side="left")

        self.lbl_modo = ctk.CTkLabel(mc,
            text="← Elige un modo para habilitar el formulario",
            font=ctk.CTkFont(size=11), text_color=AMBAR)
        self.lbl_modo.pack(anchor="w", pady=(8, 0))

        self.form_scroll = ctk.CTkScrollableFrame(sc, fg_color=FONDO, border_width=0)
        self.form_scroll.pack(fill="both", expand=True, padx=16, pady=8)

        self.overlay = ctk.CTkFrame(self.form_scroll, fg_color="#F0F0F0", corner_radius=8,
                                     border_color=BORDE, border_width=1)
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        ctk.CTkLabel(self.overlay, text="Selecciona cómo vas a llenar la solicitud",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=AZUL_DARK
                     ).place(relx=.5, rely=.20, anchor="center")
        ctk.CTkLabel(self.overlay,
                     text="Usa los botones de arriba: 'Subir recibo del proveedor' o 'Llenado manual'",
                     font=ctk.CTkFont(size=12), text_color=MUTED
                     ).place(relx=.5, rely=.27, anchor="center")

        self._build_form(self.form_scroll)
        self.after(100, lambda: self._set_form_state("disabled"))

    def _modo_ocr(self):
        ruta = filedialog.askopenfilename(
            title="Selecciona el recibo del proveedor",
            filetypes=[("PDF e imágenes","*.pdf *.png *.jpg *.jpeg *.tif *.tiff"),("Todos","*.*")])
        if not ruta: return
        # Limpiar SIEMPRE antes de un nuevo escaneo
        self._limpiar_solo_campos()
        self._unlock_form("ocr")
        self.lbl_modo.configure(text="Leyendo recibo con OCR, espera un momento…", text_color=AMBAR)
        groq_key = config.cargar().get("groq_api_key","")
        def _scan():
            tipo = self._tipo_doc.get() if hasattr(self, '_tipo_doc') else 'recibo'
            res = escanear_recibo(ruta, groq_api_key=groq_key, tipo_doc=tipo)
            self.after(0, lambda: self._apply_ocr(res))
        threading.Thread(target=_scan, daemon=True).start()

    def _modo_manual(self):
        # Limpiar siempre al elegir modo manual
        self._limpiar_solo_campos()
        self._unlock_form("manual")
        self.lbl_modo.configure(text="Modo manual — llena los campos del formulario", text_color=VERDE)

    def _unlock_form(self, modo):
        # Si ya había datos de un modo anterior, limpiarlos primero
        if self._modo is not None and self._modo != modo:
            self._limpiar_solo_campos()
        self._modo = modo
        self.overlay.place_forget()
        self.btn_modo_pdf.configure(
            fg_color=ACENTO_HOV if modo=="ocr" else BORDE,
            text_color="white" if modo=="ocr" else TEXTO)
        self.btn_modo_manual.configure(
            fg_color=ACENTO if modo=="manual" else BORDE,
            text_color="white" if modo=="manual" else TEXTO)
        self._set_form_state("normal")

    def _limpiar_solo_campos(self):
        """Limpia solo los campos de datos (no firmantes, no mes/año)."""
        try: self.ent_banco.set("")
        except Exception: pass
        for w in [self.ent_motivo, self.ent_cfdi, self.ent_nc, self.ent_monto,
                  self.ent_clabe, self.ent_cuenta, self.ent_obs]:
            try: w.delete(0, "end")
            except Exception:
                try: w.set("")
                except Exception: pass
        for cb in [self.cb_empresa, self.cb_sucursal, self.cb_proveedor]:
            try: cb.set("")
            except Exception: pass

    def _apply_ocr(self, datos: dict):
        self._datos_ocr = datos
        # Limpiar TODOS los campos de datos antes de aplicar (NUNCA los firmantes)
        # Banco es ComboBox → .set(), entries → .delete()
        try: self.ent_banco.set("")
        except Exception: pass
        for w in [self.ent_motivo, self.ent_cfdi, self.ent_nc, self.ent_monto,
                  self.ent_clabe, self.ent_cuenta, self.ent_obs]:
            try:
                w.delete(0, "end")
            except Exception:
                try: w.set("")
                except Exception: pass
        for cb in [self.cb_empresa, self.cb_sucursal, self.cb_proveedor]:
            try: cb.set("")
            except Exception: pass
        # NUNCA tocar ent_analista ni ent_gerente

        # Empresa
        if datos.get("empresa_cliente"):
            ec = datos["empresa_cliente"].upper().strip()
            matched = EMPRESAS_ALIAS.get(ec, "")
            if not matched:
                for alias, empresa in EMPRESAS_ALIAS.items():
                    if alias in ec or ec[:10] in alias:
                        matched = empresa; break
            if not matched:
                for emp in EMPRESAS:
                    if ec[:8] in emp.upper() or emp.upper()[:8] in ec:
                        matched = emp; break
            if matched: self.cb_empresa.set(matched)

        # Sucursal
        if datos.get("sucursal"):
            suc_ocr = datos["sucursal"].upper()
            matched_suc = ""
            for suc in SUCURSALES:
                if suc_ocr[:8] in suc.upper() or suc.upper()[:8] in suc_ocr:
                    matched_suc = suc; break
            if not matched_suc and "NEBRASKA" in suc_ocr: matched_suc = "NEBRASKA"
            if matched_suc: self.cb_sucursal.set(matched_suc)

        # Proveedor
        if datos.get("proveedor"):
            prov_upper = datos["proveedor"].upper()
            for p in self._nombres_proveedores():
                if prov_upper[:12] in p.upper() or p.upper()[:12] in prov_upper:
                    self.cb_proveedor.set(p)
                    self._autocompletar_proveedor(p)
                    break
            else:
                self.cb_proveedor.set(datos["proveedor"])
            # OCR sobreescribe banco/clabe del autocomplete si los tiene
            if datos.get("banco"):
                self.ent_banco.set(datos["banco"])
            if datos.get("clabe"):
                self.ent_clabe.delete(0,"end"); self.ent_clabe.insert(0, datos["clabe"])

        if datos.get("motivo_pago"): self.ent_motivo.insert(0, datos["motivo_pago"])

        # No. Folio CFDI
        if datos.get("factura_no"):
            self.ent_cfdi.delete(0,"end"); self.ent_cfdi.insert(0, datos["factura_no"])

        # Importe
        if datos.get("monto"):
            self.ent_monto.delete(0,"end"); self.ent_monto.insert(0, datos["monto"]); self._upd_letra()

        # Banco — si no vino del OCR, intentar inferir desde prefijo CLABE
        clabe_val = datos.get("clabe","")
        banco_val = datos.get("banco","")
        if not banco_val and clabe_val and self.db:
            banco_val = self.db.get_banco_por_prefijo(clabe_val.replace("-","").replace(" ",""))
        if banco_val and not self.ent_banco.get():
            if banco_val: self.ent_banco.set(banco_val)

        # CLABE
        if clabe_val and not self.ent_clabe.get():
            self.ent_clabe.insert(0, clabe_val)

        # No. cuenta del servicio
        if datos.get("no_cuenta"):
            self.ent_cuenta.delete(0,"end"); self.ent_cuenta.insert(0, datos["no_cuenta"])

        # Observaciones
        # CLABE: si OCR la dejó vacía, intentar desde BD por proveedor
        clabe_ocr = datos.get("clabe","").strip()
        if not clabe_ocr and datos.get("proveedor"):
            try:
                prov_bd = self.db.buscar_proveedor_por_nombre(datos["proveedor"])
                if prov_bd and prov_bd.get("clabe"):
                    self.ent_clabe.delete(0,"end")
                    self.ent_clabe.insert(0, prov_bd["clabe"])
            except Exception: pass

        # Observaciones: aplicar siempre desde OCR (tiene precedencia)
        if datos.get("observaciones"):
            self.ent_obs.delete(0,"end")
            self.ent_obs.insert(0, datos["observaciones"])

        # Mes + Año
        # Mes presupuesto y mes pago (Groq puede devolverlos directamente)
        mes_pres = (datos.get("mes_presupuesto") or datos.get("mes_factura") or "").capitalize()
        mes_pago_v = (datos.get("mes_pago") or datos.get("mes_factura") or "").capitalize()
        if mes_pres and mes_pres in MESES:
            try: self.cb_mes_pres.set(mes_pres)
            except Exception: pass
        if mes_pago_v and mes_pago_v in MESES:
            try: self.cb_mes_pago.set(mes_pago_v)
            except Exception: pass
        elif datos.get("mes_factura"):
            mes = datos["mes_factura"].capitalize()
            if mes in MESES:
                try: self.cb_mes_pres.set(mes)
                except Exception: pass
                try: self.cb_mes_pago.set(mes)
                except Exception: pass
        if datos.get("anio_factura"):
            try: self.ent_anio.delete(0,"end"); self.ent_anio.insert(0, datos["anio_factura"])
            except Exception: pass

        # Contar campos llenados (SIN firmantes)
        campos_leidos = [k for k in ["proveedor","empresa_cliente","monto","factura_no",
                                      "mes_factura","no_cuenta","observaciones","banco","clabe",
                                      "sucursal","motivo_pago"] if datos.get(k)]
        # Agregar banco si se infirió desde CLABE
        if banco_val and "banco" not in campos_leidos:
            campos_leidos.append("banco_inferido")
        n = len(campos_leidos)
        err_msg = datos.get("error","")
        if n == 0:
            if err_msg:
                self.lbl_modo.configure(text=f"Error OCR: {err_msg[:100]}", text_color=ROJO)
            else:
                from ocr_scanner import diagnostico_ocr
                self.lbl_modo.configure(text=f"Sin campos leídos. {diagnostico_ocr()}", text_color=ROJO)
        else:
            groq_usado = "con Groq IA" if not err_msg else "con Windows OCR"
            self.lbl_modo.configure(
                text=f"✓ {n} campo(s) leídos {groq_usado}.",
                text_color=VERDE)

    def _build_form(self, parent):
        self._form_widgets = []
        self._sec(parent, "Datos de la empresa")
        r1 = self._row(parent)
        self.cb_empresa  = self._lbl_combo(r1, "Empresa:",    EMPRESAS,   230)
        self.cb_sucursal = self._lbl_combo(r1, "Sucursal:",   SUCURSALES, 200)
        r2 = self._row(parent)
        self.cb_cc  = self._lbl_combo(r2, "Centro de costos:", CENTROS, 220)
        self.cb_dir = self._lbl_combo(r2, "Dirección:",        [], 180)

        self._sec(parent, "Beneficiario / Proveedor")
        r3 = self._row(parent)
        self.cb_proveedor = self._lbl_combo(r3, "Proveedor:", [], 260)
        self.cb_proveedor.configure(command=lambda v: self._autocompletar_proveedor(v))
        self.ent_motivo = self._lbl_entry(r3, "Motivo de pago:", 280)

        self._sec(parent, "Datos de CFDI")
        r4 = self._row(parent)
        self.ent_cfdi = self._lbl_entry(r4, "No. Folio(s) CFDI / Folio Fiscal:", 230)
        self.ent_nc   = self._lbl_entry(r4, "Nota(s) de crédito:", 120)

        self._sec(parent, "Datos de pago")
        r5 = self._row(parent)
        self.ent_monto = self._lbl_entry(r5, "Importe total (MXN):", 120)
        self.ent_monto.bind("<KeyRelease>", lambda e: self._upd_letra())
        self.lbl_letra = ctk.CTkLabel(r5, text="", font=ctk.CTkFont(size=10),
                                       text_color=MUTED, wraplength=260)
        self.lbl_letra.pack(side="left", padx=(4,0), pady=4)
        r6 = self._row(parent)
        # Banco: ComboBox cargado desde BD
        self.ent_banco = self._lbl_combo(r6, "Banco:", [], 160)
        self.ent_banco.configure(command=lambda v: self._on_banco_seleccionado(v))
        self.after(200, self._recargar_bancos)
        self.ent_clabe  = self._lbl_entry(r6, "CLABE:",    220)
        self.ent_cuenta = self._lbl_entry(r6, "No. cuenta:", 160)
        r7 = self._row(parent)
        self.ent_obs = self._lbl_entry(r7, "Observaciones / Referencia:", 400)

        self._sec(parent, "Exclusivo — Departamento de Finanzas")
        r8 = self._row(parent)
        self.cb_mes_pres = self._lbl_combo(r8, "Mes presupuesto:", MESES, 140)
        self.cb_mes_pago = self._lbl_combo(r8, "Mes pago:",        MESES, 140)
        self.ent_anio    = self._lbl_entry(r8, "Año:",              70)
        self.cb_mes_pres.set(MESES[date.today().month-1])
        self.cb_mes_pago.set(MESES[date.today().month-1])
        self.ent_anio.insert(0, str(date.today().year))

        self._sec(parent, "Nombres de Firmantes")
        r9a = self._row(parent)
        self.ent_analista  = self._lbl_entry(r9a, "Solicitante / Analista:", 220)
        self.ent_gerente   = self._lbl_entry(r9a, "Gerente de Sistemas:", 220)
        r9b = self._row(parent)
        self.ent_visto_bno = self._lbl_entry(r9b, "Vo. Bo. (Finanzas):", 220)
        self.ent_depto_fin = self._lbl_entry(r9b, "Depto. Finanzas Presupuesto:", 220)
        r9c = self._row(parent)
        self.ent_dir_fin   = self._lbl_entry(r9c, "Dirección Financiera:", 220)
        self.ent_dir_gral  = self._lbl_entry(r9c, "Dirección General:", 220)
        # Cargar defaults de config si están configurados
        _cfg_f = config.cargar()
        for ent, key in [
            (self.ent_analista, "firmante_analista"),
            (self.ent_gerente,  "firmante_gerente"),
            (self.ent_visto_bno,"firmante_visto_bno"),
            (self.ent_depto_fin,"firmante_depto_fin"),
            (self.ent_dir_fin,  "firmante_dir_fin"),
            (self.ent_dir_gral, "firmante_dir_gral"),
        ]:
            val = _cfg_f.get(key,"")
            if val: ent.insert(0, val)
        # Groq API Key se configura en la pantalla de Configuración
        self.ent_groq = None

        self.lbl_est = ctk.CTkLabel(parent, text="")

        act_card = ctk.CTkFrame(parent, fg_color=BLANCO, corner_radius=10,
                                 border_color=BORDE, border_width=1)
        act_card.pack(fill="x", pady=(12,8))
        ac = ctk.CTkFrame(act_card, fg_color="transparent")
        ac.pack(padx=16, pady=14, anchor="w")

        ctk.CTkButton(ac, text="Vista previa (PDF)",
                      fg_color="#555555", hover_color="#333333",
                      text_color="white", font=ctk.CTkFont(size=12),
                      height=40, width=170, command=self._vista_previa
                      ).pack(side="left", padx=(0,8))

        ctk.CTkButton(ac, text="Generar Solicitud de Pago (PDF)",
                      fg_color=ACENTO, hover_color=ACENTO_HOV,
                      text_color="white", font=ctk.CTkFont(size=12, weight="bold"),
                      height=40, width=260, command=self._gen_pdf
                      ).pack(side="left", padx=(0,10))

        ctk.CTkButton(ac, text="Nueva solicitud",
                      fg_color=BORDE, text_color=TEXTO, hover_color="#D0D0D0",
                      font=ctk.CTkFont(size=12), height=40, width=140,
                      command=self._limpiar
                      ).pack(side="left")

        self.lbl_save = ctk.CTkLabel(ac, text="", font=ctk.CTkFont(size=11), text_color=VERDE)
        self.lbl_save.pack(side="left", padx=14)

        self.after(300, self._recargar_proveedores)
        self.after(400, self._recargar_listas_combo)

    def _sec(self, parent, titulo):
        f = ctk.CTkFrame(parent, fg_color=AZUL_DARK, corner_radius=6)
        f.pack(fill="x", pady=(10,2))
        ctk.CTkLabel(f, text=titulo.upper(), font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").pack(anchor="w", padx=12, pady=6)
        self._form_widgets.append(f)

    def _row(self, parent):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", pady=2); self._form_widgets.append(f); return f

    def _lbl_combo(self, parent, lbl, valores, width):
        ctk.CTkLabel(parent, text=lbl, font=ctk.CTkFont(size=11), text_color=TEXTO
                     ).pack(side="left", padx=(0,4), pady=4)
        cb = ctk.CTkComboBox(parent, values=valores, width=width, font=ctk.CTkFont(size=11))
        cb.set(""); cb.pack(side="left", padx=(0,14), pady=4)
        self._form_widgets.append(cb); return cb

    def _lbl_entry(self, parent, lbl, width):
        ctk.CTkLabel(parent, text=lbl, font=ctk.CTkFont(size=11), text_color=TEXTO
                     ).pack(side="left", padx=(0,4), pady=4)
        e = ctk.CTkEntry(parent, width=width, font=ctk.CTkFont(size=11))
        e.pack(side="left", padx=(0,14), pady=4)
        self._form_widgets.append(e); return e

    def _set_form_state(self, state):
        for w in self._form_widgets:
            try: w.configure(state=state)
            except Exception: pass

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA: HISTORIAL
    # ════════════════════════════════════════════════════════════════════════
    def _build_historial(self):
        sc = ctk.CTkFrame(self.main, fg_color=FONDO, corner_radius=0)
        self.screens["historial"] = sc

        hdr = ctk.CTkFrame(sc, fg_color=BLANCO, height=58, corner_radius=0,
                           border_color=BORDE, border_width=1)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Historial de pagos",
                     font=ctk.CTkFont("Georgia",15,"bold"),
                     text_color=AZUL_DARK).pack(side="left", padx=20)

        ctrl = ctk.CTkFrame(sc, fg_color=BLANCO, corner_radius=12,
                             border_color=BORDE, border_width=1)
        ctrl.pack(fill="x", padx=16, pady=10)
        cr = ctk.CTkFrame(ctrl, fg_color="transparent")
        cr.pack(padx=16, pady=12, anchor="w")

        ctk.CTkLabel(cr, text="Mes:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,4))
        self.cb_hm = ctk.CTkComboBox(cr, values=MESES, width=130, font=ctk.CTkFont(size=12))
        self.cb_hm.set(MESES[date.today().month-1]); self.cb_hm.pack(side="left", padx=(0,12))
        ctk.CTkLabel(cr, text="Año:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,4))
        self.ent_ha = ctk.CTkEntry(cr, width=70, font=ctk.CTkFont(size=12))
        self.ent_ha.insert(0, str(date.today().year)); self.ent_ha.pack(side="left", padx=(0,12))
        ctk.CTkButton(cr, text="Consultar", fg_color=AZUL_DARK, font=ctk.CTkFont(size=12),
                      height=34, width=100, command=self._load_historial).pack(side="left", padx=(0,12))
        ctk.CTkLabel(cr, text="Buscar:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(12,4))
        self.ent_h_buscar = ctk.CTkEntry(cr, width=200, font=ctk.CTkFont(size=12),
                                          placeholder_text="Proveedor, empresa, motivo…")
        self.ent_h_buscar.pack(side="left", padx=(0,8))
        self.ent_h_buscar.bind("<Return>", lambda e: self._buscar_historial())
        ctk.CTkButton(cr, text="Buscar", fg_color=ACENTO, font=ctk.CTkFont(size=12),
                      height=34, width=80, command=self._buscar_historial).pack(side="left", padx=(0,12))
        ctk.CTkButton(cr, text="Limpiar", fg_color=BORDE, text_color=TEXTO,
                      font=ctk.CTkFont(size=12), height=34, width=70,
                      command=self._limpiar_busqueda).pack(side="left", padx=(0,12))
        ctk.CTkButton(cr, text="Exportar Excel", fg_color="#444444", text_color="white",
                      font=ctk.CTkFont(size=12), height=34, width=130,
                      command=self._xls_hist).pack(side="left")

        met = ctk.CTkFrame(sc, fg_color="transparent"); met.pack(fill="x", padx=16, pady=(0,8))
        self.m_pag = self._met(met, "Total pagado", "$0")
        self.m_pen = self._met(met, "Total pendiente", "$0")
        self.m_n   = self._met(met, "Registros", "0")

        self.tbl = ctk.CTkScrollableFrame(sc, fg_color=BLANCO, corner_radius=12,
                                           border_color=BORDE, border_width=1)
        self.tbl.pack(fill="both", expand=True, padx=16, pady=(0,12))
        self._tbl_hdr()

    def _met(self, parent, titulo, valor):
        f = ctk.CTkFrame(parent, fg_color=BLANCO, corner_radius=8,
                         border_color=BORDE, border_width=1)
        f.pack(side="left", padx=(0,10), pady=4, ipadx=12, ipady=6)
        ctk.CTkLabel(f, text=titulo, font=ctk.CTkFont(size=10), text_color=MUTED).pack()
        lbl = ctk.CTkLabel(f, text=valor, font=ctk.CTkFont(size=14, weight="bold"),
                           text_color=AZUL_DARK)
        lbl.pack(); return lbl

    def _tbl_hdr(self):
        cols = ["ID","Proveedor","Empresa","Motivo de pago","Monto","Estatus","Fecha","Acciones"]
        ws   = [40,  160,        140,       200,             90,     90,       90,     170]
        h = ctk.CTkFrame(self.tbl, fg_color=AZUL_DARK, corner_radius=0); h.pack(fill="x")
        for c, w in zip(cols, ws):
            ctk.CTkLabel(h, text=c, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="white", width=w, anchor="w").pack(side="left", padx=6, pady=8)

    def _limpiar_busqueda(self):
        self.ent_h_buscar.delete(0, "end"); self._load_historial()

    def _buscar_historial(self):
        if not self.db: return
        query = self.ent_h_buscar.get().strip()
        if not query: self._load_historial(); return
        todos = self.db.buscar_pagos(query)
        self._render_historial(todos, modo_busqueda=True)

    def _load_historial(self):
        if not self.db: return
        try:    mes = MESES.index(self.cb_hm.get())+1
        except: mes = date.today().month
        try:    anio = int(self.ent_ha.get() or date.today().year)
        except: anio = date.today().year
        estado = self.db.estado_cuenta_mes(mes, anio)
        self._render_historial(estado["todos"])
        self.m_pag.configure(text=f"${estado['total_pagado']:,.0f}")
        self.m_pen.configure(text=f"${estado['total_pendiente']:,.0f}")
        self.m_n.configure(text=str(len(estado['todos'])))

    def _render_historial(self, pagos: list, modo_busqueda=False):
        for w in list(self.tbl.winfo_children())[1:]: w.destroy()
        if modo_busqueda:
            self.m_pag.configure(text="—"); self.m_pen.configure(text="—")
            self.m_n.configure(text=str(len(pagos)))
        if not pagos:
            msg = "Sin resultados para la búsqueda." if modo_busqueda else "Sin registros para este período."
            ctk.CTkLabel(self.tbl, text=msg, font=ctk.CTkFont(size=12), text_color=MUTED).pack(pady=30)
            return
        for p in pagos:
            est = (p.get("estatus") or "PENDIENTE").upper()
            bg, tc = ESTATUS_CFG.get(est, (FONDO, TEXTO))
            rf = ctk.CTkFrame(self.tbl, fg_color=bg, corner_radius=0); rf.pack(fill="x", pady=1)
            for v, w in zip([str(p.get("id","")),
                             (p.get("proveedor_nombre","") or "")[:20],
                             (p.get("empresa","") or "")[:18],
                             (p.get("motivo_pago","") or "")[:26],
                             f"${(p.get('monto_total') or 0):,.0f}",
                             est, str(p.get("fecha_proceso","") or "")[:10]],
                            [40,160,140,200,90,90,90]):
                ctk.CTkLabel(rf, text=v, font=ctk.CTkFont(size=11), text_color=tc,
                             width=w, anchor="w").pack(side="left", padx=6, pady=5)
            pid = p["id"]
            ac = ctk.CTkFrame(rf, fg_color="transparent", width=170); ac.pack(side="left", padx=4)
            next_est = "PAGADO" if est=="PENDIENTE" else "PENDIENTE"
            btn_lbl  = "→ Pagado" if est=="PENDIENTE" else "→ Pend."
            ctk.CTkButton(ac, text=btn_lbl, width=74, height=26,
                          fg_color=VERDE_BG if est=="PENDIENTE" else AMBAR_BG,
                          text_color=VERDE if est=="PENDIENTE" else AMBAR,
                          font=ctk.CTkFont(size=9, weight="bold"),
                          command=lambda i=pid, e=next_est: self._cambiar_estatus(i, e)
                          ).pack(side="left", padx=(0,3))
            ctk.CTkButton(ac, text="Editar", width=48, height=26, fg_color=ACENTO,
                          text_color="white", font=ctk.CTkFont(size=10),
                          command=lambda i=pid: self._editar(i)).pack(side="left", padx=(0,3))
            ctk.CTkButton(ac, text="PDF", width=36, height=26, fg_color=AZUL_DARK,
                          text_color="white", font=ctk.CTkFont(size=10),
                          command=lambda i=pid: self._pdf_hist(i)).pack(side="left", padx=(0,3))
            ctk.CTkButton(ac, text="✕", width=24, height=26, fg_color=ROJO,
                          text_color="white", font=ctk.CTkFont(size=10),
                          command=lambda i=pid: self._del_pago(i)).pack(side="left")

    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA: CALENDARIO
    # ════════════════════════════════════════════════════════════════════════
    def _build_calendario(self):
        sc = ctk.CTkFrame(self.main, fg_color=FONDO, corner_radius=0)
        self.screens["calendario"] = sc

        hdr = ctk.CTkFrame(sc, fg_color=BLANCO, height=58, corner_radius=0,
                           border_color=BORDE, border_width=1)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Calendario — Alertas de Outlook",
                     font=ctk.CTkFont("Georgia",15,"bold"),
                     text_color=AZUL_DARK).pack(side="left", padx=20)

        ol_card = ctk.CTkFrame(sc, fg_color=BLANCO, corner_radius=12,
                                border_color=BORDE, border_width=1)
        ol_card.pack(fill="x", padx=16, pady=10)
        olr = ctk.CTkFrame(ol_card, fg_color="transparent")
        olr.pack(padx=16, pady=14, fill="x")
        ctk.CTkLabel(olr, text="Vinculación con Microsoft Outlook:",
                     font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXTO).pack(side="left", padx=(0,12))
        self.lbl_ol_cal = ctk.CTkLabel(olr, text="Verificando…",
                                        font=ctk.CTkFont(size=12), text_color=AMBAR)
        self.lbl_ol_cal.pack(side="left", padx=(0,16))
        ctk.CTkButton(olr, text="Verificar ahora", fg_color=BORDE, text_color=TEXTO,
                      hover_color="#D0D0D0", font=ctk.CTkFont(size=11), height=32, width=130,
                      command=self._check_outlook).pack(side="left", padx=(0,10))
        ctk.CTkButton(olr, text="Purgar citas de prueba",
                      fg_color="#8B0000", text_color="white",
                      font=ctk.CTkFont(size=11), height=32, width=180,
                      command=self._purgar_citas_outlook).pack(side="left", padx=(0,10))
        ctk.CTkButton(olr, text="Probar conexión Outlook",
                      fg_color="#555555", text_color="white",
                      font=ctk.CTkFont(size=11), height=32, width=180,
                      command=self._probar_outlook_conexion).pack(side="left", padx=(0,10))
        ctk.CTkButton(olr, text="Crear recordatorios en Outlook",
                      fg_color=ACENTO, text_color="white",
                      font=ctk.CTkFont(size=11, weight="bold"), height=32, width=230,
                      command=self._make_reminders).pack(side="left")

        cr2 = ctk.CTkFrame(sc, fg_color="transparent"); cr2.pack(fill="x", padx=16, pady=(0,8))
        ctk.CTkButton(cr2, text="Actualizar lista", fg_color=AZUL_DARK, text_color="white",
                      font=ctk.CTkFont(size=12), height=34, width=140,
                      command=self._load_calendario).pack(side="left")
        ctk.CTkLabel(cr2, text="Servicios con fecha fija de vencimiento y próximos a vencer",
                     font=ctk.CTkFont(size=11), text_color=MUTED).pack(side="left", padx=14)

        self.cal_list = ctk.CTkScrollableFrame(sc, fg_color=FONDO, border_width=0)
        self.cal_list.pack(fill="both", expand=True, padx=16, pady=(0,12))

    def _load_calendario(self):
        if not self.db: return
        proximos = self.db.servicios_proximos(config.cargar().get("dias_alerta", 30))
        for w in self.cal_list.winfo_children(): w.destroy()
        if not proximos:
            ctk.CTkLabel(self.cal_list, text="Sin pagos próximos a vencer.",
                         font=ctk.CTkFont(size=13), text_color=MUTED).pack(pady=40); return
        for s in sorted(proximos, key=lambda x: x["dias_para_vencer"]):
            dias = s["dias_para_vencer"]
            bg = ROJO_BG if dias <= 3 else AMBAR_BG if dias <= 10 else VERDE_BG
            tc = ROJO    if dias <= 3 else AMBAR     if dias <= 10 else VERDE
            c = ctk.CTkFrame(self.cal_list, fg_color=bg, corner_radius=10,
                              border_color=BORDE, border_width=1)
            c.pack(fill="x", pady=4, padx=4)
            t = ctk.CTkFrame(c, fg_color="transparent"); t.pack(fill="x", padx=14, pady=(8,2))
            ctk.CTkLabel(t, text=s.get("proveedor_nombre",""),
                         font=ctk.CTkFont(size=13, weight="bold"), text_color=tc).pack(side="left")
            fecha_str = s['fecha_limite'].strftime('%d/%m/%Y') if hasattr(s['fecha_limite'],'strftime') else str(s['fecha_limite'])
            ctk.CTkLabel(t, text=f"Vence el {fecha_str}  —  {dias} día(s)",
                         font=ctk.CTkFont(size=11), text_color=tc).pack(side="right")
            b = ctk.CTkFrame(c, fg_color="transparent"); b.pack(fill="x", padx=14, pady=(0,10))
            monto = (s.get("monto_base") or 0) + (s.get("iva") or 0)
            ctk.CTkLabel(b,
                text=f"{(s.get('descripcion',''))[:40]}   •   ${monto:,.0f} MXN   •   {s.get('empresa','')}",
                font=ctk.CTkFont(size=11), text_color=MUTED).pack(side="left")
            # Botón generar pago desde el calendario
            ctk.CTkButton(b, text="+ Generar pago",
                          fg_color=ACENTO, hover_color=ACENTO_HOV,
                          text_color="white", font=ctk.CTkFont(size=10, weight="bold"),
                          height=28, width=120,
                          command=lambda srv=s: self._generar_pago_desde_servicio(srv)
                          ).pack(side="right")

    def _generar_pago_desde_servicio(self, srv: dict):
        """Desde el calendario, abre nueva solicitud prellenada con datos del servicio."""
        self._limpiar()
        self._nav_nueva()
        self._unlock_form("manual")
        prov_nom = srv.get("proveedor_nombre","")
        self.lbl_modo.configure(
            text=f"Prellenado desde calendario: {prov_nom}", text_color=ACENTO)
        # Empresa
        emp = srv.get("empresa","")
        if emp in EMPRESAS:
            self.cb_empresa.set(emp)
        # Sucursal
        suc = srv.get("sucursal","")
        if suc:
            try: self.cb_sucursal.set(suc)
            except Exception: pass
        # Centro de costos
        cc = srv.get("centro_costos","")
        if cc:
            try: self.cb_cc.set(cc)
            except Exception: pass
        # Proveedor + autocompletar banco/CLABE/cuenta
        if prov_nom:
            self.cb_proveedor.set(prov_nom)
            self._autocompletar_proveedor(prov_nom)
        # No. cuenta del servicio
        no_c = srv.get("no_cuenta_servicio","") or srv.get("no_cuenta","")
        if no_c:
            self.ent_cuenta.delete(0,"end"); self.ent_cuenta.insert(0, no_c)
        mes_actual = MESES[date.today().month-1]
        anio_actual = str(date.today().year)
        motivo = f"SERV CTA {no_c} {mes_actual.upper()} {anio_actual}" if no_c else srv.get("descripcion","")
        self.ent_motivo.delete(0,"end"); self.ent_motivo.insert(0, motivo)
        self.cb_mes_pres.set(mes_actual); self.cb_mes_pago.set(mes_actual)
        self.ent_anio.delete(0,"end"); self.ent_anio.insert(0, anio_actual)
        monto = (srv.get("monto_base") or 0) + (srv.get("iva") or 0)
        if monto:
            self.ent_monto.delete(0,"end")
            self.ent_monto.insert(0, f"{monto:.2f}")
            self._upd_letra()

    def _vista_previa(self):
        """
        Vista previa WYSIWYG: muestra los datos en un layout visual que replica
        el formato de Solicitud de Pago. Los campos son editables directamente
        desde la ventana de preview. Botón "Generar PDF" al confirmar.
        No genera ningún archivo hasta que el usuario confirme.
        """
        if not self._modo:
            messagebox.showwarning("Elige un modo",
                "Selecciona 'Subir recibo' o 'Llenado manual' primero."); return
        datos = self._datos_form()
        if not datos["proveedor_nombre"]:
            messagebox.showwarning("Campo requerido","Selecciona un proveedor."); return

        win = ctk.CTkToplevel(self)
        win.title("Vista previa — Solicitud de Pago General")
        win.geometry("860x720")
        win.grab_set()

        # Header de la ventana
        hdr = ctk.CTkFrame(win, fg_color=AZUL_DARK, height=50)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Vista previa — Solicitud de Pago General",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").pack(side="left", padx=16, pady=12)

        # Área scrollable con el layout del formato
        scroll = ctk.CTkScrollableFrame(win, fg_color="#EEEEEE")
        scroll.pack(fill="both", expand=True)

        # Tarjeta blanca que replica el formato
        card = ctk.CTkFrame(scroll, fg_color=BLANCO, corner_radius=0)
        card.pack(fill="x", padx=20, pady=16)

        def hdr_sec(parent, txt):
            f = ctk.CTkFrame(parent, fg_color="#1A1A1A", corner_radius=0)
            f.pack(fill="x", pady=(8,0))
            ctk.CTkLabel(f, text=txt.upper(), font=ctk.CTkFont(size=9, weight="bold"),
                         text_color="white").pack(anchor="w", padx=10, pady=4)

        # Dict para capturar los entries editables de la preview
        preview_entries = {}
        def campo(parent, key, lbl, val, width=420):
            rf = ctk.CTkFrame(parent, fg_color="transparent")
            rf.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(rf, text=lbl+":", font=ctk.CTkFont(size=9, weight="bold"),
                         text_color="#555555", width=140, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(rf, width=width, font=ctk.CTkFont(size=10),
                               fg_color="#F8F8F8", border_color=BORDE, border_width=1)
            ent.pack(side="left", padx=4)
            ent.insert(0, str(val) if val else "")
            preview_entries[key] = ent

        # Título
        titulo_f = ctk.CTkFrame(card, fg_color="transparent")
        titulo_f.pack(fill="x", padx=10, pady=(12,4))
        empresa_txt = datos.get("empresa","") or "— Empresa —"
        ctk.CTkLabel(titulo_f, text="SOLICITUD DE PAGO GENERAL",
                     font=ctk.CTkFont(size=14, weight="bold"), text_color=AZUL_DARK).pack(anchor="center")
        ctk.CTkLabel(titulo_f, text=empresa_txt,
                     font=ctk.CTkFont(size=11), text_color="#666666").pack(anchor="center")

        # Fila sucursal + fecha
        f0 = ctk.CTkFrame(card, fg_color="transparent"); f0.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f0, text="SUCURSAL:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(side="left")
        ctk.CTkLabel(f0, text=datos.get("sucursal","—"),
                     font=ctk.CTkFont(size=10, weight="bold"), text_color=AZUL_DARK).pack(side="left", padx=8)
        ctk.CTkLabel(f0, text=f"  Fecha: {datos.get('fecha_proceso','—')}",
                     font=ctk.CTkFont(size=9), text_color="#888").pack(side="right")

        hdr_sec(card, "Datos de la empresa")
        campo(card, "centro_costos", "Centro de costos", datos.get("centro_costos",""))
        campo(card, "direccion", "Dirección", datos.get("direccion",""))

        hdr_sec(card, "Beneficiario / Proveedor")
        campo(card, "proveedor_nombre", "Beneficiario", datos.get("proveedor_nombre",""))
        campo(card, "motivo_pago", "Motivo de pago", datos.get("motivo_pago",""))

        hdr_sec(card, "Datos de CFDI")
        campo(card, "folio_cfdi", "No. Folio(s) CFDI", datos.get("folio_cfdi",""))
        campo(card, "notas_credito", "Nota(s) de crédito", str(datos.get("notas_credito","")) if datos.get("notas_credito") else "")

        hdr_sec(card, "Datos de pago")
        monto = datos.get("monto_total",0) or 0
        campo(card, "importe_letra", "Importe en letra", datos.get("importe_letra",""))
        campo(card, "monto_total", "Importe total", f"{monto:.2f}")
        campo(card, "banco", "Institución Bancaria", datos.get("banco",""))
        campo(card, "clabe", "CLABE interbancaria", datos.get("clabe",""))
        campo(card, "no_cuenta", "No. de Cuenta", datos.get("no_cuenta",""))
        campo(card, "observaciones", "Observaciones", datos.get("observaciones",""))

        hdr_sec(card, "Exclusivo — Departamento de Finanzas")
        f_mes = ctk.CTkFrame(card, fg_color="transparent"); f_mes.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(f_mes, text="Mes presupuesto:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(side="left")
        ctk.CTkLabel(f_mes, text=datos.get("mes_presupuesto","—"),
                     font=ctk.CTkFont(size=10), text_color=AZUL_DARK).pack(side="left", padx=8)
        ctk.CTkLabel(f_mes, text="  Mes pago:", font=ctk.CTkFont(size=9, weight="bold"),
                     text_color="#555").pack(side="left", padx=(16,0))
        ctk.CTkLabel(f_mes, text=datos.get("mes_pago","—"),
                     font=ctk.CTkFont(size=10), text_color=AZUL_DARK).pack(side="left", padx=8)
        ctk.CTkLabel(f_mes, text=f"  Año: {datos.get('anio','—')}",
                     font=ctk.CTkFont(size=9), text_color="#888").pack(side="left", padx=8)

        # Firmantes (solo visualización)
        hdr_sec(card, "Firmantes")
        f_firm = ctk.CTkFrame(card, fg_color="transparent"); f_firm.pack(fill="x", padx=10, pady=8)
        for rol, nombre in [
            ("Solicitante / Analista de Sistemas", datos.get("analista_nombre","")),
            ("Gerente de Sistemas",                datos.get("gerente_nombre","")),
        ]:
            ff = ctk.CTkFrame(f_firm, fg_color="#F5F5F5", corner_radius=6,
                              border_color=BORDE, border_width=1)
            ff.pack(side="left", padx=(0,8), ipadx=8, ipady=4)
            ctk.CTkLabel(ff, text=rol, font=ctk.CTkFont(size=8), text_color=MUTED).pack()
            ctk.CTkLabel(ff, text=nombre or "____________________",
                         font=ctk.CTkFont(size=10, weight="bold"), text_color=AZUL_DARK).pack()

        ctk.CTkFrame(card, fg_color="transparent", height=12).pack()

        # Botones de acción
        bf = ctk.CTkFrame(win, fg_color=BLANCO, height=64, corner_radius=0,
                          border_color=BORDE, border_width=1)
        bf.pack(fill="x", side="bottom"); bf.pack_propagate(False)
        bf2 = ctk.CTkFrame(bf, fg_color="transparent"); bf2.pack(pady=14, padx=16, anchor="e")
        ctk.CTkLabel(bf2, text="¿Todo correcto?", font=ctk.CTkFont(size=11),
                     text_color=MUTED).pack(side="left", padx=(0,16))
        ctk.CTkButton(bf2, text="← Volver a editar", fg_color=BORDE, text_color=TEXTO,
                      hover_color="#D0D0D0", height=38, width=160,
                      command=win.destroy).pack(side="left", padx=(0,10))
        def _confirmar_con_edits():
            # Aplicar valores editados en la preview de vuelta al formulario
            for key, ent in preview_entries.items():
                val = ent.get().strip()
                try:
                    if key == "proveedor_nombre":
                        self.cb_proveedor.set(val)
                    elif key == "motivo_pago":
                        self.ent_motivo.delete(0,"end"); self.ent_motivo.insert(0,val)
                    elif key == "folio_cfdi":
                        self.ent_cfdi.delete(0,"end"); self.ent_cfdi.insert(0,val)
                    elif key == "monto_total":
                        self.ent_monto.delete(0,"end"); self.ent_monto.insert(0,val)
                    elif key == "banco":
                        try: self.ent_banco.set(val)
                        except Exception: pass
                    elif key == "clabe":
                        self.ent_clabe.delete(0,"end"); self.ent_clabe.insert(0,val)
                    elif key == "no_cuenta":
                        self.ent_cuenta.delete(0,"end"); self.ent_cuenta.insert(0,val)
                    elif key == "observaciones":
                        self.ent_obs.delete(0,"end"); self.ent_obs.insert(0,val)
                except Exception: pass
            win.destroy()
            self._gen_pdf()

        ctk.CTkButton(bf2, text="✓ Confirmar y generar PDF",
                      fg_color=ACENTO, hover_color=ACENTO_HOV,
                      text_color="white", font=ctk.CTkFont(size=12, weight="bold"),
                      height=38, width=240,
                      command=_confirmar_con_edits).pack(side="left")

    def _borrar_tmp(self, ruta: str):
        try:
            import os
            if os.path.exists(ruta): os.remove(ruta)
        except Exception: pass

    def _render_pdf_a_imagen(self, pdf_path: str):
        """Convierte primera página del PDF a imagen PIL via PowerShell."""
        import os, subprocess, tempfile
        safe_dir = os.path.join(os.environ.get("TEMP","C:\\Temp"), "GestorPreview")
        os.makedirs(safe_dir, exist_ok=True)
        png_out = os.path.join(safe_dir, "preview_pg.png")
        ps = r"""
param([string]$Pdf,[string]$Png)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function A1($t,$y){$m=[System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}|select -First 1;$x=$m.MakeGenericMethod($y).Invoke($null,@($t));$x.Wait();return $x.Result}
function AA($t){$m=[System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction'}|select -First 1;$x=$m.Invoke($null,@($t));$x.Wait()}
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapEncoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$f=A1 ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Pdf)) ([Windows.Storage.StorageFile])
$d=A1 ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($f)) ([Windows.Data.Pdf.PdfDocument])
$p=$d.GetPage(0)
$s=[Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
$o=[Windows.Data.Pdf.PdfPageRenderOptions]::new();$o.DestinationWidth=790
AA($p.RenderToStreamAsync($s,$o))
$s.Seek(0)
$dec=A1 ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp=A1 ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$dir=[System.IO.Path]::GetDirectoryName($Png)
$nm=[System.IO.Path]::GetFileName($Png)
$fol=A1 ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($dir)) ([Windows.Storage.StorageFolder])
$fi=A1 ($fol.CreateFileAsync($nm,[Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
$out=A1 ($fi.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
$enc=A1 ([Windows.Graphics.Imaging.BitmapEncoder]::CreateAsync([Windows.Graphics.Imaging.BitmapEncoder]::PngEncoderId,$out)) ([Windows.Graphics.Imaging.BitmapEncoder])
$enc.SetSoftwareBitmap($bmp)
AA($enc.FlushAsync())
$out.Dispose()
Write-Host "PREVIEW_OK"
"""
        ps1 = os.path.join(safe_dir, "render_preview.ps1")
        with open(ps1, "w", encoding="utf-8") as f: f.write(ps)
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", ps1, "-Pdf", str(Path(pdf_path).resolve()), "-Png", png_out],
                capture_output=True, text=True, timeout=30)
            if "PREVIEW_OK" in r.stdout and os.path.exists(png_out):
                return Image.open(png_out).copy()
        except Exception:
            pass
        return None

    def _mostrar_preview_imagen(self, img, frame, tmp_pdf):
        for w in frame.winfo_children(): w.destroy()
        if img:
            ctk_img = ctk.CTkImage(light_image=img, size=(img.width, img.height))
            lbl = ctk.CTkLabel(frame, image=ctk_img, text="")
            lbl.pack(pady=12, padx=12)
            lbl._img_ref = ctk_img  # evitar garbage collection
        else:
            ctk.CTkLabel(frame,
                text="Vista previa no disponible.\nUsa 'Confirmar y generar PDF' para ver el resultado.",
                font=ctk.CTkFont(size=13), text_color="white").pack(pady=40)

    def _abrir_externo(self, ruta: str):
        try: os.startfile(ruta)
        except Exception:
            try: subprocess.run(["start", "", ruta], shell=True)
            except Exception: pass

    def _render_pdf_preview(self, pdf_path: str):
        """Renderiza la primera página del PDF como imagen PIL usando PowerShell."""
        import os, tempfile, subprocess
        tmp_dir = tempfile.mkdtemp(prefix="ss_preview_")
        png_out = os.path.join(tmp_dir, "preview.png")
        ps = r"""
param([string]$PdfPath, [string]$PngPath)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
function Await1($task, $type) {
    $m = [System.WindowsRuntimeSystemExtensions].GetMethods() |
         Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } |
         Select-Object -First 1
    $t = $m.MakeGenericMethod($type).Invoke($null, @($task)); $t.Wait(); return $t.Result
}
function AwaitAction($task) {
    $m = [System.WindowsRuntimeSystemExtensions].GetMethods() |
         Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' } |
         Select-Object -First 1
    $t = $m.Invoke($null, @($task)); $t.Wait()
}
$null = [Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFolder,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapEncoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$pdfFile = Await1 ([Windows.Storage.StorageFile]::GetFileFromPathAsync($PdfPath)) ([Windows.Storage.StorageFile])
$pdfDoc  = Await1 ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($pdfFile)) ([Windows.Data.Pdf.PdfDocument])
$page    = $pdfDoc.GetPage(0)
$renderStream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
$opts = [Windows.Data.Pdf.PdfPageRenderOptions]::new(); $opts.DestinationWidth = 850
AwaitAction ($page.RenderToStreamAsync($renderStream, $opts))
$renderStream.Seek(0)
$decoder = Await1 ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($renderStream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$softBmp = Await1 ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$dir = [System.IO.Path]::GetDirectoryName($PngPath)
$name= [System.IO.Path]::GetFileName($PngPath)
$folder= Await1 ([Windows.Storage.StorageFolder]::GetFolderFromPathAsync($dir)) ([Windows.Storage.StorageFolder])
$file  = Await1 ($folder.CreateFileAsync($name,[Windows.Storage.CreationCollisionOption]::ReplaceExisting)) ([Windows.Storage.StorageFile])
$out   = Await1 ($file.OpenAsync([Windows.Storage.FileAccessMode]::ReadWrite)) ([Windows.Storage.Streams.IRandomAccessStream])
$enc   = Await1 ([Windows.Graphics.Imaging.BitmapEncoder]::CreateAsync([Windows.Graphics.Imaging.BitmapEncoder]::PngEncoderId,$out)) ([Windows.Graphics.Imaging.BitmapEncoder])
$enc.SetSoftwareBitmap($softBmp)
AwaitAction ($enc.FlushAsync())
$out.Dispose()
Write-Host "PNG_OK"
"""
        ps1 = os.path.join(tmp_dir, "render.ps1")
        with open(ps1, "w", encoding="utf-8") as f: f.write(ps)
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1,
             "-PdfPath", str(Path(pdf_path).resolve()), "-PngPath", png_out],
            capture_output=True, text=True, timeout=30)
        if "PNG_OK" in r.stdout and os.path.exists(png_out):
            return Image.open(png_out).copy()
        return None

    # ── Lógica ───────────────────────────────────────────────────────────────
    def _recargar_listas_combo(self):
        """Recarga combos de empresa/sucursal/CC/dirección/banco desde BD + config."""
        try:
            cfg = config.cargar()
            # Cargar desde BD
            db_empresas = []; db_sucursales = []; db_cc = []; db_dirs = []; db_bancos = []
            if self.db:
                try:
                    rows = self.db._conn().execute(
                        "SELECT DISTINCT empresa FROM empresas_cc ORDER BY empresa").fetchall()
                    db_empresas = [r[0] for r in rows if r[0]]
                except Exception: pass
                try:
                    rows = self.db._conn().execute(
                        "SELECT DISTINCT sucursal FROM empresas_cc ORDER BY sucursal").fetchall()
                    db_sucursales = [r[0] for r in rows if r[0]]
                except Exception: pass
                try:
                    rows = self.db._conn().execute(
                        "SELECT DISTINCT centro_costos FROM empresas_cc ORDER BY centro_costos").fetchall()
                    db_cc = [r[0] for r in rows if r[0]]
                except Exception: pass
                try:
                    rows = self.db._conn().execute(
                        "SELECT DISTINCT direccion FROM empresas_cc ORDER BY direccion").fetchall()
                    db_dirs = [r[0] for r in rows if r[0]]
                except Exception: pass
                try:
                    rows = self.db._conn().execute(
                        "SELECT nombre FROM bancos ORDER BY nombre").fetchall()
                    db_bancos = [r[0] for r in rows if r[0]]
                except Exception: pass

            # Combinar BD + config + defaults
            for cb, db_vals, key_extra, defaults in [
                (self.cb_empresa,  db_empresas,  "empresas_extra",    EMPRESAS),
                (self.cb_sucursal, db_sucursales,"sucursales_extra",  SUCURSALES),
                (self.cb_cc,       db_cc,        "centros_extra",     CENTROS),
                (self.cb_dir,      db_dirs,      "direcciones_extra", []),
            ]:
                extras = cfg.get(key_extra, [])
                combined = list(dict.fromkeys(defaults + db_vals + extras))
                try: cb.configure(values=combined)
                except Exception: pass

            # Banco desde BD
            if db_bancos:
                try: self.ent_banco.configure(values=db_bancos)
                except Exception: pass
        except Exception: pass

    def _recargar_proveedores(self):
        try:
            nombres = self._nombres_proveedores()
            if nombres: self.cb_proveedor.configure(values=nombres); self.cb_proveedor.set("")
            else: self.after(500, self._recargar_proveedores)
        except Exception: self.after(500, self._recargar_proveedores)

    def _recargar_bancos(self):
        try:
            if self.db:
                nombres = [b["nombre"] for b in self.db.listar_bancos()]
                if nombres:
                    self.ent_banco.configure(values=nombres)
                    return
            self.after(800, self._recargar_bancos)
        except Exception:
            self.after(800, self._recargar_bancos)

    def _get_bancos_lista(self) -> list:
        if not self.db: return []
        try: return [b["nombre"] for b in self.db.listar_bancos()]
        except Exception: return []

    def _nombres_proveedores(self) -> list:
        if not self.db: return []
        try: return [r["nombre"] for r in self.db.listar_proveedores()]
        except Exception: return []

    def _autocompletar_proveedor(self, nombre):
        if not self.db: return
        p = self.db.get_proveedor(nombre)
        if not p: return
        # Banco usa set() porque es ComboBox
        banco_val = (p.get("banco") or "").strip()
        if banco_val: self.ent_banco.set(banco_val)
        for e, k in [(self.ent_clabe,"clabe"),(self.ent_cuenta,"no_cuenta")]:
            e.delete(0,"end"); e.insert(0,(p.get(k) or "").strip())


    def _on_banco_seleccionado(self, nombre: str):
        """Cuando el usuario elige un banco del combo, podría hacer lógica adicional."""
        pass  # El banco se guarda directamente de ent_banco.get()

    def _guardar_groq_key(self):
        """Guarda la Groq API Key — ahora redirige a pantalla de configuración."""
        key = ""
        if hasattr(self, 'ent_groq_cfg'):
            key = self.ent_groq_cfg.get().strip()
        elif hasattr(self, 'ent_groq') and self.ent_groq:
            key = self.ent_groq.get().strip()
        cfg = config.cargar()
        cfg["groq_api_key"] = key
        config.guardar(cfg)


    def _upd_letra(self):
        try: m = float(self.ent_monto.get().replace(",","").replace("$","") or 0)
        except: m = 0.0
        self.lbl_letra.configure(text=numero_a_letra(m) if m else "")

    def _datos_form(self) -> dict:
        try:   monto = float(self.ent_monto.get().replace(",","").replace("$","") or 0)
        except: monto = 0.0
        try:   nc = float(self.ent_nc.get().replace(",","") or 0)
        except: nc = 0.0
        try:   mi = MESES.index(self.cb_mes_pago.get())+1
        except: mi = date.today().month
        # Dirección: inferir de la combinación sucursal+CC en BD
        direccion = self.cb_dir.get() if hasattr(self,'cb_dir') else ""
        analista = self.ent_analista.get().strip() if hasattr(self,'ent_analista') else ""
        gerente  = self.ent_gerente.get().strip()  if hasattr(self,'ent_gerente')  else ""
        return {
            "empresa": self.cb_empresa.get(), "sucursal": self.cb_sucursal.get(),
            "centro_costos": self.cb_cc.get(), "direccion": direccion,
            "proveedor_nombre": self.cb_proveedor.get(), "beneficiario": self.cb_proveedor.get(),
            "motivo_pago": self.ent_motivo.get(), "folio_cfdi": self.ent_cfdi.get(),
            "notas_credito": nc, "monto_total": monto, "importe_letra": numero_a_letra(monto),
            "banco": self.ent_banco.get(), "clabe": self.ent_clabe.get(),
            "no_cuenta": self.ent_cuenta.get(), "forma_pago": "Transferencia SPEI",
            "observaciones": self.ent_obs.get(), "mes_presupuesto": self.cb_mes_pres.get(),
            "mes_pago": self.cb_mes_pago.get(), "mes": mi,
            "anio": int(self.ent_anio.get() or date.today().year),
            "estatus": "PENDIENTE", "fecha_proceso": date.today().isoformat(),
            "analista_nombre": analista,
            "gerente_nombre": gerente,
        }

    def _guardar_bd(self) -> int | None:
        if not self.db: return None
        datos = self._datos_form()
        if not datos["proveedor_nombre"]:
            messagebox.showwarning("Campo requerido","Selecciona un proveedor."); return None

        # CRUD orgánico: guardar proveedor, banco, empresa, sucursal, CC y dirección
        prov_nombre = datos["proveedor_nombre"]
        banco  = datos.get("banco","").strip()
        clabe  = datos.get("clabe","").strip()
        no_cta = datos.get("no_cuenta","").strip()

        # Proveedor
        if prov_nombre:
            try:
                self.db.upsert_proveedor({
                    "nombre": prov_nombre, "banco": banco,
                    "clabe": clabe, "no_cuenta": no_cta,
                })
                self.after(100, self._recargar_proveedores)
            except Exception: pass

        # Banco
        if banco:
            try:
                bancos_actuales = self._get_bancos_lista()
                if banco.upper() not in [b.upper() for b in bancos_actuales]:
                    prefijo = clabe[:3] if clabe and len(clabe) >= 3 else ""
                    self.db.upsert_banco({"nombre": banco.upper(), "prefijo_clabe": prefijo})
                    self.after(100, self._recargar_bancos)
            except Exception: pass

        # Empresa / Sucursal / Centro de costos / Dirección
        # Los guardamos en una tabla JSON en config para que persistan entre sesiones
        try:
            empresa  = datos.get("empresa","").strip()
            sucursal = datos.get("sucursal","").strip()
            cc       = datos.get("centro_costos","").strip()
            direccion= datos.get("direccion","").strip()
            cfg_listas = config.cargar()
            changed = False
            for key_lst, val in [("empresas_extra", empresa),
                                  ("sucursales_extra", sucursal),
                                  ("centros_extra", cc),
                                  ("direcciones_extra", direccion)]:
                if val:
                    lista = cfg_listas.get(key_lst, [])
                    if val not in lista:
                        lista.append(val)
                        cfg_listas[key_lst] = lista
                        changed = True
            if changed:
                config.guardar(cfg_listas)
                self.after(200, self._recargar_listas_combo)
        except Exception: pass

        if self._pago_editando:
            self.db.actualizar_pago(self._pago_editando, datos); pid = self._pago_editando
        else:
            pid = self.db.crear_pago(datos)
        return pid

    def _nombre_pdf(self, datos: dict) -> str:
        """Genera el nombre del PDF: Solicitud_EUP_TELEFONOSDEMEXICO_070526_MAY_4.pdf"""
        import re, unicodedata
        def clean(s: str, maxlen: int = 20) -> str:
            s = unicodedata.normalize("NFD", s)
            s = s.encode("ascii", "ignore").decode("ascii")
            s = re.sub(r"[^A-Za-z0-9]", "", s).upper()
            return s[:maxlen]
        empresa  = datos.get("empresa","") or ""
        prov     = datos.get("proveedor_nombre","") or ""
        # Abreviar empresa: iniciales de cada palabra
        emp_words = [w for w in empresa.split() if len(w) > 2 and w.upper() not in ("SA","DE","CV","SRL")]
        emp_short = "".join(w[0] for w in emp_words[:4]).upper() or clean(empresa, 6)
        prov_short = clean(prov.replace("TELEFONOS DE MEXICO","TELMEX")
                             .replace("TOTAL PLAY TELECOMUNICACIONES","TOTALPLAY")
                             .replace("RADIOMOVIL DIPSA","TELCEL"), 16)
        fecha = date.today().strftime("%d%m%y")
        mes   = (datos.get("mes_pago") or datos.get("mes_presupuesto") or "")[:3].upper()
        # Número correlativo
        num = 1
        if self.db:
            try:
                total = self.db._conn().execute("SELECT COUNT(*) FROM pagos").fetchone()[0]
                num = (total or 0) + 1
            except Exception: pass
        return f"Solicitud_{emp_short}_{prov_short}_{fecha}_{mes}_{num}.pdf"

    def _gen_pdf(self):
        import config as cfg_mod
        cfg_now = cfg_mod.cargar()
        # No guardamos firmantes en config — son por solicitud, no globales
        cfg_mod.guardar(cfg_now)
        if not self._modo:
            messagebox.showwarning("Elige un modo","Selecciona 'Subir recibo' o 'Llenado manual' primero."); return
        pid = self._guardar_bd()
        if pid is None: return
        datos = self._datos_form()
        prov  = datos["proveedor_nombre"][:15].replace(" ","_")
        ruta  = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF","*.pdf")],
            initialfile=f"SolicitudPago_{prov}_{date.today().isoformat()}.pdf")
        if not ruta: return
        try:
            exportar_solicitud_pdf(datos, ruta_salida=ruta)
            if self.db: self.db.actualizar_pdf(pid, ruta)
            self.lbl_save.configure(text=f"✓ PDF generado (ID {pid})", text_color=VERDE)
            # Refrescar historial inmediatamente
            try: self._load_historial()
            except Exception: pass
            if messagebox.askyesno("PDF generado", f"PDF guardado:\n{ruta}\n\n¿Abrir el PDF ahora?"):
                try: os.startfile(ruta)
                except Exception: pass
        except Exception as e:
            messagebox.showerror("Error al generar PDF", str(e))

    def _editar(self, pid):
        if not self.db: return
        p = self.db.get_pago(pid)
        if not p: return
        self._pago_editando = pid
        self._unlock_form("manual"); self._nav_nueva()
        self.lbl_modo.configure(text=f"Editando registro ID {pid}", text_color=AMBAR)
        self.cb_empresa.set(p.get("empresa","")); self.cb_sucursal.set(p.get("sucursal",""))
        self.cb_cc.set(p.get("centro_costos","")); self.cb_proveedor.set(p.get("proveedor_nombre",""))
        banco_edit = str(p.get("banco","") or "")
        if banco_edit: self.ent_banco.set(banco_edit)
        for e, k in [(self.ent_motivo,"motivo_pago"),(self.ent_cfdi,"folio_cfdi"),
                     (self.ent_monto,"monto_total"),(self.ent_clabe,"clabe"),
                     (self.ent_cuenta,"no_cuenta"),(self.ent_obs,"observaciones")]:
            e.delete(0,"end"); e.insert(0, str(p.get(k,"") or ""))
        self._upd_letra()
        self.btn_eliminar_hdr.pack(side="right", padx=(0,8), pady=12)
        self.lbl_save.configure(text=f"Editando ID {pid}", text_color=AMBAR)

    def _eliminar_editando(self):
        """Eliminar de BD si hay registro guardado, luego limpiar campos sin bloquear."""
        if self._pago_editando:
            pid = self._pago_editando
            if messagebox.askyesno("Eliminar registro",
                f"¿Eliminar el registro ID {pid}?\nEsta acción no se puede deshacer."):
                if self.db: self.db.eliminar_pago(pid)
                self._limpiar_solo_campos()
                messagebox.showinfo("Eliminado", f"Registro ID {pid} eliminado.")
        else:
            self._limpiar_solo_campos()
    def _cambiar_estatus(self, pid: int, nuevo_est: str):
        if not self.db: return
        self.db.actualizar_pago(pid, {"estatus": nuevo_est}); self._load_historial()

    def _del_pago(self, pid):
        if messagebox.askyesno("Confirmar",f"¿Eliminar el pago ID {pid}?\nNo se puede deshacer."):
            self.db.eliminar_pago(pid); self._load_historial()

    def _pdf_hist(self, pid):
        if not self.db: return
        p = self.db.get_pago(pid)
        if not p: return
        ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")],
            initialfile=f"SolicitudPago_{pid}.pdf")
        if not ruta: return
        try: exportar_solicitud_pdf(p, ruta_salida=ruta); messagebox.showinfo("PDF generado", f"Guardado en:\n{ruta}")
        except Exception as e: messagebox.showerror("Error",str(e))

    def _xls_hist(self):
        self._do_xls(MESES.index(self.cb_hm.get())+1, int(self.ent_ha.get() or date.today().year))

    def _do_xls(self, mes, anio):
        if not self.db: return
        ruta = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=f"EstadoCuenta_{MESES[mes-1]}_{anio}.xlsx")
        if not ruta: return
        estado = self.db.estado_cuenta_mes(mes, anio)
        exportar_estado_cuenta_xlsx(estado, ruta_salida=ruta)

    def _limpiar_eventos_prueba(self):
        """Elimina eventos de prueba de TODOS los perfiles de Outlook."""
        from outlook_alertas import eliminar_eventos_prueba
        if not messagebox.askyesno(
            "Confirmar limpieza",
            "Se eliminarán TODOS los eventos de prueba del calendario de Outlook "
            "(incluyendo los que quedaron en otros perfiles).\n\nContinuar?"
        ):
            return
        n, msg = eliminar_eventos_prueba("PRUEBA-TEST")
        if n > 0:
            messagebox.showinfo("Limpieza completa", msg)
        else:
            messagebox.showinfo("Sin eventos", f"No se encontraron eventos de prueba.\n{msg}")

    def _purgar_citas_outlook(self):
        """Elimina TODAS las citas creadas por la app en el calendario activo."""
        if not messagebox.askyesno("Confirmar purga",
            "Esto eliminara TODAS las citas con el texto 'PAGAR:' del calendario "
            "de Outlook activo.\n\nUsar para limpiar citas creadas en una "
            "cuenta incorrecta. Continuar?"):
            return
        import threading
        def _do():
            try:
                n = purgar_citas_outlook("PAGAR:")
                self.after(0, lambda: messagebox.showinfo(
                    "Citas eliminadas", f"Se eliminaron {n} citas del calendario activo."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"No se pudieron eliminar las citas:\n{e}"))
        threading.Thread(target=_do, daemon=True).start()

    def _probar_outlook_conexion(self):
        """Prueba la conexión con Outlook y muestra resultado en ventana."""
        import threading
        def _do():
            try:
                import win32com.client as _win32
                ol = _win32.Dispatch("Outlook.Application")
                ver = ol.Version
                ns = ol.GetNamespace("MAPI")
                email = ""
                try: email = ns.CurrentUser.Address
                except Exception: pass
                msg = f"✓ Outlook conectado correctamente.\nVersión: {ver}\nUsuario: {email}"
                color = VERDE
            except ImportError:
                msg = "✗ pywin32 no instalado.\nEjecuta INSTALAR.bat para instalarlo."
                color = ROJO
            except Exception as e:
                msg = f"✗ No se pudo conectar con Outlook:\n{str(e)[:200]}"
                color = ROJO
            self.after(0, lambda: self._mostrar_resultado_outlook(msg, color))
        threading.Thread(target=_do, daemon=True).start()
        messagebox.showinfo("Probando", "Intentando conectar con Outlook... Espera un momento.")

    def _mostrar_resultado_outlook(self, msg: str, color: str):
        win = ctk.CTkToplevel(self)
        win.title("Resultado — Conexión Outlook")
        win.geometry("500x220")
        win.grab_set()
        hdr = ctk.CTkFrame(win, fg_color=AZUL_DARK, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Diagnóstico de conexión con Outlook",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="white").pack(side="left", padx=16, pady=10)
        ctk.CTkButton(hdr, text="✕", fg_color="#555", height=28, width=36,
                      command=win.destroy).pack(side="right", padx=8, pady=8)
        ctk.CTkLabel(win, text=msg, font=ctk.CTkFont(size=12),
                     text_color=color, wraplength=460, justify="left").pack(pady=24, padx=24)

    def _check_outlook(self):
        def _check():
            ok = verificar_outlook()
            self.after(0, lambda: self._set_ol(ok))
        threading.Thread(target=_check, daemon=True).start()

    def _set_ol(self, ok: bool):
        self._outlook_ok = ok
        if ok:
            msg = "✓ Outlook vinculado — recordatorios se crearán en tu calendario"
            color = VERDE; sb_color = "#4CAF50"
        else:
            msg = "✗ Outlook no encontrado — abre Outlook primero"
            color = ROJO; sb_color = ROJO
        try:
            self.lbl_ol_cal.configure(text=msg, text_color=color)
            self.lbl_ol_sb.configure(text=f"● {'Outlook vinculado' if ok else 'Outlook desconectado'}",
                                      text_color=sb_color)
        except Exception: pass

    def _make_reminders(self):
        if not self.db: return
        if not self._outlook_ok:
            messagebox.showwarning("Outlook no disponible","Outlook no está disponible. Ábrelo primero."); return
        servicios = self.db.servicios_proximos(31)  # todo el mes  # (60)
        if not servicios:
            messagebox.showinfo("Sin servicios","No hay servicios próximos a vencer."); return
        creados = crear_recordatorios_lote(servicios)
        messagebox.showinfo("Recordatorios creados",f"Se crearon {creados} recordatorio(s) en tu calendario de Outlook.")

    def _limpiar(self):
        """Limpia COMPLETAMENTE el formulario. Los firmantes se recargan de config."""
        self._pago_editando = None
        self._modo = None
        self._datos_ocr = {}
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._set_form_state("disabled")
        self.btn_modo_pdf.configure(fg_color=ACENTO, text_color="white")
        self.btn_modo_manual.configure(fg_color=BORDE, text_color=TEXTO)
        self.lbl_modo.configure(text="← Elige un modo para habilitar el formulario", text_color=AMBAR)
        # Limpiar TODOS los campos de datos (NUNCA los firmantes automáticamente)
        # Banco es ComboBox → .set(), entries → .delete()
        try: self.ent_banco.set("")
        except Exception: pass
        for w in [self.ent_motivo, self.ent_cfdi, self.ent_nc, self.ent_monto,
                  self.ent_clabe, self.ent_cuenta, self.ent_obs]:
            try:
                w.delete(0, "end")
            except Exception:
                try: w.set("")
                except Exception: pass
        # Firmantes: quedan VACÍOS — el usuario los llena manualmente
        for e in [self.ent_analista]:
            try: e.delete(0,"end")
            except Exception: pass
        # Resetear combos
        for cb in [self.cb_empresa, self.cb_sucursal, self.cb_cc, self.cb_dir, self.cb_proveedor]:
            try: cb.set("")
            except Exception: pass
        try:
            mes_actual = MESES[date.today().month-1]
            self.cb_mes_pres.set(mes_actual); self.cb_mes_pago.set(mes_actual)
        except Exception: pass
        try: self.ent_anio.delete(0,"end"); self.ent_anio.insert(0, str(date.today().year))
        except Exception: pass
        self.lbl_letra.configure(text="")
        self.lbl_save.configure(text="")
        # Reset mes/año a valores actuales (no dejarlos como estaban)
        try:
            self.cb_mes_pres.set(MESES[date.today().month-1])
            self.cb_mes_pago.set(MESES[date.today().month-1])
        except Exception: pass
        try:
            self.ent_anio.delete(0,"end")
            self.ent_anio.insert(0, str(date.today().year))
        except Exception: pass
        self.lbl_est.configure(text="")
        self.btn_eliminar_hdr.pack_forget()



    # ════════════════════════════════════════════════════════════════════════
    # PANTALLA: CONFIGURACIÓN
    # ════════════════════════════════════════════════════════════════════════
    def _build_configuracion(self):
        sc = ctk.CTkFrame(self.main, fg_color=FONDO, corner_radius=0)
        self.screens["configuracion"] = sc

        hdr = ctk.CTkFrame(sc, fg_color=BLANCO, height=58, corner_radius=0,
                           border_color=BORDE, border_width=1)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Configuración",
                     font=ctk.CTkFont("Georgia",15,"bold"),
                     text_color=AZUL_DARK).pack(side="left", padx=20)

        scroll = ctk.CTkScrollableFrame(sc, fg_color=FONDO, border_width=0)
        scroll.pack(fill="both", expand=True, padx=24, pady=16)

        # ── Sección: OCR con IA ──────────────────────────────────────────
        sec1 = ctk.CTkFrame(scroll, fg_color=AZUL_DARK, corner_radius=6)
        sec1.pack(fill="x", pady=(0,6))
        ctk.CTkLabel(sec1, text="OCR CON INTELIGENCIA ARTIFICIAL (GROQ)",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").pack(anchor="w", padx=12, pady=6)

        groq_card = ctk.CTkFrame(scroll, fg_color=BLANCO, corner_radius=10,
                                  border_color=BORDE, border_width=1)
        groq_card.pack(fill="x", pady=(0,16))
        gc = ctk.CTkFrame(groq_card, fg_color="transparent"); gc.pack(padx=16, pady=14, fill="x")

        ctk.CTkLabel(gc,
            text="Groq Vision lee recibos PDF con IA y llena campos automáticamente.\n"
                 "Es completamente gratuito. Obtén tu key en: console.groq.com -> API Keys",
            font=ctk.CTkFont(size=11), text_color=MUTED, justify="left").pack(anchor="w", pady=(0,10))

        cfg_now = config.cargar()
        key_actual = cfg_now.get("groq_api_key","")
        estado_groq = "✓ Groq configurado — el OCR usa IA" if key_actual else "✗ Sin API Key — OCR usa Windows nativo"
        color_groq = VERDE if key_actual else AMBAR
        self.lbl_groq_estado = ctk.CTkLabel(gc, text=estado_groq,
                                             font=ctk.CTkFont(size=11, weight="bold"),
                                             text_color=color_groq)
        self.lbl_groq_estado.pack(anchor="w", pady=(0,8))

        gr = ctk.CTkFrame(gc, fg_color="transparent"); gr.pack(anchor="w", fill="x")
        ctk.CTkLabel(gr, text="API Key:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,8))
        self.ent_groq_cfg = ctk.CTkEntry(gr, width=420, font=ctk.CTkFont(size=11),
                                          placeholder_text="gsk_...")
        self.ent_groq_cfg.pack(side="left", padx=(0,8))
        if key_actual:
            self.ent_groq_cfg.insert(0, key_actual)
        ctk.CTkButton(gr, text="Guardar", fg_color=ACENTO, hover_color=ACENTO_HOV,
                      text_color="white", height=34, width=90, font=ctk.CTkFont(size=12),
                      command=self._guardar_groq_cfg).pack(side="left", padx=(0,6))
        ctk.CTkButton(gr, text="Probar", fg_color="#555555", text_color="white",
                      height=34, width=70, font=ctk.CTkFont(size=12),
                      command=self._probar_groq).pack(side="left", padx=(0,6))
        ctk.CTkButton(gr, text="Borrar", fg_color=BORDE, text_color=ROJO,
                      height=34, width=70, font=ctk.CTkFont(size=12),
                      command=lambda: self._guardar_groq_cfg(borrar=True)).pack(side="left")

        self.lbl_groq_test = ctk.CTkLabel(gc, text="",
                                           font=ctk.CTkFont(size=11), text_color=VERDE)
        self.lbl_groq_test.pack(anchor="w", pady=(8,0))
        ctk.CTkButton(gc, text="Probar conexión a Groq ahora",
                      fg_color="#555555", hover_color="#333333",
                      text_color="white", height=32, width=230, font=ctk.CTkFont(size=11),
                      command=self._test_groq).pack(anchor="w", pady=(4,0))


        # ── Sección: Usuario ─────────────────────────────────────────────
        sec2 = ctk.CTkFrame(scroll, fg_color=AZUL_DARK, corner_radius=6)
        sec2.pack(fill="x", pady=(0,6))
        ctk.CTkLabel(sec2, text="USUARIO Y FIRMANTES",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").pack(anchor="w", padx=12, pady=6)

        user_card = ctk.CTkFrame(scroll, fg_color=BLANCO, corner_radius=10,
                                  border_color=BORDE, border_width=1)
        user_card.pack(fill="x", pady=(0,16))
        uc = ctk.CTkFrame(user_card, fg_color="transparent"); uc.pack(padx=16, pady=14, fill="x")

        ctk.CTkLabel(uc, text="Estos nombres aparecen en las solicitudes de pago generadas.",
                     font=ctk.CTkFont(size=11), text_color=MUTED).pack(anchor="w", pady=(0,10))

        ur1 = ctk.CTkFrame(uc, fg_color="transparent"); ur1.pack(anchor="w", pady=4)
        ctk.CTkLabel(ur1, text="Solicitante (tu nombre):", font=ctk.CTkFont(size=12),
                     width=220, anchor="w").pack(side="left")
        self.ent_cfg_analista = ctk.CTkEntry(ur1, width=280, font=ctk.CTkFont(size=12),
                                              placeholder_text="Nombre completo")
        self.ent_cfg_analista.pack(side="left")
        self.ent_cfg_analista.insert(0, cfg_now.get("analista_nombre",""))

        ur2 = ctk.CTkFrame(uc, fg_color="transparent"); ur2.pack(anchor="w", pady=4)
        ctk.CTkLabel(ur2, text="Gerente / Autoriza:", font=ctk.CTkFont(size=12),
                     width=220, anchor="w").pack(side="left")
        self.ent_cfg_gerente = ctk.CTkEntry(ur2, width=280, font=ctk.CTkFont(size=12),
                                             placeholder_text="Nombre completo")
        self.ent_cfg_gerente.pack(side="left")
        self.ent_cfg_gerente.insert(0, cfg_now.get("gerente_nombre",""))

        self.lbl_cfg_guardado = ctk.CTkLabel(uc, text="",
                                              font=ctk.CTkFont(size=11), text_color=VERDE)
        self.lbl_cfg_guardado.pack(anchor="w", pady=(8,0))

        for key_cfg, lbl_cfg in [
            ("firmante_analista",  "Solicitante/Analista por default:"),
            ("firmante_gerente",   "Gerente de Sistemas por default:"),
            ("firmante_visto_bno", "Vo. Bo. / Depto. Finanzas:"),
            ("firmante_depto_fin", "Depto. Finanzas Presupuestos:"),
            ("firmante_dir_fin",   "Dirección Financiera:"),
            ("firmante_dir_gral",  "Dirección General:"),
        ]:
            ur_f = ctk.CTkFrame(uc, fg_color="transparent"); ur_f.pack(anchor="w", pady=2)
            ctk.CTkLabel(ur_f, text=lbl_cfg, font=ctk.CTkFont(size=11),
                         width=240, anchor="w").pack(side="left")
            ent_f = ctk.CTkEntry(ur_f, width=260, font=ctk.CTkFont(size=11))
            ent_f.pack(side="left")
            ent_f.insert(0, cfg_now.get(key_cfg,""))
            ent_f._cfg_key = key_cfg  # tag para guardar

        ctk.CTkButton(uc, text="Guardar nombres", fg_color=ACENTO, hover_color=ACENTO_HOV,
                      text_color="white", height=36, width=160, font=ctk.CTkFont(size=12),
                      command=self._guardar_nombres_cfg).pack(anchor="w", pady=(8,0))

        # ── Sección: Base de datos ────────────────────────────────────────
        sec3 = ctk.CTkFrame(scroll, fg_color=AZUL_DARK, corner_radius=6)
        sec3.pack(fill="x", pady=(0,6))
        ctk.CTkLabel(sec3, text="BASE DE DATOS",
                     font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="white").pack(anchor="w", padx=12, pady=6)

        db_card = ctk.CTkFrame(scroll, fg_color=BLANCO, corner_radius=10,
                                border_color=BORDE, border_width=1)
        db_card.pack(fill="x", pady=(0,16))
        dc = ctk.CTkFrame(db_card, fg_color="transparent"); dc.pack(padx=16, pady=14, fill="x")

        cfg_again = config.cargar()
        db_ruta = cfg_again.get("db_path","") or "(no configurada)"
        # Resolver ruta real si es relativa
        import os
        if db_ruta and db_ruta != "(no configurada)" and not os.path.isabs(db_ruta):
            db_ruta_abs = str(Path(db_ruta).resolve())
        elif db_ruta == "(no configurada)":
            db_ruta_abs = db_ruta
        else:
            db_ruta_abs = db_ruta
        # ── Card: Eliminar eventos de prueba de Outlook ──────────────────────
        lim_card = ctk.CTkFrame(dc, fg_color="#FEE2E2", corner_radius=10,
                                border_color="#C0392B", border_width=1)
        lim_card.pack(fill="x", pady=(0,10))
        lim_row = ctk.CTkFrame(lim_card, fg_color="transparent")
        lim_row.pack(padx=14, pady=10, fill="x")
        ctk.CTkLabel(lim_row,
                     text="🗑  Eliminar eventos de PRUEBA del calendario (borra de TODOS los perfiles de Outlook):",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#C0392B").pack(side="left", padx=(0,12))
        ctk.CTkButton(lim_row, text="Limpiar ahora",
                      fg_color="#C0392B", text_color="white",
                      font=ctk.CTkFont(size=11, weight="bold"),
                      height=34, width=130,
                      command=self._limpiar_eventos_prueba).pack(side="right")

        self.lbl_db_ruta = ctk.CTkLabel(dc,
            text=f"Archivo activo: {db_ruta_abs}",
            font=ctk.CTkFont(size=11), text_color=MUTED,
            wraplength=700, justify="left")
        self.lbl_db_ruta.pack(anchor="w", pady=(0,10))
        db_btn_row = ctk.CTkFrame(dc, fg_color="transparent")
        db_btn_row.pack(anchor="w")
        ctk.CTkButton(db_btn_row, text="Cambiar ruta de pagos.db",
                      fg_color=BORDE, text_color=TEXTO, hover_color="#D0D0D0",
                      height=32, width=200, font=ctk.CTkFont(size=11),
                      command=self._cambiar_ruta_db).pack(side="left", padx=(0,10))
        ctk.CTkButton(db_btn_row, text="Borrar BD y reiniciar",
                      fg_color="#C0392B", text_color="white", hover_color="#922B21",
                      height=32, width=180, font=ctk.CTkFont(size=11),
                      command=self._borrar_bd_reiniciar).pack(side="left")

    def _load_configuracion(self):
        """Recarga los valores actuales al entrar a configuración."""
        cfg = config.cargar()
        try:
            key = cfg.get("groq_api_key","")
            self.ent_groq_cfg.delete(0,"end")
            if key: self.ent_groq_cfg.insert(0, key)
            estado = "✓ Groq configurado — el OCR usa IA" if key else "✗ Sin API Key — OCR usa Windows nativo"
            self.lbl_groq_estado.configure(text=estado, text_color=VERDE if key else AMBAR)
        except Exception: pass
        try:
            self.ent_cfg_analista.delete(0,"end")
            self.ent_cfg_analista.insert(0, cfg.get("analista_nombre",""))
            self.ent_cfg_gerente.delete(0,"end")
            self.ent_cfg_gerente.insert(0, cfg.get("gerente_nombre",""))
        except Exception: pass

    def _test_groq(self):
        """Prueba la conexión a Groq y muestra resultado detallado."""
        key = self.ent_groq_cfg.get().strip()
        if not key:
            try: self.lbl_groq_test.configure(text="✗ Ingresa una API Key primero", text_color=ROJO)
            except Exception: pass
            return
        try: self.lbl_groq_test.configure(text="⏳ Probando conexión a Groq...", text_color=AMBAR)
        except Exception: pass
        self.update()

        def _do_test():
            log_lines = []
            # Paso 1: test de texto
            log_lines.append("─── Paso 1: Conexión de texto ───")
            ok, msg = probar_groq_conexion(key)
            log_lines.append(msg)
            if not ok:
                self.after(0, lambda m=msg: self._set_groq_test_result(m, ROJO))
                self.after(0, lambda ll=log_lines: self._mostrar_groq_detalle(ll))
                return
            # Paso 2: test de visión
            log_lines.append("─── Paso 2: Vision con imagen ───")
            try:
                import base64, struct, zlib, urllib.request, urllib.error
                def tiny_png():
                    def chunk(n, d):
                        c = struct.pack('>I',len(d))+n+d
                        return c+struct.pack('>I',zlib.crc32(n+d)&0xffffffff)
                    return (b'\x89PNG\r\n\x1a\n'
                            +chunk(b'IHDR',struct.pack('>IIBBBBB',10,10,8,2,0,0,0))
                            +chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'*10*10))
                            +chunk(b'IEND',b''))
                img_b64 = base64.b64encode(tiny_png()).decode()
                payload = json.dumps({
                    "model":"meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages":[{"role":"user","content":[
                        {"type":"image_url","image_url":{"url":f"data:image/png;base64,{img_b64}"}},
                        {"type":"text","text":"Que ves? Una palabra."}
                    ]}],
                    "max_tokens":15
                }).encode()
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
                    }
                )
                with urllib.request.urlopen(req, timeout=20) as r:
                    data2 = json.loads(r.read())
                resp2 = data2["choices"][0]["message"]["content"].strip()
                log_lines.append(f"✓ Vision OK — respuesta: '{resp2}'")
                log_lines.append("✓ Groq Vision está listo para OCR de recibos")
                final_msg = "✓ Todo OK — Groq Vision funcionando"
                final_color = VERDE
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")
                log_lines.append(f"✗ HTTP {e.code} en vision: {body[:200]}")
                final_msg = f"✗ Vision falló (HTTP {e.code})"
                final_color = ROJO
            except Exception as e:
                log_lines.append(f"✗ Error en vision: {str(e)[:150]}")
                final_msg = "✗ Error en Vision"
                final_color = ROJO

            self.after(0, lambda m=final_msg, c=final_color: self._set_groq_test_result(m, c))
            self.after(0, lambda ll=log_lines: self._mostrar_groq_detalle(ll))

        import threading, json
        threading.Thread(target=_do_test, daemon=True).start()

    def _mostrar_groq_detalle(self, lineas: list):
        """Muestra ventana con el log detallado del test de Groq."""
        win = ctk.CTkToplevel(self)
        win.title("Diagnóstico Groq")
        win.geometry("640x420")
        win.grab_set()
        hdr = ctk.CTkFrame(win, fg_color=AZUL_DARK, height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Resultado del diagnóstico de Groq",
                     font=ctk.CTkFont(size=13, weight="bold"), text_color="white"
                     ).pack(side="left", padx=16, pady=10)
        ctk.CTkButton(hdr, text="✕ Cerrar", fg_color="#555", font=ctk.CTkFont(size=11),
                      height=28, command=win.destroy).pack(side="right", padx=8, pady=8)
        txt = ctk.CTkTextbox(win, font=ctk.CTkFont("Courier",11), wrap="word")
        txt.pack(fill="both", expand=True, padx=12, pady=12)
        txt.insert("end", "\n".join(lineas))
        txt.configure(state="disabled")

    def _set_groq_test_result(self, msg: str, color: str):
        try: self.lbl_groq_test.configure(text=msg, text_color=color)
        except Exception: pass

    def _guardar_groq_cfg(self, borrar=False):
        cfg = config.cargar()
        if borrar:
            cfg["groq_api_key"] = ""
            config.guardar(cfg)
            try:
                self.ent_groq_cfg.delete(0,"end")
                self.lbl_groq_estado.configure(text="✗ Sin API Key — OCR usa Windows nativo", text_color=AMBAR)
            except Exception: pass
            return
        key = self.ent_groq_cfg.get().strip()
        cfg["groq_api_key"] = key
        config.guardar(cfg)
        estado = "✓ Groq configurado — el OCR usa IA" if key else "✗ Sin API Key"
        try: self.lbl_groq_estado.configure(text=estado, text_color=VERDE if key else AMBAR)
        except Exception: pass

    def _probar_groq(self):
        """Prueba la conexión con Groq en un hilo separado."""
        import threading
        key = self.ent_groq_cfg.get().strip()
        if not key:
            try: self.lbl_groq_test.configure(text="✗ Ingresa una API Key primero", text_color=ROJO)
            except Exception: pass
            return
        try: self.lbl_groq_test.configure(text="Probando conexión con Groq…", text_color=AMBAR)
        except Exception: pass
        def _test():
            import urllib.request, urllib.error, json as _json
            try:
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = _json.loads(resp.read())
                    modelos = [m["id"] for m in data.get("data", [])]
                    vision = [m for m in modelos if "vision" in m or "llama-4" in m]
                    msg = f"✓ Groq OK — {len(modelos)} modelos disponibles"
                    color = VERDE
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")[:80]
                msg = f"✗ Error {e.code}: {body}"
                color = ROJO
            except Exception as e:
                msg = f"✗ {type(e).__name__}: {str(e)[:80]}"
                color = ROJO
            self.after(0, lambda: self.lbl_groq_test.configure(text=msg, text_color=color))
        threading.Thread(target=_test, daemon=True).start()

    def _guardar_nombres_cfg(self):
        cfg = config.cargar()
        # Guardar todos los firmantes configurados en la pantalla
        try:
            for widget in self._get_all_children(self.screens.get("configuracion")):
                if hasattr(widget, "_cfg_key") and hasattr(widget, "get"):
                    val = widget.get().strip()
                    if val: cfg[widget._cfg_key] = val
        except Exception: pass
        # También los entries específicos si existen
        for ent_attr, key in [
            ("ent_cfg_analista","firmante_analista"),
            ("ent_cfg_gerente","firmante_gerente"),
        ]:
            try:
                val = getattr(self, ent_attr).get().strip()
                if val: cfg[key] = val
            except Exception: pass
        config.guardar(cfg)
        try: self.lbl_cfg_guardado.configure(text="✓ Nombres guardados", text_color=VERDE)
        except Exception: pass

    def _get_all_children(self, widget):
        """Devuelve todos los widgets hijos recursivamente."""
        result = []
        if widget is None: return result
        try:
            for child in widget.winfo_children():
                result.append(child)
                result.extend(self._get_all_children(child))
        except Exception: pass
        return result


    def _cambiar_ruta_db(self):
        """Permite al usuario seleccionar una ubicación diferente para pagos.db."""
        from tkinter import filedialog as _fd
        ruta = _fd.askopenfilename(
            title="Selecciona pagos.db",
            filetypes=[("Base de datos SQLite","*.db *.sqlite"),("Todos","*.*")])
        if not ruta: return
        cfg = config.cargar()
        cfg["db_path"] = ruta
        config.guardar(cfg)
        self._init_db(ruta)
        try: self.lbl_db_ruta.configure(text=f"Archivo activo: {ruta}")
        except Exception: pass
        messagebox.showinfo("BD cambiada", f"Ahora usando:\n{ruta}")

    def _borrar_bd_reiniciar(self):
        """Borra la BD actual y crea una nueva desde cero con datos semilla."""
        import os
        if not messagebox.askyesno("Confirmar",
            "¿Seguro que quieres borrar TODA la base de datos y reiniciar?\n"
            "Se perderán todos los pagos registrados. Esta acción NO se puede deshacer."):
            return
        cfg = config.cargar()
        ruta = cfg.get("db_path","") or ""
        if ruta and os.path.exists(ruta):
            try: os.remove(ruta)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar el archivo:\n{e}"); return
        # Re-inicializar con datos semilla
        self._init_db(ruta)
        try: self._load_historial()
        except Exception: pass
        try: self._load_configuracion()
        except Exception: pass
        messagebox.showinfo("Listo", "Base de datos reiniciada con datos semilla.")


if __name__ == "__main__":
    app = GestorApp()
    app.mainloop()
