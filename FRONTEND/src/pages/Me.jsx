import React, { useEffect, useMemo, useRef, useState } from "react";
import { me as getMe, updateMe, changePassword } from "../api/auth";
import "./Me.css";

const EDITABLE_BY_ROLE = {
  ADMIN: ["first_name", "last_name", "email", "username"],
  STAFF: ["first_name", "last_name", "email"],
  RESIDENT: ["first_name", "last_name", "email"],
};

const pick = (obj, keys) =>
  keys.reduce((acc, k) => (obj[k] !== undefined ? { ...acc, [k]: obj[k] } : acc), {});

// ------------ helpers de errores (sin tocar tu flujo) ------------
const LABELS = {
  current_password: "Contraseña actual",
  new_password: "Nueva contraseña",
  email: "Correo electrónico",
  username: "Usuario",
  first_name: "Nombres",
  last_name: "Apellidos",
};

function extractFieldErrors(data) {
  if (!data || typeof data !== "object") return {};
  const out = {};
  for (const k of Object.keys(data)) {
    const v = data[k];
    if (Array.isArray(v) && v.length) out[k] = v;
    else if (typeof v === "string") out[k] = [v];
  }
  return out;
}

function normalizeTopMessage(e) {
  const data = e?.response?.data;
  if (data?.detail) return String(data.detail);
  if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length) {
    return String(data.non_field_errors[0]);
  }
  return e?.message || "Revisa los campos resaltados.";
}
// -----------------------------------------------------------------

