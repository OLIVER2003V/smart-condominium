import axios from "axios";

const RAW_BASE =
  import.meta.env.VITE_API_BASE ||
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000/api/";
// Normaliza: garantiza que termine en '/'
const BASE = RAW_BASE.endsWith("/") ? RAW_BASE : RAW_BASE + "/";

const LOGIN_PATH = (import.meta.env.VITE_API_LOGIN_PATH || "auth/login/").replace(/^\/+/, "");
const ME_PATH = (import.meta.env.VITE_API_ME_PATH || "auth/me/").replace(/^\/+/, "");
const ME_UPDATE_PATH = (import.meta.env.VITE_API_UPDATE_PATH || "auth/me/update/").replace(/^\/+/, "");
const CHANGE_PASSWORD = "auth/change-password/";

//CLIENTE AXIOS
export const api = axios.create({
  baseURL: BASE,
  headers: { Accept: "application/json", "Content-Type": "application/json" },
  timeout: 15000,
});

//FUNCION TOKEN
export function setAuthToken(token) {
  if (token) {
    localStorage.setItem("token", token);
    api.defaults.headers.common.Authorization = `Token ${token}`;
  } else {
    localStorage.removeItem("token");
    delete api.defaults.headers.common.Authorization;
  }
}

// Si hay token guardado, lo cargamos al iniciar.
const saved = localStorage.getItem("token");
if (saved) setAuthToken(saved);

// 🔎 logea cada request para verificar la URL final (solo en dev)
api.interceptors.request.use((cfg) => {
  if (import.meta.env.DEV) {
    const full = new URL(cfg.url ?? "", cfg.baseURL ?? window.location.origin).toString();
    console.log("[REQUEST]", cfg.method?.toUpperCase(), full, cfg.params || "");
  }
  return cfg;
});

// Limpieza automática si el backend responde 401
api.interceptors.response.use(
  (r) => r,
  (error) => {
    if (error?.response?.status === 401) {
      setAuthToken(null);
      localStorage.removeItem("me");
    }
    return Promise.reject(error);
  }
);

// --- util: traducir errores de DRF a mensajes amigables
export function friendlyLoginError(err) {
  const data = err?.response?.data || {};

  if (data.username?.length) return "El usuario es obligatorio.";
  if (data.password?.length) return "La contraseña es obligatoria.";
  if (Array.isArray(data.non_field_errors) && data.non_field_errors[0]) {
    return "Usuario o contraseña incorrectos.";
  }
  if (typeof data.detail === "string" && data.detail) {
    if (data.detail.toLowerCase().includes("no active")) {
      return "Tu cuenta está inactiva. Contacta al administrador.";
    }
    if (data.detail.toLowerCase().includes("invalid")) {
      return "Datos inválidos. Revisa usuario y contraseña.";
    }
    return data.detail;
  }

  const s = err?.response?.status;
  if (s === 400) return "Datos inválidos. Revisa usuario y contraseña.";
  if (s === 401) return "No autorizado. Verifica tus credenciales.";
  if (s === 403) return "No tienes permisos para realizar esta acción.";
  if (s === 500) return "Error del servidor. Intenta de nuevo más tarde.";

  return "Error al iniciar sesión. Inténtalo de nuevo.";
}

//POST MANDA CREDENCIALES AL ENDPOINT
export async function login(username, password) {
  try {
    const { data, status } = await api.post(LOGIN_PATH, {
      username: (username || "").trim(),
      password: password || "",
    });

    const token =
      data?.token ||
      data?.key ||
      data?.access ||
      data?.access_token ||
      data?.values?.token ||
      data?.values?.key;

    if (!token) {
      if (import.meta.env.DEV) console.warn("[LOGIN NO TOKEN]", { status, data });
      const serverMsg =
        data?.detail || data?.message || data?.error || "No se recibió token desde el backend";
      throw new Error(serverMsg);
    }

    setAuthToken(token);
    return { token };
  } catch (err) {
    if (import.meta.env.DEV) {
      if (axios.isAxiosError?.(err)) {
        console.warn("[LOGIN AXIOS ERROR]", {
          status: err.response?.status,
          body: err.response?.data,
          url: (err.config?.baseURL || "") + (err.config?.url || ""),
          method: err.config?.method,
          code: err.code,
          message: err.message,
        });
      } else {
        console.warn("[LOGIN GENERIC ERROR]", { name: err?.name, message: err?.message });
      }
    }
    const friendly = friendlyLoginError(err);
    const e = new Error(friendly);
    e.original = err;
    throw e;
  }
}

//GET LLAMA AL ENDPOINT Y DEVUELVE EL USUARIO SOLO SI EL HEADER AUTHORIZATION YA FUE SETEADO
export async function me() {
  const { data } = await api.get(ME_PATH);
  return data;
}

export async function updateMe(payload) {
  const { data } = await api.patch(ME_UPDATE_PATH, payload);
  return data;
}

export async function changePassword({ current_password, new_password }) {
  const { data } = await api.post(CHANGE_PASSWORD, {
    current_password,
    new_password,
  });
  return data;
}

//LIMPIA EL TOKEN, HEADER Y CACHE
export function logout() {
  setAuthToken(null);
  localStorage.removeItem("me");
}

export default api;

export const ROLES = {
  ADMIN: "ADMIN",
  STAFF: "STAFF",
  RESIDENT: "RESIDENT",
};

export function getRole(obj) {
  const raw =
    obj?.role ?? obj?.rol ?? obj?.rolNombre ?? obj?.profile?.role ?? null;

  if (typeof raw !== "string") return null;
  const r = raw.trim().toUpperCase();

  const map = {
    ADMIN: "ADMIN",
    ADMINISTRADOR: "ADMIN",
    STAFF: "STAFF",
    PERSONAL: "STAFF",
    RESIDENT: "RESIDENTE",
    RESIDENTE: "RESIDENT",
    CLIENT: "CLIENTE",
    CLIENTE: "CLIENTE",
  };
  return map[r] ?? r;
}

//API DE USUARIOS
const USERS_BASE = import.meta.env.VITE_API_USERS_PATH ?? "admin/users/";

function cleanUserPayload(input, isCreate = false) {
  const p = { ...input };
  for (const k of ["email", "first_name", "last_name"]) {
    if (!p[k]) delete p[k];
  }
  if (!isCreate && !p.password) delete p.password;
  if (typeof p.role === "string" && p.role.trim()) {
    const out = p.role.trim().toUpperCase();
    const mapOut = { PERSONAL: "STAFF", RESIDENTE: "RESIDENT" };
    p.role_input = mapOut[out] || out;
    delete p.role;
  }
  return p;
}

export async function listUsers(params = {}) {
  const { data } = await api.get(USERS_BASE, { params });
  return Array.isArray(data) ? data : data.results || data;
}

export async function createUser(payload) {
  const { data } = await api.post(USERS_BASE, cleanUserPayload(payload, true));
  return data;
}

export async function updateUser(id, payload) {
  const { data } = await api.patch(
    `${USERS_BASE}${id}/`,
    cleanUserPayload(payload, false)
  );
  return data;
}

export async function deleteUser(id) {
  await api.delete(`${USERS_BASE}${id}/`);
}
