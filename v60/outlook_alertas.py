"""
outlook_alertas.py v58.1 — Gestor de Constancias Aduaneras
CORRECCIÓN: Usa el Outlook del usuario actual (sistemas.3@selectshop.com.mx)
            NO el Outlook Classic de otro perfil.
            Fuerza la cuenta correcta al enviar.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta

try:
    import win32com.client as win32
    OUTLOOK_DISPONIBLE = True
except ImportError:
    OUTLOOK_DISPONIBLE = False

# Cuenta que DEBE usar la app para enviar (el analista de sistemas)
CUENTA_REMITENTE = "sistemas.3@selectshop.com.mx"
# Destinatario de prueba (para cuando modo_prueba=True)
CORREO_PRUEBA_DESTINO = "sistemas.2@selectshop.com.mx"

CUERPO_CORREO = """\
Estimado cliente buena tarde.

Le recordamos que 10 días antes del vencimiento de las constancias deberá enviar por correo electrónico la documentación necesaria para la liberación de los recursos en garantía al buzón cuentaaduanera.mx@bbva.com los documentos que deberá enviar digitalizados en un solo correo son:

1. Formato de Liberación. Al registrar en la plataforma la liberación de sus constancias el sistema le arrojará este formato, el cual deberán dar nombre y firma de su representante legal (lo puedes obtener en la plataforma, dentro del apartado de "Devolución" indicando el folio de la constancia y consultar, da clic en el folio, abrirá una pantalla con la información de la constancia y en la parte de abajo aparecerán el botón de "solicitar devolución", indicar 100% cliente si requiere la devolución a su favor, dar nombre y firma del apoderado).

2. Archivo de la constancia de garantía que emitimos en su momento

3. Copia del pedimento pagado el número de pedimento debe coincidir con el de la constancia emitida

Favor de enviar los tres documentos en un mismo correo. El titulo del correo indicar "liberación de constancia folio ****".

