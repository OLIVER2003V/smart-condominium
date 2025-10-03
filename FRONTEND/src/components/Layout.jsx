// src/components/Layout.jsx
import { useEffect, useMemo, useState } from "react";
import { NavLink, Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import "../styles.css";
import { getRole } from "../api/auth"; // ⬅️ importa el helper

/** ========== Helpers visuales reusables ========== */
function NavGroup({ title, open, onToggle, children, hidden }) {
  if (hidden) return null; // ⬅️ no renderiza si el grupo no tiene hijos visibles
  return (
    <div className="nav-group">
      <button type="button" className="nav-group__header" onClick={onToggle}>
        <span>{title}</span>
        <span className={`chev ${open ? "open" : ""}`}>▸</span>
      </button>
      <div className={`nav-group__items ${open ? "open" : ""}`}>{children}</div>
    </div>
  );
}

function SubGroup({ title, open, onToggle, children, hidden }) {
  if (hidden) return null;
  return (
    <div className="nav__package">
      <button type="button" className="nav-group__header" onClick={onToggle}>
        <span>{title}</span>
        <span className={`chev ${open ? "open" : ""}`}>▸</span>
      </button>
      <div className={`nav-group__items ${open ? "open" : ""}`}>{children}</div>
    </div>
  );
}

function NavItem({ to, children, hidden }) {
  if (hidden) return null;
  return (
    <NavLink
      to={to}
      className={({ isActive }) => `nav__sublink ${isActive ? "active" : ""}`}
    >
      {children}
    </NavLink>
  );
}

/** ============================ Layout ============================ */
export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const me = useMemo(() => {
    try { return JSON.parse(localStorage.getItem("me") || "{}"); }
    catch { return {}; }
  }, []);

  const role = getRole(me) || (me?.is_superuser ? "ADMIN" : "");
  const isRes = role === "RESIDENTE";
  const isStaff = role === "STAFF"; 
  const isAdm = role === "ADMIN";// "ADMIN" | "STAFF" | "RESIDENT"
  const roleCode =
    me?.profile?.role?.code ||
    me?.profile?.role_code ||
    (me?.is_superuser ? "ADMIN" : "");

  const can = (roles) => {
    if (!roles || roles.length === 0) return true;
    return roles.includes(role);
  };

  const signout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("me");
    navigate("/signin", { replace: true });
  };

  // ====== Estado móvil: sidebar ======
  const [sidebarOpen, setSidebarOpen] = useState(false);
  useEffect(() => { setSidebarOpen(false); }, [location.pathname, location.search]);

  // ====== Helpers y params ======
  const params = new URLSearchParams(location.search);
  const currentGroup = params.get("group");
  const onUsersPath = location.pathname === "/admin/usuarios";
  const activeUsers = onUsersPath && !currentGroup;
  const activeStaff = onUsersPath && currentGroup === "staff";
  const activeResidents = onUsersPath && currentGroup === "residents";
  const isPath = (p) => location.pathname.startsWith(p);

  // ========= Estado de grupos =========
  const [groups, setGroups] = useState(() => ({
    admin: location.pathname.startsWith("/admin"),
    usr: isPath("/admin/usuarios"),
    uni: isPath("/admin/unidades"),
    fin: isPath("/admin/cuotas") || isPath("/admin/pagos"),
    com: isPath("/admin/avisos"),
    areas: isPath("/admin/areas-comunes"),
    tasks: isPath("/admin/tareas") || isPath("/admin/asignar-tareas"),
    seg: isPath("/admin/infracciones"),
    rep: isPath("/admin/reportes"),
    reservas: isPath("/admin/reservas") || isPath("/admin/areas-comunes/reservas"),
    seguridad: isPath("/acceso-vehicular") || isPath("/face"),
  }));

  useEffect(() => {
    if (location.pathname.startsWith("/admin")) {
      setGroups((g) => ({ ...g, admin: true }));
    }
  }, [location.pathname]);

  const toggle = (key) => setGroups((g) => ({ ...g, [key]: !g[key] }));

  // ====== Cálculo de visibilidad por rol ======
  const show = {
    // menús simples
    dashboard: can(["ADMIN","STAFF","RESIDENTE"]),
    areasDisp: can(["ADMIN","RESIDENTE"]),
    misAvisos: can(["ADMIN","STAFF","RESIDENTE"]),
    misTareas: can(["STAFF","ADMIN"]),
    misVehiculos: can(["ADMIN","STAFF","RESIDENTE"]),

    // gestionar usuarios
    me: can(["ADMIN","RESIDENTE","STAFF"]), // si quieres ocultar a STAFF, quítalo
    adminUsuarios: can(["ADMIN","STAFF"]), // si solo ADMIN, deja ["ADMIN"]
    adminRoles: can(["ADMIN"]),
    adminPerms: can(["ADMIN"]),
    estadoCuenta: can(["ADMIN","RESIDENTE"]),
    personal: can(["ADMIN"]),
    vehiculosAut: can(["ADMIN","STAFF"]),

    // subgrupos
    sgUsuarios: can(["ADMIN","STAFF"]),
    sgComunicacion: can(["ADMIN"]),
    sgAreas: can(["ADMIN"]),
    sgTareas: can(["ADMIN","STAFF"]),
    sgReportes: can(["ADMIN"]),

    // otros grupos principales
    gUnidades: can(["ADMIN","RESIDENTE"]),
    gFinanzas: can(["ADMIN"]),
    gSeguridad: can(["ADMIN","STAFF"]),
  };

  // si un grupo no tiene hijos visibles, lo escondemos
  const groupHasChildren = {
    admin:
      show.me ||
      show.adminUsuarios ||
      show.adminRoles ||
      show.adminPerms ||
      show.estadoCuenta ||
      show.personal ||
      show.vehiculosAut ||
      show.sgUsuarios ||
      show.sgComunicacion ||
      show.sgAreas ||
      show.sgTareas ||
      show.sgReportes,
    gUnidades: show.gUnidades,
    gFinanzas: show.gFinanzas,
    gSeguridad: show.gSeguridad,
  };

  return (
    <div className={`layout ${sidebarOpen ? "layout--locked" : ""}`}>
      {/* ===== Topbar (móvil) ===== */}
      <header className="topbar">
        <button className="hamburger" aria-label="Abrir menú" onClick={() => setSidebarOpen((v) => !v)}>☰</button>
        <div className="topbar__title">Smart Condominio</div>
        <div className="topbar__spacer" />
      </header>

      {/* Backdrop móvil */}
      <div className={`sidebar__backdrop ${sidebarOpen ? "open" : ""}`} onClick={() => setSidebarOpen(false)} />

      {/* ===== Sidebar ===== */}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10 }}>
          Smart Condominio
        </div>

        {/* Contenido desplazable del menú */}
        <div className="sidebar__scroll">
          {show.dashboard && (
            <NavLink to="/dashboard" className={({ isActive }) => `nav__link ${isActive ? "active" : ""}`}>
              Dashboard
            </NavLink>
          )}

          {show.areasDisp && (
            <NavLink to="/areas/disponibilidad" className={({ isActive }) => `nav__link ${isActive ? "active" : ""}`}>
              Disponibilidad de áreas
            </NavLink>
          )}

          {show.misAvisos && (
            <NavLink to="/avisos" className={({ isActive }) => `nav__link ${isActive ? "active" : ""}`}>
              Mis avisos
            </NavLink>
          )}

          {show.misTareas && (
            <NavLink to="/tareas" className={({ isActive }) => `nav__link ${isActive ? "active" : ""}`}>
              Mis tareas
            </NavLink>
          )}

          {show.misVehiculos && (
            <NavLink to="/vehiculos" className={({ isActive }) => `nav__link ${isActive ? "active" : ""}`}>
              Mis vehículos
            </NavLink>
          )}

          {/* ===== GESTIONAR USUARIOS ===== */}
          <NavGroup
            title="GESTIONAR USUARIOS"
            open={groups.admin}
            onToggle={() => toggle("admin")}
            hidden={!groupHasChildren.admin}
          >
            <NavItem to="/me" hidden={!show.me}>Gestionar Perfil (CU03)</NavItem>
            <NavItem to="/admin/usuarios" hidden={!show.adminUsuarios}>Gestionar Usuarios (CU04)</NavItem>
            <NavItem to="/admin/roles" hidden={!show.adminRoles}>Gestionar Roles (CU05)</NavItem>
            <NavItem to="/admin/permisos" hidden={!show.adminPerms}>Gestionar Permisos (CU06)</NavItem>
            <NavItem to="/estado-cuenta" hidden={!show.estadoCuenta}>Consultar Estado de Cuenta (CU10)</NavItem>
            <NavItem to="/personal" hidden={!show.personal}>Gestionar Personal (CU14)</NavItem>
            <NavItem to="/admin/solicitudes-vehiculo" hidden={!show.vehiculosAut}>
              Gestionar Vehículos Autorizados (CU26)
            </NavItem>

            {/* Subgrupo: Gestión de usuarios (CU04) */}
            <SubGroup
              title="Gestionar Usuarios (CU04)"
              open={groups.usr}
              onToggle={() => toggle("usr")}
              hidden={!show.sgUsuarios}
            >
              <Link to="/admin/usuarios" className={`nav__sublink ${onUsersPath && !currentGroup ? "active" : ""}`}>
                Usuarios
              </Link>
              <Link to={{ pathname: "/admin/usuarios", search: "?group=staff" }}
                    className={`nav__sublink ${onUsersPath && currentGroup === "staff" ? "active" : ""}`}>
                Staff
              </Link>
              <Link to={{ pathname: "/admin/usuarios", search: "?group=residents" }}
                    className={`nav__sublink ${onUsersPath && currentGroup === "residents" ? "active" : ""}`}>
                Residentes
              </Link>
            </SubGroup>

            {/* Subgrupo: Comunicación */}
            <SubGroup title="Comunicación" open={groups.com} onToggle={() => toggle("com")} hidden={!show.sgComunicacion}>
              <NavItem to="/admin/avisos">Avisos (Admin)</NavItem>
            </SubGroup>

            {/* Subgrupo: Áreas comunes */}
            <SubGroup title="Áreas comunes" open={groups.areas} onToggle={() => toggle("areas")} hidden={!show.sgAreas}>
              <NavItem to="/admin/areas-comunes">Catálogo de áreas</NavItem>
              <NavItem to="/admin/areas-comunes/reglas">Reglas de disponibilidad</NavItem>
            </SubGroup>

            {/* Subgrupo: Gestión de tareas */}
            <SubGroup title="Gestión de tareas" open={groups.tasks} onToggle={() => toggle("tasks")} hidden={!show.sgTareas}>
              <NavItem to="/admin/tareas">Tareas (Admin)</NavItem>
              <NavItem to="/admin/asignar-tareas">Asignar tareas</NavItem>
            </SubGroup>

            {/* Subgrupo: Reportes */}
            <SubGroup title="Reportes" open={groups.rep} onToggle={() => toggle("rep")} hidden={!show.sgReportes}>
              {/* por ahora vacío */}
            </SubGroup>
          </NavGroup>

          {/* ===== Otros menús principales ===== */}
          <NavGroup
            title="GESTIONAR UNIDADES"
            open={groups.reservas}
            onToggle={() => toggle("reservas")}
            hidden={!show.gUnidades}
          >
            <NavItem to="/admin/unidades" hidden={!isAdm}>Gestionar Unidades (CU07)</NavItem>
            <NavItem to="/visits" hidden={!isAdm && !isStaff}>Gestionar Visitas (CU22)</NavItem>
            <NavItem to="/mis-visitas" hidden={!isRes}>Mis Visitas (CU22)</NavItem>
            <NavItem to="/estado">Pagar QR (CU09)</NavItem>
          </NavGroup>

          <NavGroup
            title="GESTIONAR FINANZAS"
            open={groups.fin}
            onToggle={() => toggle("fin")}
            hidden={!show.gFinanzas}
          >
            <NavItem to="/admin/cuotas">Gestionar Cuotas (CU08)</NavItem>
            <NavItem to="/admin/infracciones">Gestionar Infracciones (CU09)</NavItem>
            <NavItem to="/estado">Pagar QR (CU09)</NavItem>
          </NavGroup>

          <NavGroup
            title="GESTIONAR SEGURIDAD"
            open={groups.seguridad}
            onToggle={() => toggle("seguridad")}
            hidden={!show.gSeguridad}
          >
            <NavItem to="/acceso-vehicular">Acceso Vehicular (CU23)</NavItem>
            <NavItem to="/visits">Gestionar Visitas (CU22)</NavItem>
            <NavItem to="/face/enroll">Enrolar Rostros (CU23)</NavItem>
            <NavItem to="/face/identify">Reconocimiento facial (CU23)</NavItem>
          </NavGroup>
        </div>

        {/* Footer fijo */}
        <div className="userbox userbox--sticky">
          <div className="muted" style={{ fontSize: 18 }}>
            {role || "—"} {roleCode ? <span className="badge">{roleCode}</span> : null}
          </div>
          <button className="au-button au-button--ghost" onClick={signout}>
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* ===== Contenido ===== */}
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
