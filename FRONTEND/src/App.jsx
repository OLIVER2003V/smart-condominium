// src/App.jsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

import Signin from "./pages/Signin";
import Dashboard from "./pages/Dashboard";
import Me from "./pages/Me";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import RequireRole from "./components/RequireRole";

// Admin / Gestión
import AdminUsers from "./pages/AdminUsers";
import RolesPage from "./pages/Roles";
import Permisos from "./pages/Permisos";
import UnitsPage from "./pages/UnitsPage";
import CuotasPage from "./pages/CuotasPage";
import InfraccionesPage from "./pages/InfraccionesPage";
import AdminAvisosPage from "./pages/AdminAvisosPage";
import AdminTareasPage from "./pages/AdminTareasPage";
import AsignarTareasPage from "./pages/AsignarTareasPage";
import AdminAreasPage from "./pages/AdminAreasPage";
import AdminAreaReglasPage from "./pages/AdminAreaReglasPage";
import StaffPage from "./pages/StaffPage";
import SolicitudesVehiculoPage from "./pages/SolicitudesVehiculoPage";

// Usuario
import MisAvisosPage from "./pages/MisAvisosPage";
import MisTareasPage from "./pages/MisTareasPage";
import EstadoCuentaPage from "./pages/EstadoCuentaPage";
import AreasDisponibilidad from "./pages/AreasDisponibilidad";
import AreaReservaNueva from "./pages/AreaReservaNueva";
import VehiculosPage from "./pages/VehiculosPage";
import VisitsPage from "./pages/VisitsPage";
import ResidentVisitsPage from "./pages/ResidentVisitsPage";
import AccessControl from "./pages/AccessControl";
import FaceEnroll from "./pages/FaceEnroll";
import FaceIdentify from "./pages/FaceIdentify";
import EstadoCuenta from "./pages/EstadoCuenta";

/* ===========================
   Helper: lee el rol del usuario
   =========================== */
function readRoleFromLocalStorage() {
  const raw = localStorage.getItem("me") || localStorage.getItem("user");
  if (!raw) return null;
  try {
    const u = JSON.parse(raw);
    const role =
      u?.role ||
      u?.role_code ||
      u?.profile?.role?.code ||
      u?.profile?.role_code ||
      "";
    return String(role).toUpperCase() || null;
  } catch {
    return null;
  }
}

/* ===========================
   Switch de vistas para /visits
   =========================== */
function VisitsSwitch() {
  const [role, setRole] = useState(readRoleFromLocalStorage());

  // Por si el "me" en localStorage cambia durante la sesión
  useEffect(() => {
    const onStorage = () => setRole(readRoleFromLocalStorage());
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const isStaff = role === "ADMIN" || role === "STAFF";
  return isStaff ? <VisitsPage /> : <ResidentVisitsPage />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Pública */}
        <Route path="/signin" element={<Signin />} />

        {/* Zona autenticada con Layout */}
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="me" element={<Me />} />

          {/* Gestión de usuarios */}
          <Route
            path="admin/usuarios"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <AdminUsers />
              </RequireRole>
            }
          />
          <Route
            path="admin/roles"
            element={
              <RequireRole allow={["ADMIN"]}>
                <RolesPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/permisos"
            element={
              <RequireRole allow={["ADMIN"]}>
                <Permisos />
              </RequireRole>
            }
          />
          <Route
            path="personal"
            element={
              <RequireRole allow={["ADMIN"]}>
                <StaffPage />
              </RequireRole>
            }
          />

          {/* Unidades, cuotas, infracciones */}
          <Route
            path="admin/unidades"
            element={
              <RequireRole allow={["ADMIN"]}>
                <UnitsPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/cuotas"
            element={
              <RequireRole allow={["ADMIN"]}>
                <CuotasPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/infracciones"
            element={
              <RequireRole allow={["ADMIN"]}>
                <InfraccionesPage />
              </RequireRole>
            }
          />

          {/* Seguridad */}
          <Route
            path="acceso-vehicular"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <AccessControl />
              </RequireRole>
            }
          />
          <Route
            path="face/enroll"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <FaceEnroll />
              </RequireRole>
            }
          />
          <Route
            path="face/identify"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <FaceIdentify />
              </RequireRole>
            }
          />

          {/* Visitas */}
          <Route
            path="visits"
            element={
              <RequireRole allow={["ADMIN", "STAFF", "RESIDENT"]}>
                <VisitsSwitch />
              </RequireRole>
            }
          />
          
              <Route path="mis-visitas" element={<RequireRole allow={["RESIDENTE"]}><ResidentVisitsPage/></RequireRole>} />
              <Route path="estado" element={<RequireRole allow={["RESIDENTE"]}><EstadoCuenta/></RequireRole>} />
          

          {/* Avisos */}
          <Route
            path="admin/avisos"
            element={
              <RequireRole allow={["ADMIN"]}>
                <AdminAvisosPage />
              </RequireRole>
            }
          />
          <Route path="avisos" element={<MisAvisosPage />} />

          {/* Tareas */}
          <Route
            path="admin/tareas"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <AdminTareasPage />
              </RequireRole>
            }
          />
          <Route path="tareas" element={<MisTareasPage />} />
          <Route
            path="admin/asignar-tareas"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <AsignarTareasPage />
              </RequireRole>
            }
          />

          {/* Estado de cuenta */}
          <Route path="estado-cuenta" element={<EstadoCuentaPage />} />

          {/* Áreas comunes (usuarios) */}
          <Route path="areas/disponibilidad" element={<AreasDisponibilidad />} />
          <Route path="areas/reservar" element={<AreaReservaNueva />} />

          {/* Áreas comunes (admin) */}
          <Route
            path="admin/areas-comunes"
            element={
              <RequireRole allow={["ADMIN"]}>
                <AdminAreasPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/areas-comunes/reglas"
            element={
              <RequireRole allow={["ADMIN"]}>
                <AdminAreaReglasPage />
              </RequireRole>
            }
          />

          {/* Vehículos */}
          <Route
            path="vehiculos"
            element={
              <RequireRole allow={["ADMIN", "STAFF", "RESIDENT"]}>
                <VehiculosPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/solicitudes-vehiculo"
            element={
              <RequireRole allow={["ADMIN", "STAFF"]}>
                <SolicitudesVehiculoPage />
              </RequireRole>
            }
          />

          {/* fallback dentro autenticado */}
          <Route path="*" element={<Navigate to="dashboard" replace />} />
        </Route>

        {/* fallback global */}
        <Route path="*" element={<Navigate to="/signin" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
