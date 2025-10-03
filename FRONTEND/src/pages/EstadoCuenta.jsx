// src/pages/EstadoCuentaPage.jsx
import { useEffect, useMemo, useState } from "react";

/* ========= Helpers mínimos (borra si ya tienes estos) ========= */
const API_BASE = import.meta.env.VITE_API_BASE;
const STATIC_TOKEN = import.meta.env.VITE_API_STATIC_TOKEN;

function getToken() {
  return localStorage.getItem("authToken") || STATIC_TOKEN || "";
}

async function apiJson(path, { method = "GET", body, headers = {} } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Token ${getToken()}` } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof data === "string" ? data : data?.detail || JSON.stringify(data);
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return data;
}
/* =============================================================== */

/* ========== API específicas de esta página ========== */
async function listCuotas({ pageUrl } = {}) {
  // Soporta paginación del backend (DRF): si viene pageUrl, úsala directamente
  const url = pageUrl ?? `/api/cuotas/?mine=1&ordering=vencimiento`;
  return apiJson(url.startsWith("http") ? url.replace(API_BASE, "") : url);
}

async function createCheckout({ cuotaId, medio = "QR" }) {
  return apiJson(`/api/pagos/mock/checkout/`, {
    method: "POST",
    body: { cuota: cuotaId, medio },
  });
}
/* ===================================================== */

/* ========== Modal QR interno (simple, sin libs) ========== */
function QrDialog({ open, onClose, payload, confirmationUrl }) {
  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose?.(); }
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="qr-backdrop" onClick={onClose}>
      <div className="qr-card" onClick={(e) => e.stopPropagation()}>
        <h3>Pago por QR</h3>
        <p>Escanea o copia el contenido:</p>
        <code className="qr-code">{payload}</code>

        <div className="qr-actions">
          <a className="btn" href={confirmationUrl} target="_blank" rel="noreferrer">
            Abrir página de pago
          </a>
          <button className="btn btn-sec" onClick={onClose}>Cerrar</button>
        </div>
      </div>
      <style>{`
        .qr-backdrop{position:fixed;inset:0;background:#0008;display:flex;align-items:center;justify-content:center;z-index:999}
        .qr-card{background:#fff;padding:16px 18px;border-radius:12px;min-width:340px;max-width:680px;box-shadow:0 10px 30px #0002}
        .qr-code{display:block;word-break:break-all;background:#f7f7f7;border:1px dashed #ddd;border-radius:8px;padding:10px;margin:8px 0}
        .qr-actions{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
        .btn{padding:8px 12px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer;text-decoration:none}
        .btn-sec{background:#f3f3f3}
      `}</style>
    </div>
  );
}
/* ========================================================= */

/* ================== Página ================== */
export default function EstadoCuenta() {
  const [rows, setRows] = useState([]);
  const [nextUrl, setNextUrl] = useState(null);
  const [prevUrl, setPrevUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // Modal QR
  const [qrOpen, setQrOpen] = useState(false);
  const [qrPayload, setQrPayload] = useState("");
  const [qrConfirmUrl, setQrConfirmUrl] = useState("");

  const totalSaldo = useMemo(
    () => (rows || []).reduce((acc, c) => acc + Number(c?.saldo ?? 0), 0),
    [rows]
  );

  async function fetchPage(pageUrl) {
    setLoading(true);
    setErr("");
    try {
      const data = await listCuotas({ pageUrl });
      const items = data.results ?? data; // DRF paginado o lista simple
      setRows(items);
      setNextUrl(data.next || null);
      setPrevUrl(data.previous || null);
    } catch (e) {
      console.error(e);
      setErr(e.message);
      setRows([]);
      setNextUrl(null);
      setPrevUrl(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchPage(); }, []);

  async function onPagar(cuotaId) {
    try {
      const intent = await createCheckout({ cuotaId, medio: "QR" });
      // Backend devuelve confirmation_url y (si QR) qr_payload (mismo link)
      setQrPayload(intent.qr_payload || intent.confirmation_url);
      setQrConfirmUrl(intent.confirmation_url);
      setQrOpen(true);
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <div className="ec-wrap">
      <header className="ec-header">
        <h2>Estado de cuenta</h2>
        <div className="ec-summary">
          <span>Total saldo: </span>
          <b>{totalSaldo.toFixed(2)}</b>
        </div>
      </header>

      {err ? <div className="ec-error">⚠️ {err}</div> : null}
      {loading ? (
        <div className="ec-skel">
          <div className="sk-row" /><div className="sk-row" /><div className="sk-row" />
        </div>
      ) : (
        <div className="ec-card">
          <table className="ec-table">
            <thead>
              <tr>
                <th>Periodo</th>
                <th>Concepto</th>
                <th>Monto</th>
                <th>Pagado</th>
                <th>Saldo</th>
                <th>Vencimiento</th>
                <th>Estado</th>
                <th style={{width:100}}>Acción</th>
              </tr>
            </thead>
            <tbody>
              {(rows || []).length === 0 ? (
                <tr><td colSpan={8} style={{textAlign:"center",padding:"14px"}}>Sin cuotas</td></tr>
              ) : (rows || []).map((c) => (
                <tr key={c.id}>
                  <td>{c.periodo}</td>
                  <td>{c.concepto}</td>
                  <td>{Number(c.monto_base).toFixed(2)}</td>
                  <td>{Number(c.pagado ?? 0).toFixed(2)}</td>
                  <td>{Number(c.saldo ?? 0).toFixed(2)}</td>
                  <td>{c.vencimiento ?? "-"}</td>
                  <td>{c.estado}</td>
                  <td>
                    {Number(c.saldo) > 0 ? (
                      <button className="btn btn-pay" onClick={() => onPagar(c.id)}>Pagar (QR)</button>
                    ) : <span className="ec-badge">Pagada</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="ec-pager">
            <button className="btn" disabled={!prevUrl} onClick={() => fetchPage(prevUrl)}>« Anterior</button>
            <button className="btn" disabled={!nextUrl} onClick={() => fetchPage(nextUrl)}>Siguiente »</button>
            <button className="btn btn-sec" onClick={() => fetchPage()}>Recargar</button>
          </div>
        </div>
      )}

      <QrDialog
        open={qrOpen}
        onClose={() => setQrOpen(false)}
        payload={qrPayload}
        confirmationUrl={qrConfirmUrl}
      />

      <style>{`
        .ec-wrap{max-width:1100px;margin:0 auto;padding:10px}
        .ec-header{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}
        .ec-summary{display:flex;gap:6px;align-items:center}
        .ec-error{background:#fff3f3;border:1px solid #ffd3d3;padding:10px;border-radius:10px;margin-bottom:10px}
        .ec-card{background:#fff;border:1px solid #eee;border-radius:12px;box-shadow:0 6px 20px #0000000a;padding:12px}
        .ec-table{width:100%;border-collapse:collapse}
        .ec-table th,.ec-table td{border-bottom:1px solid #f0f0f0;padding:8px;text-align:left}
        .ec-table thead th{font-size:13px;color:#666}
        .ec-pager{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}
        .btn{padding:8px 12px;border:1px solid #ddd;border-radius:8px;background:#fff;cursor:pointer}
        .btn-pay{background:#f7fff7;border-color:#cfe8cf}
        .btn-sec{background:#f6f6f6}
        .ec-badge{display:inline-block;padding:4px 8px;border:1px solid #e8e8e8;border-radius:999px;font-size:12px;color:#666}
        .ec-skel .sk-row{height:42px;background:linear-gradient(90deg,#f5f5f5,#ededed,#f5f5f5);background-size:200% 100%;animation:sk 1.2s infinite}
        @keyframes sk{0%{background-position:200% 0}100%{background-position:-200% 0}}
      `}</style>
    </div>
  );
}
