import React, { useRef, useState } from "react";
import { snapshotCheck, visitEnter } from "../api/access";

export default function AccessControl() {
  const videoRef = useRef(null);
  const [streamOn, setStreamOn] = useState(false);
  const [loading, setLoading] = useState(false);
  const [res, setRes] = useState(null);
  const [error, setError] = useState(null);

  const startCam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" }, audio: false
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
        setStreamOn(true);
      }
    } catch (e) {
      setError(e?.message || "No se pudo abrir la cámara");
    }
  };

  const stopCam = () => {
    const s = videoRef.current?.srcObject;
    s?.getTracks().forEach(t => t.stop());
    if (videoRef.current) videoRef.current.srcObject = null;
    setStreamOn(false);
  };

  const captureFrame = async () => {
    const v = videoRef.current;
    if (!v) return null;
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth || 1280;
    canvas.height = v.videoHeight || 720;
    canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
    return await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", 0.9));
  };

  const sendFromCamera = async () => {
    setError(null); setLoading(true); setRes(null);
    try {
      const blob = await captureFrame();
      if (!blob) throw new Error("No se pudo capturar imagen");
      const data = await snapshotCheck(blob, { camera_id: "porteria_norte" });
      setRes(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.detail || e?.message || "Error enviando snapshot");
    } finally {
      setLoading(false);
    }
  };

  const onPickFile = async (ev) => {
    const f = ev.target.files?.[0];
    if (!f) return;
    setError(null); setLoading(true); setRes(null);
    try {
      const data = await snapshotCheck(f, { camera_id: "porteria_norte" });
      setRes(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.detail || e?.message || "Error enviando snapshot");
    } finally {
      setLoading(false);
      ev.target.value = "";
    }
  };

  const handleEnter = async () => {
    if (!res?.visit_id) return;
    try {
      setLoading(true);
      await visitEnter(res.visit_id);
      alert("Entrada registrada");
    } catch (e) {
      alert(e?.response?.data?.detail || e?.detail || e?.message || "No se pudo marcar entrada");
    } finally {
      setLoading(false);
    }
  };

  const color = {
    ALLOW_RESIDENT: "#16a34a",
    ALLOW_VISIT: "#16a34a",
    DENY_UNKNOWN: "#dc2626",
    ERROR_OCR: "#ca8a04",
  }[res?.decision || "ERROR_OCR"] || "#6b7280";

  return (
    <div style={{ maxWidth: 720, margin: "20px auto" }}>
      <h2>Acceso Vehicular (OCR)</h2>

      {/* Cámara */}
      <div>
        <video ref={videoRef} style={{ width: "100%", borderRadius: 8, background: "#000" }} playsInline muted />
        <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
          {!streamOn ? (
            <button onClick={startCam}>Encender cámara</button>
          ) : (
            <button onClick={stopCam} style={{ background: "#dc2626", color: "#fff" }}>Apagar cámara</button>
          )}
          <button disabled={!streamOn || loading} onClick={sendFromCamera}>
            {loading ? "Procesando..." : "Capturar y enviar"}
          </button>
        </div>
      </div>

      {/* Subida manual */}
      <div style={{ marginTop: 12 }}>
        <label>o subir una imagen</label><br />
        <input type="file" accept="image/*" disabled={loading} onChange={onPickFile} />
      </div>

      {/* Mensajes */}
      {error && <div style={{ background: "#fee2e2", color: "#991b1b", padding: 8, borderRadius: 8, marginTop: 8 }}>{String(error)}</div>}

      {res && (
        <div style={{ background: color, color: "#fff", padding: 12, borderRadius: 12, marginTop: 10 }}>
          <div style={{ fontWeight: 700, fontSize: 18 }}>
            {res.decision === "ALLOW_RESIDENT" && "Residente autorizado"}
            {res.decision === "ALLOW_VISIT" && "Visita autorizada"}
            {res.decision === "DENY_UNKNOWN" && "No autorizado"}
            {res.decision === "ERROR_OCR" && "Placa ilegible / baja confianza"}
          </div>
          <div>Placa: <b>{res.plate || "—"}</b> · Score: <b>{res.score ?? "—"}</b> · Barrera: {res.opened ? "Abierta" : "Cerrada"}</div>
          {res.decision === "ALLOW_RESIDENT" && (
            <div style={{ marginTop: 6 }}>
              Vehículo ID: {res.vehicle_id} · Propietario: {res.owner_id} · Unidad: {res.unit_id ?? "—"}
            </div>
          )}
          {res.decision === "ALLOW_VISIT" && (
            <div style={{ marginTop: 6 }}>
              Visita ID: {res.visit_id} · Unidad: {res.unit_id} · Anfitrión: {res.host_id}
              <div style={{ marginTop: 8 }}>
                <button disabled={loading} onClick={handleEnter}>Marcar entrada</button>
              </div>
            </div>
          )}
          <div style={{ marginTop: 6, opacity: 0.9 }}>{res.reason}</div>
        </div>
      )}
    </div>
  );
}
