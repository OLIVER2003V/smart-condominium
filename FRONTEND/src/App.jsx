import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Signin from "./pages/Signin";
import Dashboard from "./pages/Dashboard";
import Me from "./pages/Me";
import Layout from "./components/Layout";
import RequireAuth from "./components/RequireAuth";
import RequireRole from "./components/RequireRole";
import AdminUsers from "./pages/AdminUsers"; 
import RolesPage from "./pages/Roles";
import Permisos from "./pages/Permisos";
import UnitsPage from "./pages/UnitsPage";
import CuotasPage from "./pages/CuotasPage";
import InfraccionesPage from "./pages/InfraccionesPagre";
import EstadoCuentaPage from "./pages/EstadoCuentaPage";
import PayPage from "./pages/PayPage";
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Pública */}
        <Route path="/signin" element={<Signin />} />

        {/* Zona autenticada */}
        <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="me" element={<Me />} />

          {/* Solo ADMIN */}
          <Route
            path="admin/usuarios"
            element={
              <RequireRole allow={["ADMIN"]}>
                <AdminUsers />
              </RequireRole>
            }
          />
          {/* Solo ADMIN para los roles */}
          <Route
            path="admin/roles"
            element={
              <RequireRole allow={["ADMIN"]}>
                <RolesPage />
              </RequireRole>
            }
          />
          <Route
            path="admin/permissions"
            element={
              <RequireRole allow={["ADMIN"]}>
                <Permisos /> {/* 👈 nueva página */}
              </RequireRole>
            }
          />
          <Route
            path="admin/unidades"
            element={
              <RequireRole allow={["ADMIN"]}>
                <UnitsPage /> {/* 👈 nueva página */}
              </RequireRole>
            }
          />
          <Route
            path="admin/cuotas"
            element={
              <RequireRole allow={["ADMIN"]}>
                <CuotasPage /> {/* 👈 nueva página */}
              </RequireRole>
            }
          />
          <Route
            path="admin/infracciones"
            element={
              <RequireRole allow={["ADMIN"]}>
                <InfraccionesPage /> {/* 👈 nueva página */}
              </RequireRole>
            }
          />
         
          <Route path="/estado-cuenta" element={<EstadoCuentaPage />} />
          
          <Route path="/pay/:id" element={<PayPage />} />
          {/* 404 dentro de la zona autenticada → lleva al dashboard */}
          <Route path="*" element={<Navigate to="dashboard" replace />} />
        </Route>
        
          


        {/* 404 global (no autenticado) → login */}
        <Route path="*" element={<Navigate to="/signin" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
