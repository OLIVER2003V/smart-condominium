import { useState } from "react";
import { faceRegister } from "../api/face";

export default function FaceEnroll() {
  const [objId, setObjId] = useState("");
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
    if (!file || !objId) {
      setErr("Selecciona una foto y escribe el ID del residente.");
      return;
    }
    setLoading(true);
    try {
      const data = await faceRegister({ kind: "resident", obj_id: objId, file });
      setOut(data);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-xl mx-auto space-y-4">
      <h1 className="text-2xl font-semibold">Enrolar rostro (AWS Rekognition)</h1>

      <form onSubmit={onSubmit} className="space-y-3">
        <label className="block">
          <span className="text-sm">ID de residente (obj_id)</span>
          <input
            className="border rounded w-full px-3 py-2"
            value={objId}
            onChange={(e) => setObjId(e.target.value)}
            placeholder="31"
          />
        </label>

        <label className="block">
          <span className="text-sm">Foto (frontal, buena luz)</span>
          <input type="file" accept="image/*" onChange={onFile} />
        </label>

        {preview && (
          <img src={preview} alt="preview" className="max-h-64 rounded border" />
        )}

        <button
          className="px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-50"
          disabled={loading}
        >
          {loading ? "Enviando..." : "Enrolar"}
        </button>
      </form>

      {err && <p className="text-red-600 text-sm">Error: {err}</p>}

      {out && (
        <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">
          {JSON.stringify(out, null, 2)}
        </pre>
      )}
    </div>
  );
}
