"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Check,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
  ShieldCheck,
} from "lucide-react";
import {
  clearStoredSession,
  getStoredSession,
  loginWithPassword,
  safeNextPath,
  verifySession,
} from "@/lib/auth";
import { assetPath } from "@/lib/paths";
import { QuantumShieldIcon } from "./QuantumShieldIcon";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginForm() {
  const router = useRouter();
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const session = getStoredSession();
    if (!session) return;
    verifySession(session)
      .then(() => {
        const next = safeNextPath(new URLSearchParams(window.location.search).get("next"));
        router.replace(next);
      })
      .catch(() => undefined);
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const normalizedEmail = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError("Vui lòng nhập một địa chỉ email hợp lệ.");
      return;
    }
    if (password.length < 6) {
      setError("Mật khẩu cần có ít nhất 6 ký tự.");
      return;
    }

    setSubmitting(true);
    try {
      const session = await loginWithPassword(normalizedEmail, password, remember);
      await verifySession(session);
      const next = safeNextPath(new URLSearchParams(window.location.search).get("next"));
      router.replace(next);
    } catch (cause) {
      clearStoredSession();
      setError(cause instanceof Error ? cause.message : "Không thể đăng nhập. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main
      className="auth-page"
      style={{ backgroundImage: `url(${assetPath("/Authentication.png")})` }}
    >
      <div className="auth-page-shade" />
      <header className="auth-header">
        <div className="auth-brand" aria-label="NOVARIS Q-SHIELD">
          <Image
            src={assetPath("/novaris-mark.png")}
            alt=""
            width={62}
            height={62}
            priority
          />
          <div>
            <strong>NOVARIS</strong>
            <span>Q‑SHIELD</span>
          </div>
        </div>
        <Link className="auth-back" href="/">
          <ArrowLeft size={19} />
          Quay lại trang chủ
        </Link>
      </header>

      <div className="auth-layout">
        <section className="auth-intro" aria-labelledby="auth-intro-title">
          <p className="auth-kicker">QUANTUM RISK INTELLIGENCE</p>
          <h1 id="auth-intro-title">Quantum Access</h1>
          <h2>Truy cập nền tảng lượng tử</h2>
          <p>
            Kết nối đến hệ sinh thái mô phỏng rủi ro, AI và tối ưu lượng tử để khám phá
            những quyết định vững vàng hơn.
          </p>
          <div className="auth-features">
            <Feature icon={<ShieldCheck size={21} />} title="Quantum Security" text="Bảo mật lượng tử" />
            <Feature icon={<BrainCircuit size={21} />} title="AI Workspace" text="Không gian AI thông minh" />
            <Feature icon={<BarChart3 size={21} />} title="Risk Analytics" text="Phân tích có bằng chứng" />
          </div>
        </section>

        <section className="auth-card" aria-labelledby="login-title">
          <div className="auth-card-glow" />
          <QuantumShieldIcon />
          <div className="auth-card-heading">
            <p className="auth-card-kicker">SECURE CONSOLE</p>
            <h2 id="login-title">Đăng nhập hệ thống lượng tử</h2>
            <p>Truy cập an toàn vào không gian dữ liệu và công nghệ tiên tiến</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <div className="auth-field">
              <label htmlFor={emailId}>Email</label>
              <div className="auth-input-wrap">
                <Mail size={19} />
                <input
                  id={emailId}
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="Nhập email của bạn"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  disabled={submitting}
                  aria-invalid={Boolean(error)}
                  required
                />
              </div>
            </div>

            <div className="auth-field">
              <label htmlFor={passwordId}>Mật khẩu</label>
              <div className="auth-input-wrap">
                <LockKeyhole size={19} />
                <input
                  id={passwordId}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Nhập mật khẩu của bạn"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  disabled={submitting}
                  aria-invalid={Boolean(error)}
                  required
                />
                <button
                  className="auth-password-toggle"
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                </button>
              </div>
            </div>

            <div className="auth-options">
              <label className="auth-checkbox">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                  disabled={submitting}
                />
                <span className="auth-checkbox-box"><Check size={13} /></span>
                Ghi nhớ đăng nhập
              </label>
              <span className="auth-help" title="Liên hệ quản trị viên để đặt lại mật khẩu">
                Quên mật khẩu?
              </span>
            </div>

            {error ? (
              <div className="auth-error" role="alert">{error}</div>
            ) : null}

            <button className="auth-submit" type="submit" disabled={submitting}>
              <span>{submitting ? "Đang xác thực…" : "Đăng nhập"}</span>
              {submitting ? <LoaderCircle className="auth-spin" size={20} /> : <ArrowRight size={21} />}
            </button>

            <p className="auth-switch">
              Chưa có tài khoản? <Link href="/register">Đăng ký ngay</Link>
            </p>
          </form>

          <div className="auth-trust">
            <ShieldCheck size={17} />
            <span>Bảo mật lượng tử</span><i />
            <span>Mã hóa đầu cuối</span><i />
            <span>Tuân thủ chuẩn quốc tế</span>
          </div>
        </section>
      </div>
    </main>
  );
}

function Feature({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="auth-feature">
      <span>{icon}</span>
      <div><strong>{title}</strong><small>{text}</small></div>
    </div>
  );
}