export default function Me() {
  const cached = JSON.parse(localStorage.getItem("me") || "null");

  const [profile, setProfile] = useState(cached);
  const role =
    profile?.role ||
    profile?.role_code ||
    (profile?.is_superuser ? "ADMIN" : "RESIDENT");

  const [form, setForm] = useState({
    username: profile?.username || "",
    first_name: profile?.first_name || "",
    last_name: profile?.last_name || "",
    email: profile?.email || "",
  });

  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  // Mensajes: conservamos tu msg para éxito/info y agregamos err para errores
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  const [pwd, setPwd] = useState({ current_password: "", new_password: "" });

  // Errores por campo (perfil y contraseña)
  const [fieldErrors, setFieldErrors] = useState({});

  // Para recordar y restaurar el foco si algo lo roba (tu lógica)
  const [focusedName, setFocusedName] = useState(null);
  const inputsRef = useRef({}); // name -> HTMLInputElement

  useEffect(() => {
    (async () => {
      try {
        const fresh = await getMe();
        setProfile(fresh);
        setForm({
          username: fresh.username || "",
          first_name: fresh.first_name || "",
          last_name: fresh.last_name || "",
          email: fresh.email || "",
        });
        localStorage.setItem("me", JSON.stringify(fresh));
      } catch (e) {
        setErr(normalizeTopMessage(e));
      }
    })();
  }, []);

  // Campos editables por rol
  const allowed = useMemo(() => EDITABLE_BY_ROLE[role] || [], [role]);

  // Restaurar el foco si el input actual se re-creó (tu lógica)
  useEffect(() => {
    if (!editing || !focusedName) return;
    const el = inputsRef.current[focusedName];
    if (el && document.activeElement !== el) {
      const v = el.value;
      el.focus();
      //el.setSelectionRange?.(v.length, v.length);
    }
  });

  async function onPrimaryClick(e) {
    e.preventDefault();
    setMsg("");
    setErr("");
    setFieldErrors({});

    if (!editing) {
      setEditing(true);
      // focos: primer campo editable disponible
      const first = ["username", "first_name", "last_name", "email"].find((n) =>
        allowed.includes(n)
      );
      if (first) {
        requestAnimationFrame(() => {
          inputsRef.current[first]?.focus();
          setFocusedName(first);
        });
      }
      return;
    }

    setLoading(true);
    try {
      const payload = pick(form, allowed);
      const updated = await updateMe(payload);
      setProfile(updated);
      localStorage.setItem("me", JSON.stringify(updated));
      setMsg("Datos actualizados ✅");
      setEditing(false);
    } catch (e) {
      // 👇 mejoras de mensaje + errores por campo
      setErr(normalizeTopMessage(e));
      setFieldErrors(extractFieldErrors(e?.response?.data));
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  function onCancelEdit() {
    setForm({
      username: profile?.username || "",
      first_name: profile?.first_name || "",
      last_name: profile?.last_name || "",
      email: profile?.email || "",
    });
    setEditing(false);
    setMsg("");
    setErr("");
    setFieldErrors({});
    setFocusedName(null);
  }

  async function onChangePwd(e) {
    e.preventDefault();
    setLoading(true);
    setMsg("");
    setErr("");
    setFieldErrors({});
    try {
      await changePassword(pwd); // { current_password, new_password }
      setPwd({ current_password: "", new_password: "" });
      setMsg("Contraseña actualizada ✅");
    } catch (e) {
      setErr(normalizeTopMessage(e));
      setFieldErrors(extractFieldErrors(e?.response?.data));
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  // Campo memoizado con id estable y contenedor fijo
  const Field = React.memo(function Field({ label, name, type = "text" }) {
    const canEdit = allowed.includes(name);
    const inputId = `me-field-${name}`; // id estable por nombre
    const hasError = !!fieldErrors[name];

    if (!editing) {
      return (
        <div className="au-field">
          <label htmlFor={inputId}>{label}</label>
          <div className="au-readonly">{form[name] || "—"}</div>
        </div>
      );
    }

    return (
      <div className="au-field">
        <label htmlFor={inputId}>{label}</label>
        <input
          id={inputId}
          name={name}
          className={`au-input ${hasError ? "au-input--error" : ""}`}
          type={type}
          value={form[name] ?? ""}
          ref={(el) => (inputsRef.current[name] = el)}
          onFocus={() => setFocusedName(name)}
          onChange={(e) =>
            setForm((f) => ({ ...f, [name]: e.target.value }))
          }
          onKeyDown={(e) => {
            if (e.key === "Enter") e.preventDefault(); // evita submit y re-montajes
          }}
          disabled={!canEdit || loading}
          autoComplete={type === "email" ? "email" : "off"}
          inputMode={type === "email" ? "email" : undefined}
        />
        {hasError && (
          <p className="au-error-text">
            {(fieldErrors[name][0] || "")
              .replace(/^current_password/i, LABELS.current_password)
              .replace(/^new_password/i, LABELS.new_password)
              .replace(/^email/i, LABELS.email)
              .replace(/^username/i, LABELS.username)
              .replace(/^first_name/i, LABELS.first_name)
              .replace(/^last_name/i, LABELS.last_name)}
          </p>
        )}
      </div>
    );
  });

  return (
    <div className="card" style={{ maxWidth: 640 }}>
      <h3>
        Mi Perfil{" "}
        {role ? <span className="badge" style={{ marginLeft: 8 }}>{role}</span> : null}
      </h3>

      {msg && <p className="info">{msg}</p>}
      {err && <p className="error">{err}</p>}

      {/* PERFIL */}
      <form
        className="au-form"
        onSubmit={onPrimaryClick}
        onKeyDown={(e) => {
          // blindaje extra: ningún Enter hace submit aquí
          if (e.key === "Enter") e.preventDefault();
        }}
        style={{ marginBottom: 24 }}
      >
        <div className="au-form__grid">
          <Field label="Usuario" name="username" />
          <Field label="Nombres" name="first_name" />
          <Field label="Apellidos" name="last_name" />
          <Field label="Correo electrónico" name="email" type="email" />
        </div>

        <div className="au-actions" style={{ marginTop: 12 }}>
          <button className="au-button" type="submit" disabled={loading}>
            {editing ? (loading ? "Guardando..." : "Guardar") : "Editar"}
          </button>

          {editing && (
            <button
              type="button"
              className="au-button au-button--ghost"
              disabled={loading}
              onMouseDown={(e) => e.preventDefault()} // evita robar foco antes del click
              onClick={onCancelEdit}
            >
              Cancelar
            </button>
          )}
        </div>

        {!editing && allowed.length === 0 && (
          <p className="muted" style={{ marginTop: 8 }}>
            Tu rol no tiene permisos para editar información del perfil.
          </p>
        )}
      </form>

      {/* CAMBIO DE CONTRASEÑA */}
      <form
        className="au-form"
        onSubmit={onChangePwd}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.preventDefault();
        }}
      >
        <h4>Cambiar contraseña</h4>
        <label htmlFor="pwd-current">Contraseña actual</label>
        <input
          id="pwd-current"
          className={`au-input ${fieldErrors.current_password ? "au-input--error" : ""}`}
          type="password"
          value={pwd.current_password}
          onChange={(e) =>
            setPwd((p) => ({ ...p, current_password: e.target.value }))
          }
          required
          autoComplete="current-password"
        />
        {fieldErrors.current_password && (
          <p className="au-error-text">
            {(fieldErrors.current_password[0] || "").replace(
              /^current_password/i,
              LABELS.current_password
            )}
          </p>
        )}

        <label htmlFor="pwd-new">Nueva contraseña</label>
        <input
          id="pwd-new"
          className={`au-input ${fieldErrors.new_password ? "au-input--error" : ""}`}
          type="password"
          value={pwd.new_password}
          onChange={(e) =>
            setPwd((p) => ({ ...p, new_password: e.target.value }))
          }
          required
          autoComplete="new-password"
        />
        {fieldErrors.new_password && (
          <p className="au-error-text">
            {(fieldErrors.new_password[0] || "").replace(
              /^new_password/i,
              LABELS.new_password
            )}
          </p>
        )}

        <button className="au-button" type="submit" disabled={loading}>
          {loading ? "Actualizando..." : "Actualizar contraseña"}
        </button>
      </form>
    </div>
  );
}
