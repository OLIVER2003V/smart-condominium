// src/pages/VisitsPage.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import api from "../api/auth";
import {
  listVisits,
  getVisit,
  createVisit,
  updateVisit,
  deleteVisit,
  enterVisit,
  exitVisit,
  cancelVisit,
  denyVisit,
  serializeVisitPayload,
  buildVisitQuery,
  approvalBadgeClass, // 👈 nuevo helper
} from "../api/visits";
import "./VisitsPage.css";

const STATUS_CHOICES = [
  { value: "", label: "(todas)" },
  { value: "REGISTRADO", label: "Registrado" },
  { value: "INGRESADO", label: "Ingresado" },
  { value: "SALIDO", label: "Salido" },
  { value: "CANCELADO", label: "Cancelado" },
  { value: "DENEGADO", label: "Denegado" },
];

const FORM_INIT = {
  // visitante
  visitor_full_name: "",
  visitor_doc_type: "CI",
  visitor_doc_number: "",
  visitor_phone: "",
  // visita
  unit: "",
  host_resident: "",
  vehicle_plate: "",
  purpose: "",
  scheduled_for: "",
  notes: "",
};

function asISOorNull(v) {
  const s = String(v || "").trim();
  if (!s) return null;
  // "YYYY-MM-DDTHH:mm" -> "YYYY-MM-DDTHH:mm:00Z"
  if (s.length === 16) return s + ":00Z";
  // "YYYY-MM-DDTHH:mm:ss" -> "YYYY-MM-DDTHH:mm:ssZ"
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(s)) return s + "Z";
  return s;
}

function badgeClass(status) {
  const s = String(status || "").toLowerCase();
  if (s === "ingresado") return "badge--success";
  if (s === "registrado") return "badge--info";
  if (s === "salido") return "badge--neutral";
  if (s === "cancelado" || s === "denegado") return "badge--danger";
  return "badge--neutral";
}

