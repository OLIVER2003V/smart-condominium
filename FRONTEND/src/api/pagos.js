// src/api/pagos.js
const RAW_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/";
const BASE = RAW_BASE.endsWith("/") ? RAW_BASE : RAW_BASE + "/";

// Helper para unir paths sin duplicar slash
const u = (path) => `${BASE}${path}`; // path sin slash inicial

// Headers con token
function authHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Token ${token}` } : {}),
  };
}

// parseo seguro de errores JSON
async function safeJson(res) {
  try { return await res.json(); } catch { return { detail: res.statusText || "Error" }; }
}

// helper de querystring (omite null/undefined/"")
function qs(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.append(k, v);
  });
  const s = q.toString();
  return s ? `?${s}` : "";
}

/**
 * LISTAR PAGOS (con filtros / ordering / paginación)
 * Filtros soportados por tu PagoViewSet:
 *   cuota, valido, medio
 * Ordering soportado (por defecto en el viewset): created_at desc
 *
 * Usa pageUrl si pasas DRF next absoluto; si no, arma URL con params.
 */
export async function listPagos(params = {}, pageUrl) {
  const url = pageUrl || (u("pagos/") + qs({
    page: params.page,
    page_size: params.page_size,
    cuota: params.cuota,
    valido: params.valido,
    medio: params.medio,      // "EFECTIVO" | "TRANSFERENCIA" | "TARJETA" | "ONLINE_STRIPE" | "OTRO"
    ordering: params.ordering // ej: "-created_at"
  }));

  const res = await fetch(url, { headers: authHeaders() });
  const data = await safeJson(res);
  if (!res.ok) throw data;
  return data; // {results, count, next, previous} ó lista
}

/** GET detalle de un pago */
export async function getPago(id) {
  const res = await fetch(u(`pagos/${id}/`), { headers: authHeaders() });
  const data = await safeJson(res);
  if (!res.ok) throw data;
  return data;
}

/**
 * CREAR PAGO DIRECTO (POST /pagos/)
 * Usa el serializer PagoCreateSerializer base.
 * payload esperado:
 *   {
 *     cuota: <id>,            // requerido
 *     monto: "50.00",         // requerido (> 0 y <= saldo)
 *     medio: "EFECTIVO",      // default EFECTIVO si no envías
 *     referencia: "CAJA-001"  // opcional (si envías, debe ser única por medio)
 *   }
 *
 * Nota: también puedes pagar por la ruta de cuota (/cuotas/:id/pagos/).
 */
export async function createPago(payload) {
  const res = await fetch(u("pagos/"), {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await safeJson(res);
  if (!res.ok) throw data;
  return data; // pago serializado
}

/**
 * INICIAR PAGO ONLINE (Stripe) – POST /pay/online/init/
 * payload:
 *   { cuota: <id>, amount: "10.50" }   // también acepta { cuota_id: <id> }
 *
 * Respuesta:
 *   { client_secret, provisional: { online_payment_id, intent_id, amount, currency, status } }
 */
export async function iniciarPagoOnline(cuotaId, amount) {
  const res = await fetch(u("pay/online/init/"), {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ cuota: cuotaId, amount }),
  });
  const data = await safeJson(res);
  if (!res.ok) throw data;
  return data;
}
