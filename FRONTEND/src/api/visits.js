// src/api/visits.js
import api from "./auth";

/** Serializa el payload desde el form que usas en VisitsPage.jsx */
export function serializeVisitPayload({
  visitor_full_name,
  visitor_doc_type,
  visitor_doc_number,
  visitor_phone,
  unit,
  host_resident,
  vehicle_plate,
  purpose,
  scheduled_for,
  notes,
}) {
  const visitor = {
    full_name: visitor_full_name?.trim(),
    doc_type: visitor_doc_type || "CI",
    doc_number: String(visitor_doc_number || "").trim(),
    phone: (visitor_phone || "").trim(),
  };
  const body = {
    visitor,
    unit,
    host_resident,
    vehicle_plate: (vehicle_plate || "").toUpperCase(),
    purpose: purpose || "",
    notes: notes || "",
  };
  if (scheduled_for) body.scheduled_for = scheduled_for; // ISO string
  return body;
}

/** Builder de querystring que ya usas en VisitsPage.jsx */
export function buildVisitQuery({
  q,
  status,
  unit,
  host_resident,
  approval_status,
  ordering,
  page = 1,
  page_size = 50,
  mine,
} = {}) {
  const params = {};
  if (q) params.search = q;
  if (status) params.status = status;
  if (unit) params.unit = unit;
  if (host_resident) params.host_resident = host_resident;
  if (approval_status) params.approval_status = approval_status;
  if (ordering) params.ordering = ordering;
  if (page) params.page = page;
  if (page_size) params.page_size = page_size;
  if (mine) params.mine = 1;
  return params;
}

// -------- CRUD base --------
export async function listVisits(params) {
  const { data } = await api.get("visits/", { params });
  return data;
}
export async function getVisit(id) {
  const { data } = await api.get(`visits/${id}/`);
  return data;
}
export async function createVisit(payload) {
  const { data } = await api.post("visits/", payload);
  return data;
}
export async function updateVisit(id, payload) {
  const { data } = await api.patch(`visits/${id}/`, payload);
  return data;
}
export async function deleteVisit(id) {
  await api.delete(`visits/${id}/`);
}

// -------- Acciones de flujo (portería) --------
export async function enterVisit(id, { force = false } = {}) {
  const { data } = await api.post(`visits/${id}/enter/`, { force });
  return data;
}
export async function exitVisit(id) {
  const { data } = await api.post(`visits/${id}/exit/`);
  return data;
}
export async function cancelVisit(id) {
  const { data } = await api.post(`visits/${id}/cancel/`);
  return data;
}
export async function denyVisit(id) {
  const { data } = await api.post(`visits/${id}/deny/`);
  return data;
}

// -------- Aprobación (residente) --------
export async function approveVisit(id, { hours_valid = 24 } = {}) {
  const { data } = await api.post(`visits/${id}/approve/`, { hours_valid });
  return data;
}
export async function denyApproval(id, { reason = "" } = {}) {
  const { data } = await api.post(`visits/${id}/deny-approval/`, { reason });
  return data;
}

// -------- Helpers para páginas --------
export async function listResidentPending() {
  // mine=1 (sólo mis visitas como anfitrión) + approval_status=PEND
  const params = buildVisitQuery({
    mine: true,
    approval_status: "PEND",
    ordering: "-created_at",
    page_size: 100,
  });
  return listVisits(params);
}

export function approvalBadgeClass(ap) {
  if (!ap) return "badge--neutral";
  const s = String(ap).toLowerCase();
  if (s === "apr") return "badge--success";
  if (s === "pend") return "badge--warn";
  if (s === "den" || s === "exp") return "badge--danger";
  return "badge--neutral";
}
