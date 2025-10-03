// src/api/payments.js
import { apiJson, apiMultipart } from "./auth";

// CU11 - crear intento (QR/CARD)
export function createCheckout({ cuotaId, medio = "QR" }) {
  return apiJson("/api/pagos/mock/checkout/", {
    method: "POST",
    body: { cuota: cuotaId, medio },
  });
}

// (Opcional) listar intents del usuario (si tienes endpoint de dashboard)
export function listMyIntents() {
  return apiJson("/api/pagos/mock/intents/dashboard/");
}

// Subir comprobante del intent
export function uploadReceipt({ intent, amount, reference, bank_name, file, receipt_url }) {
  const fd = new FormData();
  fd.append("intent", intent);
  if (amount) fd.append("amount", amount);
  if (reference) fd.append("reference", reference);
  if (bank_name) fd.append("bank_name", bank_name);
  if (receipt_url) fd.append("receipt_url", receipt_url);
  if (file) fd.append("receipt_file", file);
  return apiMultipart("/api/pagos/mock/receipt/", fd);
}

// Verificar (admin/staff)
export function verifyReceipt({ receipt_id, approve }) {
  return apiJson("/api/pagos/mock/verify/", {
    method: "POST",
    body: { receipt_id, approve: !!approve },
  });
}
