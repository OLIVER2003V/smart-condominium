// src/pages/ResidentVisitsPage.jsx
import { useEffect, useState } from "react";
import {
  listResidentPending,
  approveVisit,
  denyApproval,
  buildVisitQuery,
  listVisits,
  approvalBadgeClass,
} from "../api/visits";
import api from "../api/auth";

export default function ResidentVisitsPage() {
  const [pending, setPending] = useState([]);
  const [recentApproved, setRecentApproved] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(null); // id en acción

  const load = async () => {
    setLoading(true);
    try {
      // Pendientes
      const pend = await listResidentPending();
      const pendRows = Array.isArray(pend) ? pend : pend?.results || [];
      setPending(pendRows);

      // Aprobadas recientes (últimas 30)
      const params = buildVisitQuery({
        mine: true,
        approval_status: "APR",
        ordering: "-approved_at",
        page_size: 30,
      });
      const apr = await listVisits(params);
      const aprRows = Array.isArray(apr) ? apr : apr?.results || [];
      setRecentApproved(aprRows);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const doApprove = async (id) => {
    try {
      setActionLoading(id);
      await approveVisit(id, { hours_valid: 24 });
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  const doDeny = async (id) => {
    try {
      const reason = prompt("Motivo (opcional):") || "";
      setActionLoading(id);
      await denyApproval(id, { reason });
      await load();
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="visits-page">
      <h2>Mis visitas (Residente)</h2>

      {/* Pendientes */}
      <div className="card table-card">
        <div className="card__header">
          <h3>Pendientes por aprobar</h3>
          <button className="au-button au-button--ghost" onClick={load} disabled={loading}>
            {loading ? "Actualizando…" : "Actualizar"}
          </button>
        </div>
        <table className="au-table au-table--compact">
          <thead>
            <tr>
              <th>Visitante</th>
              <th>Documento</th>
              <th>Unidad</th>
              <th>Programada</th>
              <th>Aprobación</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pending.length === 0 && (
              <tr>
                <td colSpan={6}>No tienes visitas pendientes.</td>
              </tr>
            )}
            {pending.map((v) => (
              <tr key={v.id}>
                <td>
                  {v?.visitor?.full_name || "—"}
                  <div className="subtle">{v?.purpose || ""}</div>
                </td>
                <td>
                  {v?.visitor?.doc_type}-{v?.visitor?.doc_number}
                </td>
                <td>{v.unit_name || v.unit}</td>
                <td>{v.scheduled_for ? new Date(v.scheduled_for).toLocaleString() : "—"}</td>
                <td>
                  <span className={`badge ${approvalBadgeClass(v.approval_status)}`}>
                    {v.approval_status}
                  </span>
                </td>
                <td className="au-actions">
                  <button
                    className="au-button"
                    onClick={() => doApprove(v.id)}
                    disabled={actionLoading === v.id}
                  >
                    {actionLoading === v.id ? "Procesando…" : "Aprobar"}
                  </button>
                  <button
                    className="au-button au-button--ghost"
                    onClick={() => doDeny(v.id)}
                    disabled={actionLoading === v.id}
                  >
                    Denegar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Aprobadas recientes */}
      <div className="card table-card" style={{ marginTop: 16 }}>
        <div className="card__header">
          <h3>Aprobadas recientemente</h3>
        </div>
        <table className="au-table au-table--compact">
          <thead>
            <tr>
              <th>Visitante</th>
              <th>Unidad</th>
              <th>Programada</th>
              <th>Expira</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {recentApproved.length === 0 && (
              <tr>
                <td colSpan={5}>No hay aprobaciones recientes.</td>
              </tr>
            )}
            {recentApproved.map((v) => (
              <tr key={v.id}>
                <td>{v?.visitor?.full_name || "—"}</td>
                <td>{v.unit_name || v.unit}</td>
                <td>{v.scheduled_for ? new Date(v.scheduled_for).toLocaleString() : "—"}</td>
                <td>{v.approval_expires_at ? new Date(v.approval_expires_at).toLocaleString() : "—"}</td>
                <td>
                  <span className={`badge ${approvalBadgeClass(v.approval_status)}`}>
                    {v.approval_status}
                  </span>{" "}
                  / {v.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
