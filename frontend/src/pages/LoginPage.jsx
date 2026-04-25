import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Wallet, Lock, EnvelopeSimple } from "@phosphor-icons/react";

export default function LoginPage() {
  const { login, error, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("admin@crackerpro.com");
  const [password, setPassword] = useState("Admin@123");
  const [busy, setBusy] = useState(false);

  React.useEffect(() => {
    if (user && user.id) navigate("/dashboard", { replace: true });
  }, [user, navigate]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const ok = await login(email, password);
    setBusy(false);
    if (ok) navigate("/dashboard", { replace: true });
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left: hero */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-[#111110]">
        <img
          src="https://images.pexels.com/photos/3137084/pexels-photo-3137084.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=900&w=1200"
          alt="Modern architecture"
          className="absolute inset-0 w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/30 to-black/70" />
        <div className="relative z-10 flex flex-col justify-between p-12 text-white w-full">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[#A67C00] flex items-center justify-center">
              <Wallet weight="bold" size={22} className="text-black" />
            </div>
            <div>
              <div className="font-display text-xl font-bold tracking-tight">CRacker Pro</div>
              <div className="text-[10px] tracking-overline text-[#D4AF37]">Business Finance Platform</div>
            </div>
          </div>
          <div>
            <div className="text-[10px] tracking-overline text-[#D4AF37] mb-3">Project Commercial Lifecycle</div>
            <h2 className="font-display text-4xl xl:text-5xl font-bold leading-tight tracking-tight">
              From Pipeline to Closure.
              <br />
              <span className="text-[#D4AF37]">Engineered for finance.</span>
            </h2>
            <p className="mt-6 text-white/70 max-w-md text-sm leading-relaxed">
              Replace fragile Excels with audit-tracked workflows, configurable approvals, and a real-time
              dashboard built for CFOs, controllers, and project owners.
            </p>
          </div>
          <div className="text-[10px] tracking-overline text-white/40">© CRacker Pro · Confidential · Authorised access only</div>
        </div>
      </div>

      {/* Right: form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 bg-[#FAFAF8]">
        <form onSubmit={onSubmit} className="w-full max-w-sm" data-testid="login-form">
          <div className="text-[10px] tracking-overline text-[#5E5E5A] mb-3">Sign in to your workspace</div>
          <h1 className="font-display text-3xl font-bold tracking-tight text-[#111110] mb-1">Welcome back</h1>
          <p className="text-sm text-[#5E5E5A] mb-8">Use your CRacker Pro credentials. Passwords are admin-managed.</p>

          <label className="block text-[11px] tracking-overline text-[#5E5E5A] mb-1.5">Email</label>
          <div className="relative mb-4">
            <EnvelopeSimple size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5E5E5A]" />
            <input
              type="email"
              required
              className="input pl-9"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="login-email"
              autoComplete="email"
            />
          </div>

          <label className="block text-[11px] tracking-overline text-[#5E5E5A] mb-1.5">Password</label>
          <div className="relative mb-2">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5E5E5A]" />
            <input
              type="password"
              required
              className="input pl-9"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="login-password"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <div className="text-xs text-[#991B1B] bg-[#fdeaea] border border-[#f1c2c2] p-2 mt-3" data-testid="login-error">
              {error}
            </div>
          )}

          <button type="submit" disabled={busy} className="btn-primary w-full mt-6" data-testid="login-submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <div className="mt-6 text-[11px] text-[#5E5E5A] border-t border-[#E5E5E0] pt-4">
            Forgot your password? Contact your CRacker Pro administrator. <span className="text-[#A67C00]">No OTP-based reset.</span>
          </div>
        </form>
      </div>
    </div>
  );
}