export default function VisitsPage() {
  // tabla
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  // filtros
  const [q, setQ] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fUnit, setFUnit] = useState("");

  // combos
  const [units, setUnits] = useState([]);
  const [residents, setResidents] = useState([]);
  const [loadingCombos, setLoadingCombos] = useState(false);

  // form
  const [openForm, setOpenForm] = useState(false);
  const [form, setForm] = useState(FORM_INIT);
  const [editingId, setEditingId] = useState(null);
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // === CARGA TABLA ===
  const load = async () => {
    setLoading(true);
    try {
      const params = buildVisitQuery({
        q,
        status: fStatus,
        unit: fUnit,
        ordering: "-created_at",
        page_size: 100,
      });
      const data = await listVisits(params);
      setRows(Array.isArray(data) ? data : data?.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // recarga cuando cambian filtros/búsqueda (debounce)
  const debounceRef = useRef(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      load();
    }, 350);
    return () => clearTimeout(debounceRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, fStatus, fUnit]);

  // combos (unidades y residentes) cuando abres el form
  useEffect(() => {
    if (!openForm) return;
    (async () => {
      try {
        setLoadingCombos(true);
        const [uRes, rRes] = await Promise.all([
          api.get("unidades/", {
            params: {
              is_active: true,
              page_size: 1000,
              ordering: "manzana,lote,numero",
            },
          }),
          api.get("admin/users/", {
            params: {
              is_active: true,
              page_size: 1000,
              ordering: "first_name,last_name",
            },
          }),
        ]);

        const unitsRaw = Array.isArray(uRes.data) ? uRes.data : uRes.data?.results || [];
        setUnits(
          unitsRaw.map((u) => ({
            id: u.id,
            label: `Mza ${u.manzana}${u.lote ? `-${u.lote}` : ""}-${u.numero}`,
          }))
        );

        const usersRaw = Array.isArray(rRes.data) ? rRes.data : rRes.data?.results || [];
        const onlyResidents = usersRaw.filter((u) => {
          const code =
            u?.role ||
            u?.role_code ||
            u?.profile?.role?.code ||
            (u?.profile?.role_code ?? "");
          return String(code).toUpperCase() === "RESIDENT";
        });
        setResidents(
          onlyResidents.map((u) => ({
            id: u.id,
            label:
              [u.first_name, u.last_name].filter(Boolean).join(" ").trim() ||
              u.username ||
              `Usuario ${u.id}`,
            email: u.email || "",
          }))
        );
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingCombos(false);
      }
    })();
  }, [openForm]);

  // handlers
  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const openNew = () => {
    setEditingId(null);
    setForm(FORM_INIT);
    setFormError("");
    setOpenForm(true);
  };

  const editRow = async (id) => {
    try {
      const v = await getVisit(id);
      setEditingId(id);
      setForm({
        visitor_full_name: v?.visitor?.full_name || "",
        visitor_doc_type: v?.visitor?.doc_type || "CI",
        visitor_doc_number: v?.visitor?.doc_number || "",
        visitor_phone: v?.visitor?.phone || "",
        unit: v.unit || "",
        host_resident: v.host_resident || "",
        vehicle_plate: v.vehicle_plate || "",
        purpose: v.purpose || "",
        scheduled_for: v.scheduled_for ? v.scheduled_for.slice(0, 16) : "",
        notes: v.notes || "",
      });
      setFormError("");
      setOpenForm(true);
    } catch (e) {
      console.error(e);
      alert("No se pudo cargar la visita.");
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setFormError("");

    if (!form.unit || !form.host_resident) {
      setFormError("Unidad y Anfitrión son obligatorios.");
      return;
    }
    if (!form.visitor_doc_number || !form.visitor_full_name) {
      setFormError("Completa nombre y documento del visitante.");
      return;
    }

    const payload = serializeVisitPayload({
      visitor_full_name: form.visitor_full_name,
      visitor_doc_type: form.visitor_doc_type || "CI",
      visitor_doc_number: (form.visitor_doc_number || "").trim(),
      visitor_phone: form.visitor_phone || "",
      unit: Number(form.unit),
      host_resident: Number(form.host_resident),
      vehicle_plate: (form.vehicle_plate || "").toUpperCase(),
      purpose: form.purpose || "",
      scheduled_for: asISOorNull(form.scheduled_for),
      notes: form.notes || "",
    });

    try {
      setSubmitting(true);
      console.log("VISIT PAYLOAD →", payload);
      if (editingId) {
        await updateVisit(editingId, payload);
      } else {
        await createVisit(payload);
      }
      setOpenForm(false);
      setForm(FORM_INIT);
      setEditingId(null);
      await load();
    } catch (err) {
      console.error("CREATE/UPDATE VISIT ERROR →", err?.response?.data || err);
     const data = err?.response?.data;
     let msg = "No se pudo guardar la visita.";
     if (typeof data === "string") {
       msg = data;
     } else if (data) {
       // junta todos los errores campo: mensaje
       const parts = [];
       Object.entries(data).forEach(([k, v]) => {
         if (Array.isArray(v)) parts.push(`${k}: ${v.join(", ")}`);
         else if (typeof v === "string") parts.push(`${k}: ${v}`);
         else parts.push(`${k}: ${JSON.stringify(v)}`);
       });
       if (parts.length) msg = parts.join(" | ");
     }
     setFormError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const removeRow = async (id) => {
    // eslint-disable-next-line no-restricted-globals
    if (!confirm("¿Eliminar esta visita?")) return;
    try {
      await deleteVisit(id);
      await load();
    } catch (e) {
      console.error(e);
      alert("No se pudo eliminar.");
    }
  };

  // acciones estado (portería)
  const doEnter = async (id, { force = false } = {}) => {
    await enterVisit(id, { force });
    await load();
  };
  const doExit = async (id) => {
    await exitVisit(id);
    await load();
  };
  const doCancel = async (id) => {
    await cancelVisit(id);
    await load();
  };
  const doDeny = async (id) => {
    await denyVisit(id);
    await load();
  };

  // render
  const unitOptions = useMemo(
    () =>
      (units ?? []).map((u) => (
        <option key={u.id} value={u.id}>
          {u.label}
        </option>
      )),
    [units]
  );
  const residentOptions = useMemo(
    () =>
      (residents ?? []).map((r) => (
        <option key={r.id} value={r.id}>
          {r.label} {r.email ? `— ${r.email}` : ""}
        </option>
      )),
    [residents]
  );

  return (
    <div className="visits-page">
      <h2>Gestión de Visitas</h2>

      {/* Toolbar */}
      <div className="card au-toolbar">
        <form
          className="au-toolbar__form"
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
        >
          <div className="au-field">
            <label className="au-label">Búsqueda</label>
            <input
              className="au-input"
              placeholder="nombre/doc/placa/propósito…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          </div>

          <div className="au-field" style={{ minWidth: 180 }}>
            <label className="au-label">Estado</label>
            <select
              className="au-input"
              value={fStatus}
              onChange={(e) => setFStatus(e.target.value)}
            >
              {STATUS_CHOICES.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="au-field" style={{ minWidth: 220 }}>
            <label className="au-label">Unidad</label>
            <select
              className="au-input"
              value={fUnit}
              onChange={(e) => setFUnit(e.target.value)}
            >
              <option value="">(todas)</option>
              {unitOptions}
            </select>
          </div>

          <button className="au-button" disabled={loading}>
            {loading ? "Buscando…" : "Buscar"}
          </button>
          <button
            type="button"
            className="au-button au-button--ghost"
            onClick={() => {
              setQ("");
              setFStatus("");
              setFUnit("");
            }}
            disabled={loading}
          >
            Limpiar
          </button>
          <button
            type="button"
            className="au-button au-button--ghost"
            onClick={openNew}
          >
            + Nueva visita
          </button>
        </form>
      </div>

      {/* Formulario */}
      {openForm && (
        <form className="card visit-form" onSubmit={submit}>
          <div className="visit-form__header">
            <h3>{editingId ? "Editar visita" : "Nueva visita"}</h3>
            <div className="visit-form__header-actions">
              <button
                type="button"
                className="au-button au-button--ghost"
                onClick={() => {
                  setOpenForm(false);
                  setEditingId(null);
                  setForm(FORM_INIT);
                  setFormError("");
                }}
              >
                Cerrar
              </button>
            </div>
          </div>

          {formError && <p className="error">{formError}</p>}

          <div className="au-grid-3">
            <div className="au-field">
              <label className="au-label">Nombre del visitante</label>
              <input
                name="visitor_full_name"
                className="au-input"
                value={form.visitor_full_name}
                onChange={onChange}
                required
              />
            </div>
            <div className="au-field">
              <label className="au-label">Tipo doc.</label>
              <select
                name="visitor_doc_type"
                className="au-input"
                value={form.visitor_doc_type}
                onChange={onChange}
              >
                <option value="CI">Cédula</option>
                <option value="PASS">Pasaporte</option>
                <option value="OTRO">Otro</option>
              </select>
            </div>
            <div className="au-field">
              <label className="au-label">N° documento</label>
              <input
                name="visitor_doc_number"
                className="au-input"
                value={form.visitor_doc_number}
                onChange={onChange}
                required
              />
            </div>
          </div>

          <div className="au-grid-3">
            <div className="au-field">
              <label className="au-label">Teléfono (opcional)</label>
              <input
                name="visitor_phone"
                className="au-input"
                value={form.visitor_phone}
                onChange={onChange}
                placeholder="Ej. 70000000"
              />
            </div>

            <div className="au-field">
              <label className="au-label">Unidad</label>
              <select
                name="unit"
                className="au-input"
                value={form.unit}
                onChange={onChange}
                required
                disabled={loadingCombos}
              >
                <option value="">Selecciona…</option>
                {unitOptions}
              </select>
            </div>

            <div className="au-field">
              <label className="au-label">Anfitrión (residente)</label>
              <select
                name="host_resident"
                className="au-input"
                value={form.host_resident}
                onChange={onChange}
                required
                disabled={loadingCombos}
              >
                <option value="">Selecciona…</option>
                {residentOptions}
              </select>
            </div>
          </div>

          <div className="au-grid-3">
            <div className="au-field">
              <label className="au-label">Placa (opcional)</label>
              <input
                name="vehicle_plate"
                className="au-input"
                value={form.vehicle_plate}
                onChange={onChange}
                placeholder="ABC123"
              />
            </div>
            <div className="au-field">
              <label className="au-label">Propósito</label>
              <input
                name="purpose"
                className="au-input"
                value={form.purpose}
                onChange={onChange}
                placeholder="Ej. reunión, entrega…"
              />
            </div>
            <div className="au-field">
              <label className="au-label">Programada para</label>
              <input
                type="datetime-local"
                name="scheduled_for"
                className="au-input"
                value={form.scheduled_for}
                onChange={onChange}
              />
            </div>
          </div>

          <div className="au-field">
            <label className="au-label">Notas</label>
            <textarea
              name="notes"
              className="au-input"
              rows={3}
              value={form.notes}
              onChange={onChange}
            />
          </div>

          <div className="visit-form__footer">
            <button className="au-button" disabled={submitting}>
              {submitting
                ? "Guardando…"
                : editingId
                ? "Guardar cambios"
                : "Crear visita"}
            </button>
            <button
              type="button"
              className="au-button au-button--ghost"
              onClick={() => {
                setOpenForm(false);
                setEditingId(null);
                setForm(FORM_INIT);
                setFormError("");
              }}
              disabled={submitting}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* Tabla */}
      <div className="card table-card">
        <table className="au-table au-table--compact visits-table">
          <thead>
            <tr>
              <th className="col--lg">Visitante</th>
              <th className="col--md">Documento</th>
              <th className="col--md">Unidad</th>
              <th className="col--md">Anfitrión</th>
              <th className="col--sm">Placa</th>
              <th className="col--md">Propósito</th>
              <th className="col--sm">Aprobación</th> {/* 👈 nueva */}
              <th className="col--sm">Estado</th>
              <th className="col--md">Entrada</th>
              <th className="col--md">Salida</th>
              <th className="col--actions"></th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={11}>Cargando…</td>
              </tr>
            )}
            {!loading && (rows?.length ?? 0) === 0 && (
              <tr>
                <td colSpan={11}>Sin resultados.</td>
              </tr>
            )}
            {(rows ?? []).map((v) => (
              <tr key={v.id}>
                <td>
                  {v?.visitor?.full_name || "—"}
                  <div className="subtle">
                    {v?.visitor?.phone ? `📞 ${v.visitor.phone}` : ""}
                  </div>
                </td>
                <td>
                  {v?.visitor?.doc_type}-{v?.visitor?.doc_number}
                </td>
                <td>{v.unit_name || v.unit}</td>
                <td>{v.host_resident_name || v.host_resident}</td>
                <td>{v.vehicle_plate || "—"}</td>
                <td>{v.purpose || "—"}</td>

                {/* Aprobación */}
                <td>
                  <span className={`badge ${approvalBadgeClass(v.approval_status)}`}>
                    {v.approval_status || "—"}
                  </span>
                  {v.approval_expires_at && (
                    <div className="subtle">
                      Expira: {new Date(v.approval_expires_at).toLocaleString()}
                    </div>
                  )}
                </td>

                {/* Estado operativo */}
                <td>
                  <span className={`badge ${badgeClass(v.status)}`}>{v.status}</span>
                </td>
                <td>{v.entry_at ? new Date(v.entry_at).toLocaleString() : "—"}</td>
                <td>{v.exit_at ? new Date(v.exit_at).toLocaleString() : "—"}</td>

                <td className="au-actions">
                  <button
                    className="au-button au-button--ghost"
                    onClick={() => editRow(v.id)}
                    title="Editar"
                  >
                    Editar
                  </button>
                  <button
                    className="au-button au-button--ghost"
                    onClick={() => removeRow(v.id)}
                    title="Eliminar"
                  >
                    Eliminar
                  </button>

                  {/* Acciones de flujo */}
                  {v.status === "REGISTRADO" && (
                    <>
                      <button
                        className="au-button au-button--ghost"
                        onClick={() => doEnter(v.id)}
                        title="Marcar entrada"
                        disabled={v.approval_status !== "APR"} // 👈 bloquea si no aprobado
                      >
                        Ingresar
                      </button>

                      {v.approval_status !== "APR" && (
                        <button
                          className="au-button au-button--ghost"
                          onClick={() => doEnter(v.id, { force: true })}
                          title="Forzar ingreso (sin aprobación válida)"
                        >
                          Ingresar (forzar)
                        </button>
                      )}

                      <button
                        className="au-button au-button--ghost"
                        onClick={() => doDeny(v.id)}
                        title="Denegar"
                      >
                        Denegar
                      </button>
                      <button
                        className="au-button au-button--ghost"
                        onClick={() => doCancel(v.id)}
                        title="Cancelar"
                      >
                        Cancelar
                      </button>
                    </>
                  )}

                  {v.status === "INGRESADO" && (
                    <button
                      className="au-button au-button--ghost"
                      onClick={() => doExit(v.id)}
                      title="Marcar salida"
                    >
                      Salir
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
