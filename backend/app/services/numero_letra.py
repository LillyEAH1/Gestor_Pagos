"""Importe en número -> letra (M.N.). Portado 1:1 de v60/numero_letra.py."""


def numero_a_letra(monto: float) -> str:
    unidades = ["", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE",
                "DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS",
                "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA",
               "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS",
                "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

    def _c(n):
        if n == 100:
            return "CIEN"
        if n == 0:
            return ""
        c = centenas[n // 100]
        r = n % 100
        if r == 0:
            return c
        mid = unidades[r] if r < 20 else decenas[r // 10] + (" Y " + unidades[r % 10] if r % 10 else "")
        return (c + " " if c else "") + mid

    def _m(n):
        if n < 1000:
            return _c(n)
        pre = "MIL" if n // 1000 == 1 else _c(n // 1000) + " MIL"
        return pre + (" " + _c(n % 1000) if n % 1000 else "")

    entero = int(monto)
    cents = round((monto - entero) * 100)
    if entero == 0:
        letra = "CERO"
    elif entero < 1_000_000:
        letra = _m(entero)
    else:
        mm = entero // 1_000_000
        r = entero % 1_000_000
        letra = ("UN MILLÓN" if mm == 1 else _m(mm) + " MILLONES") + (" " + _m(r) if r else "")
    return f"{letra} {cents:02d}/100 M.N."
