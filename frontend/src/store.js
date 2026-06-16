// Estado simple persistido en localStorage (firmantes que perduran entre sesiones).
import { useState, useEffect } from "react";

const FIRMANTES_KEY = "gestorpagos.firmantes";

export const FIRMANTES_DEFAULT = {
  analista_nombre: "",
  gerente_nombre: "",
  visto_bno: "",
  depto_finanzas: "",
  dir_financiera: "",
  dir_general: "",
};

export function loadFirmantes() {
  try {
    return { ...FIRMANTES_DEFAULT, ...JSON.parse(localStorage.getItem(FIRMANTES_KEY) || "{}") };
  } catch {
    return { ...FIRMANTES_DEFAULT };
  }
}

export function saveFirmantes(f) {
  localStorage.setItem(FIRMANTES_KEY, JSON.stringify(f));
}

// Hook genérico ligado a localStorage
export function usePersistentState(key, initial) {
  const [val, setVal] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(val));
  }, [key, val]);
  return [val, setVal];
}

export const MESES = [
  "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
