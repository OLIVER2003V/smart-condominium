// src/api/face.js
import api from "./auth"; // ← usa el axios ya configurado con baseURL y token

async function postMultipart(path, fields) {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));

  // IMPORTANTE: no pongas slash inicial si tu baseURL termina en /api/
  const { data } = await api.post(path, fd, {
    headers: { "Content-Type": "multipart/form-data" }, // el boundary lo pone el navegador
  });
  return data;
}

export function faceRegister({ kind, obj_id, file }) {
  // auth.js tiene baseURL = http://127.0.0.1:8000/api/
  // así que aquí solo pasamos el path relativo a /api/
  return postMultipart("face/register-aws/", { kind, obj_id, image: file });
}

export function faceIdentify({ camera_id, file }) {
  return postMultipart("face/identify-and-log-aws/", { camera_id, image: file });
}
