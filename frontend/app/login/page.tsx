"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { loginApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await loginApi(email, password);
      localStorage.setItem("access_token", res.access_token);
      localStorage.setItem("user_role", res.user.role);
      router.push(`/dashboard/${res.user.role}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ padding: 24, maxWidth: 520, margin: "0 auto" }}>
      <h1>Sign In</h1>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 12 }}>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Email</span>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            placeholder="manager@gmail.com"
            style={{ padding: 10 }}
          />
        </label>
        <label style={{ display: "grid", gap: 6 }}>
          <span>Password</span>
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            required
            placeholder="manager@123"
            style={{ padding: 10 }}
          />
        </label>

        {error ? (
          <div style={{ color: "crimson" }}>
            {error}
          </div>
        ) : null}

        <button type="submit" disabled={loading} style={{ padding: 10 }}>
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <section style={{ marginTop: 18, fontSize: 13, opacity: 0.85 }}>
        <div>Demo roles exist in Phase 1 DB seed:</div>
        <div>Admin: admin@gmail.com</div>
        <div>Manager: manager@gmail.com</div>
        <div>Employee: employee@gmail.com</div>
      </section>
    </main>
  );
}

