import { useState } from "react";
import { faceIdentify } from "../api/face";

export default function FaceIdentify() {
  const [cameraId, setCameraId] = useState("PT-01");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [out, setOut] = useState(null);
  const [err, setErr] = useState("");

  function onFile(e) {
    const f = e.target.files?.[0];
    setFile(f || null);
    setPreview(f ? URL.createObjectURL(f) : "");
  }

  async function onSubmit(e) {
    e.preventDefault();
    setErr("");
    setOut(null);
    if (!file) {
      setErr("Selecciona una foto.");
      return;
    }
    setLoading(true);
    try {
      const data = await faceIdentify({ camera_id: cameraId, file });
      setOut(data);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  const scorePct = out?.best?.Similarity
    ? `${(out.best.Similarity).toFixed(2)}%`
    : out?.event?.score
    ? `${(out.event.score * 100).toFixed(2)}%`
    : "-";

  const decision = out?.event?.decision || (out?.match ? "ALLOW_RESIDENT" : "DENY_UNKNOWN");

  return (
    <div className="p-6 max-w-xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Identificar rostro (bitácora)</h1>

      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block">
          <span className="text-sm">Cámara</span>
          <input
            className="border rounded w-full px-3 py-2"
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            placeholder="PT-01"
          />
        </label>

        <label className="block">
          <span className="text-sm">Foto</span>
          <input type="file" accept="image/*" onChange={onFile} />
        </label>

        {preview && (
          <img src={preview} alt="preview" className="max-h-64 rounded border" />
        )}

        <button
          className="px-4 py-2 rounded bg-green-600 text-white disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Procesando..." : "Identificar"}
        </button>
      </form>

      {err && <p className="text-red-600 text-sm">Error: {err}</p>}

      {out && (
        <div className="space-y-2">
          <div className="p-3 rounded border">
            <p><b>match</b>: {String(out.match)}</p>
            <p><b>decision</b>: {decision}</p>
            <p><b>similaridad</b>: {scorePct}</p>
            <p><b>matched_id</b>: {out?.best?.ExternalImageId || out?.event?.reason || "-"}</p>
            {out?.event?.snapshot && (
              <div className="mt-2">
                <b>snapshot</b>:
                <a className="text-blue-600 underline"
                   href={`${import.meta.env.VITE_API_BASE}${out.event.snapshot}`}
                   target="_blank" rel="noreferrer">ver</a>
              </div>
            )}
          </div>

          <details className="bg-gray-50 p-3 rounded">
            <summary className="cursor-pointer">Respuesta completa</summary>
            <pre className="text-xs overflow-auto">
              {JSON.stringify(out, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}
