// src/components/QrDialog.jsx
import { useEffect } from "react";

export default function QrDialog({ open, onClose, payload, confirmationUrl }) {
  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose?.(); }
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="qr-backdrop">
      <div className="qr-card">
        <h3>Escanea el QR</h3>
        <p>Contenido:</p>
        <code style={{ wordBreak: "break-all" }}>{payload}</code>

        <div style={{ marginTop: 12 }}>
          <a className="btn" href={confirmationUrl} target="_blank" rel="noreferrer">
            Abrir página de pago
          </a>
          <button className="btn btn-sec" onClick={onClose}>Cerrar</button>
        </div>
      </div>
      <style>{`
        .qr-backdrop { position:fixed; inset:0; background:#0008; display:flex; align-items:center; justify-content:center; z-index:999; }
        .qr-card { background:#fff; padding:16px; border-radius:10px; min-width: 320px; max-width: 600px; }
        .btn { display:inline-block; margin-right:8px; padding:8px 12px; border-radius:8px; border:1px solid #ddd; text-decoration:none; }
        .btn-sec { background:#f2f2f2; }
      `}</style>
    </div>
  );
}
