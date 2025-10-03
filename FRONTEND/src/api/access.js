// src/api/access.js
const RAW_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/";
const BASE = RAW_BASE.endsWith("/") ? RAW_BASE : RAW_BASE + "/";
const u = (p) => `${BASE}${p}`;

// Headers JSON con token (para endpoints JSON)
function authHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Token ${token}` } : {}),
  };
}

// Headers para multipart (NO forzar Content-Type; el navegador pone el boundary)
function authHeadersMultipart() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Token ${token}` } : {};
}

async function safeJson(res) {
  try { return await res.json(); } catch { return { detail: res.statusText || "Error" }; }
}

// ---------------------------------------------
//  Snapshot (Plate Recognizer) - BACKEND proxy
// ---------------------------------------------

/**
 * Envía una imagen a /api/access/snapshot-check/ (requiere token).
 * @param {File|Blob} file
 * @param {{camera_id?: string, gate_id?: number}} opts
 * @returns {Promise<{
 *   decision: "ALLOW_RESIDENT"|"ALLOW_VISIT"|"DENY_UNKNOWN"|"ERROR_OCR",
 *   reason: string, plate: string, score: number|null, opened: boolean,
 *   vehicle_id?: number, owner_id?: number, unit_id?: number|null,
 *   visit_id?: number, host_id?: number
 * }>}
 */
export async function snapshotCheck(file, opts = {}) {
  const fd = new FormData();
  if (opts.camera_id) fd.append("camera_id", opts.camera_id);
  if (opts.gate_id !== undefined && opts.gate_id !== null) fd.append("gate_id", String(opts.gate_id));

  // Normaliza a File para que tenga nombre
  const snapFile = file instanceof File ? file : new File([file], "snapshot.jpg", { type: "image/jpeg" });
  fd.append("image", snapFile);

  const r = await fetch(u("access/snapshot-check/"), {
    method: "POST",
    headers: authHeadersMultipart(),
    body: fd,
  });
  const d = await safeJson(r);
  if (!r.ok) throw d;
  return d;
}

/**
 * Ping sin auth (según tu backend actual) para probar el OCR directamente.
 * @param {File|Blob} file
 * @param {{camera_id?: string}} opts
 */
export async function snapshotPing(file, opts = {}) {
  const fd = new FormData();
  if (opts.camera_id) fd.append("camera_id", opts.camera_id);
  const snapFile = file instanceof File ? file : new File([file], "snapshot.jpg", { type: "image/jpeg" });
  fd.append("image", snapFile);

  const r = await fetch(u("access/snapshot-ping/"), {
    method: "POST",
    // sin headers de auth ni Content-Type
    body: fd,
  });
  const d = await safeJson(r);
  if (!r.ok) throw d;
  return d;
}

// ---------------------------------------------
//  Visits helpers (por si usas botones en UI)
// ---------------------------------------------

export async function visitEnter(visitId) {
  const r = await fetch(u(`visits/${visitId}/enter/`), {
    method: "POST",
    headers: authHeaders(),
  });
  const d = await safeJson(r);
  if (!r.ok) throw d;
  return d;
}

export async function visitExit(visitId) {
  const r = await fetch(u(`visits/${visitId}/exit/`), {
    method: "POST",
    headers: authHeaders(),
  });
  const d = await safeJson(r);
  if (!r.ok) throw d;
  return d;
}