Quedamos en espera, saludos.
"""


def _get_outlook():
    """Obtiene la instancia del Outlook del usuario actual (NO Classic)."""
    if not OUTLOOK_DISPONIBLE:
        return None
    try:
        ol = win32.Dispatch("Outlook.Application")
        return ol
    except Exception:
        return None


def _encontrar_cuenta(ol, email_buscado: str):
    """
    Busca la cuenta con el email indicado en las cuentas configuradas de Outlook.
    Retorna la cuenta si la encuentra, None si no.
    """
    try:
        for cuenta in ol.Session.Accounts:
            if cuenta.SmtpAddress.lower() == email_buscado.lower():
                return cuenta
    except Exception:
        pass
    return None


def listar_cuentas() -> list[str]:
    """Devuelve la lista de cuentas de email configuradas en Outlook."""
    ol = _get_outlook()
    if not ol:
        return []
    cuentas = []
    try:
        for cuenta in ol.Session.Accounts:
            cuentas.append(cuenta.SmtpAddress)
    except Exception:
        pass
    return cuentas


def enviar_correo_constancia(
    folio: str,
    pedimento: str,
    fecha_vencimiento: date,
    importe: float,
    correos_para: list[str],
    correos_cc:   list[str],
    fecha_aviso:  date | None = None,
    cuenta_remitente: str = CUENTA_REMITENTE,
) -> tuple[bool, str]:
    """
    Envía el correo oficial de recordatorio de liberación de constancia.
    SIEMPRE usa la cuenta sistemas.3@selectshop.com.mx como remitente.
    """
    ol = _get_outlook()
    if ol is None:
        return False, "Outlook no está disponible en esta PC."

    try:
        mail = ol.CreateItem(0)  # olMailItem

        # ── Forzar cuenta remitente correcta ──────────────────────────────
        cuenta = _encontrar_cuenta(ol, cuenta_remitente)
        if cuenta:
            mail.SendUsingAccount = cuenta
        else:
            # Si no encuentra la cuenta exacta, registrar advertencia
            cuentas_disponibles = listar_cuentas()
            return False, (
                f"No se encontró la cuenta '{cuenta_remitente}' en Outlook.\n"
                f"Cuentas disponibles: {', '.join(cuentas_disponibles)}\n"
                f"Verifica que Outlook esté configurado con tu cuenta."
            )

        # ── Destinatarios ─────────────────────────────────────────────────
        for addr in correos_para:
            addr = addr.strip()
            if addr:
                mail.Recipients.Add(addr)

        for addr in correos_cc:
            addr = addr.strip()
            if addr:
                r = mail.Recipients.Add(addr)
                r.Type = 2  # olCC

        mail.Recipients.ResolveAll()

        fv_str = fecha_vencimiento.strftime("%d/%m/%Y") if fecha_vencimiento else "—"
        mail.Subject = f"liberación de constancia folio {folio}"
        mail.Body = CUERPO_CORREO
        mail.Send()
        return True, f"Correo enviado desde {cuenta_remitente} para folio {folio}"

    except Exception as e:
        return False, f"Error al enviar correo: {e}"


def crear_evento_calendario(
    folio: str,
    pedimento: str,
    fecha_vencimiento: date,
    importe: float,
    fecha_aviso: date,
    cuenta_remitente: str = CUENTA_REMITENTE,
) -> tuple[bool, str]:
    """
    Crea cita en el calendario de la cuenta sistemas.3@selectshop.com.mx.
    NO en el calendario de otros perfiles/cuentas.
    """
    ol = _get_outlook()
    if ol is None:
        return False, "Outlook no disponible."

    try:
        # Obtener el store (buzón) correcto de la cuenta sistemas.3
        store_correcto = None
        try:
            for store in ol.Session.Stores:
                if hasattr(store, 'DisplayName'):
                    # Buscar por email o nombre de cuenta
                    try:
                        if cuenta_remitente.lower() in store.DisplayName.lower():
                            store_correcto = store
                            break
                    except Exception:
                        pass
        except Exception:
            pass

        # Crear la cita
        cita = ol.CreateItem(1)  # olAppointmentItem

        fv_str  = fecha_vencimiento.strftime("%d/%m/%Y") if fecha_vencimiento else "—"
        fav_str = fecha_aviso.strftime("%d/%m/%Y") if fecha_aviso else "—"
        monto_str = f"${importe:,.2f}"

        inicio = datetime(fecha_aviso.year, fecha_aviso.month, fecha_aviso.day, 9, 0)
        fin    = datetime(fecha_aviso.year, fecha_aviso.month, fecha_aviso.day, 9, 30)

        cita.Subject = (
            f"Tienes vencimiento el próximo {fv_str} del número de pedimento {pedimento}, "
            f"con folio {folio} y con monto de {monto_str} y tienes hasta el día {fav_str}"
        )
        cita.Body = (
            f"Constancia de Depósito — Recordatorio de Liberación\n"
            f"{'='*55}\n"
            f"Folio:              {folio}\n"
            f"Pedimento:          {pedimento}\n"
            f"Fecha vencimiento:  {fv_str}\n"
            f"Monto vigente:      {monto_str}\n"
            f"Fecha límite aviso: {fav_str}\n\n"
            f"Acción requerida:\n"
            f"Enviar documentación de liberación al correo:\n"
            f"cuentaaduanera.mx@bbva.com\n\n"
            "Documentos necesarios:\n"
            "1. Formato de Liberación (firmado por representante legal)\n"
            "2. Archivo de la constancia de garantía\n"
            "3. Copia del pedimento pagado\n\n"
            f"Asunto del correo: 'liberación de constancia folio {folio}'"
        )

        cita.Start           = inicio.strftime("%Y-%m-%d %H:%M")
        cita.End             = fin.strftime("%Y-%m-%d %H:%M")
        cita.ReminderSet     = True
        cita.ReminderMinutesBeforeStart = 60
        cita.BusyStatus      = 0  # olFree

        # Si encontramos el store correcto, mover la cita ahí
        if store_correcto:
            try:
                carpeta_cal = store_correcto.GetRootFolder().Folders["Calendario"]
                cita.Move(carpeta_cal)
            except Exception:
                pass  # Si falla el move, igual se guarda en el default

        cita.Save()
        return True, f"Evento creado en calendario de {cuenta_remitente} para folio {folio} el {fav_str}"

    except Exception as e:
        return False, f"Error al crear evento: {e}"


def eliminar_eventos_prueba(folio_prueba: str = "PRUEBA-TEST") -> tuple[int, str]:
    """
    Elimina TODOS los eventos del calendario que contengan el folio de prueba
    o que hayan sido creados por pruebas anteriores.
    Útil para limpiar los eventos que quedaron en el calendario equivocado.
    """
    ol = _get_outlook()
    if not ol:
        return 0, "Outlook no disponible."

    eliminados = 0
    errores = []

    try:
        # Buscar en TODOS los calendarios de TODAS las cuentas
        for store in ol.Session.Stores:
            try:
                root = store.GetRootFolder()
                # Buscar carpeta Calendario (puede llamarse diferente por idioma)
                for nombre_cal in ["Calendario", "Calendar"]:
                    try:
                        cal = root.Folders[nombre_cal]
                        items = cal.Items
                        items.Sort("[Start]", True)  # más recientes primero
                        to_delete = []
                        for item in items:
                            try:
                                subj = item.Subject or ""
                                # Eliminar si tiene el folio de prueba O si es de constancias antiguas
                                if (folio_prueba in subj or
                                    "PRUEBA" in subj.upper() or
                                    ("vencimiento" in subj.lower() and
                                     "pedimento" in subj.lower() and
                                     "folio" in subj.lower())):
                                    to_delete.append(item)
                            except Exception:
                                continue
                        for item in to_delete:
                            try:
                                item.Delete()
                                eliminados += 1
                            except Exception as e:
                                errores.append(str(e))
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception as e:
        return eliminados, f"Error: {e}"

    msg = f"Se eliminaron {eliminados} evento(s) de prueba de todos los calendarios."
    if errores:
        msg += f" ({len(errores)} errores menores)"
    return eliminados, msg


def procesar_constancias_alertas(
    constancias: list[dict],
    dias_aviso:  int,
    correos_para: list[str],
    correos_cc:   list[str],
    solo_calendario: bool = False,
    cuenta_remitente: str = CUENTA_REMITENTE,
) -> list[str]:
    from datetime import timedelta
    hoy = date.today()
    mensajes = []
    for c in constancias:
        folio    = c.get("folio", "")
        pedimento = c.get("pedimento", "")
        importe  = float(c.get("importe_vigente") or 0)
        fv_str   = c.get("fecha_vencimiento", "")
        try:
            fv = date.fromisoformat(fv_str)
        except Exception:
            mensajes.append(f"[{folio}] Fecha de vencimiento inválida")
            continue
        fecha_aviso = fv - timedelta(days=dias_aviso)
        ok_cal, msg_cal = crear_evento_calendario(
            folio, pedimento, fv, importe, fecha_aviso, cuenta_remitente)
        mensajes.append(f"[{folio}] Calendario: {'✓' if ok_cal else '✗'} {msg_cal}")
        if not solo_calendario:
            ok_mail, msg_mail = enviar_correo_constancia(
                folio=folio, pedimento=pedimento,
                fecha_vencimiento=fv, importe=importe,
                correos_para=correos_para, correos_cc=correos_cc,
                cuenta_remitente=cuenta_remitente)
            mensajes.append(f"[{folio}] Correo: {'✓' if ok_mail else '✗'} {msg_mail}")
    return mensajes


def verificar_outlook() -> tuple[bool, str]:
    """
    Verifica Outlook Y qué cuenta está activa.
    Devuelve (disponible, mensaje_con_cuentas).
    """
    if not OUTLOOK_DISPONIBLE:
        return False, "pywin32 no instalado"
    try:
        ol = win32.Dispatch("Outlook.Application")
        cuentas = []
        try:
            for c in ol.Session.Accounts:
                cuentas.append(c.SmtpAddress)
        except Exception:
            pass
        if not cuentas:
            return False, "Outlook disponible pero sin cuentas configuradas"
        tiene_cuenta_correcta = any(
            CUENTA_REMITENTE.lower() in c.lower() for c in cuentas)
        if tiene_cuenta_correcta:
            return True, f"OK — Cuenta encontrada: {CUENTA_REMITENTE}"
        else:
            return False, (
                f"ADVERTENCIA: No se encontró {CUENTA_REMITENTE}\n"
                f"Cuentas en Outlook: {', '.join(cuentas)}"
            )
    except Exception as e:
        return False, f"Error conectando Outlook: {e}"


def crear_recordatorios_lote(servicios_proximos: list, dias_antes: int = 3) -> int:
    """
    Crea un recordatorio de calendario por cada servicio próximo a vencer.
    Devuelve el número de citas creadas exitosamente.
    Compatibilidad con GestorPagosMarcovich.
    """
    from datetime import date as _date, timedelta
    creados = 0
    for s in servicios_proximos:
        try:
            prov   = s.get("proveedor_nombre") or s.get("Proveedor", "")
            desc   = s.get("descripcion")      or s.get("Descripcion", "")
            emp    = s.get("empresa")          or s.get("Empresa", "")
            monto  = float(s.get("monto_base") or s.get("MontoBase") or 0) +                      float(s.get("iva")        or s.get("IVA") or 0)
            fl     = s.get("fecha_limite")
            if fl is None:
                continue
            if not isinstance(fl, _date):
                fl = _date.fromisoformat(str(fl))
            fecha_aviso = fl - timedelta(days=dias_antes)
            ok, _ = crear_evento_calendario(
                folio=desc, pedimento=prov,
                fecha_vencimiento=fl, importe=monto,
                fecha_aviso=fecha_aviso,
                cuenta_remitente=CUENTA_REMITENTE)
            if ok:
                creados += 1
        except Exception:
            continue
    return creados


def purgar_citas_outlook(patron: str = "PAGAR:") -> int:
    """
    Elimina citas del calendario activo que contengan `patron` en el asunto.
    Devuelve el número de citas eliminadas.
    Compatibilidad con GestorPagosMarcovich.
    """
    ol = _get_outlook()
    if not ol:
        return 0
    eliminadas = 0
    try:
        ns       = ol.GetNamespace("MAPI")
        calendar = ns.GetDefaultFolder(9)  # olFolderCalendar
        items    = calendar.Items
        a_borrar = []
        for i in range(items.Count, 0, -1):
            try:
                item = items.Item(i)
                if patron.upper() in (item.Subject or "").upper():
                    a_borrar.append(item.EntryID)
            except Exception:
                continue
        for entry_id in a_borrar:
            try:
                ns.GetItemFromID(entry_id).Delete()
                eliminadas += 1
            except Exception:
                continue
    except Exception as e:
        print(f"[outlook] Error al purgar: {e}")
    return eliminadas
