// src/pages/PayPage.jsx
import React, { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { CardElement, useStripe, useElements } from "@stripe/react-stripe-js";
import { iniciarPagoOnline } from "../api/pagos";

export default function PayPage() {
  const { id } = useParams();           // cuotaId
  const navigate = useNavigate();
  const stripe = useStripe();
  const elements = useElements();

  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    setMsg("");

    try {
      // 1) pides el client_secret a tu backend
      const { client_secret } = await iniciarPagoOnline(Number(id), amount || undefined);

      // 2) confirmas con Stripe usando la tarjeta del CardElement
      const result = await stripe.confirmCardPayment(client_secret, {
        payment_method: { card: elements.getElement(CardElement) },
      });

      if (result.error) {
        setMsg(`❌ ${result.error.message}`);
      } else if (result.paymentIntent.status === "succeeded") {
        setMsg("✅ Pago completado");
        // opcional: volver al estado de cuenta
        setTimeout(() => navigate("/estado-cuenta"), 1000);
      } else {
        setMsg(`Estado: ${result.paymentIntent.status}`);
      }
    } catch (err) {
      setMsg(err?.detail || err?.message || "Error al iniciar el pago");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 460, margin: "24px auto" }}>
      <h2>Pagar cuota #{id}</h2>
      <form onSubmit={handleSubmit}>
        <label style={{ display: "block", marginBottom: 8 }}>
          Monto (deja vacío para pagar el saldo completo)
        </label>
        <input
          type="number"
          min="0"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="Ej. 10.50"
          style={{ width: "100%", padding: 8, marginBottom: 12 }}
        />

        <label style={{ display: "block", marginBottom: 8 }}>Tarjeta</label>
        <div style={{ border: "1px solid #ddd", borderRadius: 6, padding: 12, marginBottom: 12 }}>
          <CardElement options={{ hidePostalCode: true }} />
        </div>

        <button type="submit" disabled={!stripe || loading} style={{ padding: "10px 16px" }}>
          {loading ? "Procesando..." : "Pagar"}
        </button>

        {msg && <p style={{ marginTop: 12 }}>{msg}</p>}
      </form>

      <div style={{ marginTop: 16, fontSize: 13, color: "#666" }}>
        Tarjeta de prueba: <code>4242 4242 4242 4242</code> — fecha futura, CVC 123.
      </div>
    </div>
  );
}
