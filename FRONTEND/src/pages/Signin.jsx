import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { login, me, getRole } from "../api/auth";
import "./Signin.css";
import logo from "../assets/logo.svg";


export default function Signin() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    setLoading(true);
    setError("");

    try {
      await login(username.trim(), password); // 1) POST -> guarda token
      const profile = await me(); // 2) GET perfil con token
      localStorage.setItem("me", JSON.stringify(profile));
      navigate(from || "/dashboard", { replace: true });
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.non_field_errors?.[0] ||
        err?.message ||
        "Usuario o contraseña incorrectos";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signin">
      <form className="signin__card" onSubmit={handleSubmit} noValidate>
        <img src={logo} alt="Logo" className="signin__logo" />
        <h2 className="signin__title">Iniciar Sesión</h2>
        <p className="signin__subtitle">
          Bienvenido a un Condominio Inteligente
        </p>

        {error && <div className="signin__error">{error}</div>}

        <div className="signin__group">
          <label htmlFor="user" className="signin__label">
            Usuario
          </label>
          <input
            id="user"
            className="signin__input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
            placeholder="Tu usuario"
          />
        </div>

        <div className="signin__group">
          <label htmlFor="pass" className="signin__label">
            Contraseña
          </label>
          <input
            id="pass"
            type="password"
            className="signin__input"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            placeholder="••••••••"
          />
        </div>

        <div className="signin__actions">
          <button
            type="submit"
            className={`signin__button${loading ? " is-loading" : ""}`}
            disabled={loading}
          >
            {loading ? "Ingresando..." : "Ingresar"}
          </button>
        </div>

        <p className="signin__muted">
          ¿Olvidaste tu contraseña?{" "}
          <a
            href="https://wa.link/z85omz"
            target="_blank"
            rel="noopener noreferrer"
          >
            Contacta al admin
          </a>
        </p>
      </form>
    </div>
  );
}
