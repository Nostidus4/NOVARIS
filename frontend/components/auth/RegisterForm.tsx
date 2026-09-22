"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  LoaderCircle,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import {
  clearStoredSession,
  getStoredSession,
  registerWithPassword,
  verifySession,
} from "@/lib/auth";
import { assetPath } from "@/lib/paths";
import { QuantumShieldIcon } from "./QuantumShieldIcon";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function RegisterForm() {
  const router = useRouter();
  const nameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const confirmId = useId();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmationEmail, setConfirmationEmail] = useState<string | null>(null);

  useEffect(() => {
    const session = getStoredSession();
    if (!session) return;
    verifySession(session)
      .then(() => router.replace("/overview"))
      .catch(() => clearStoredSession());
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const normalizedName = displayName.trim().replace(/\s+/g, " ");
    const normalizedEmail = email.trim().toLowerCase();

    if (normalizedName.length < 2) {
      setError("Vui lòng nhập họ tên có ít nhất 2 ký tự.");
      return;
    }
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setError("Vui lòng nhập một địa chỉ email hợp lệ.");
      return;
    }
    if (password.length < 8) {
      setError("Mật khẩu cần có ít nhất 8 ký tự.");
      return;
    }
    if (password !== confirmation) {
      setError("Mật khẩu xác nhận chưa khớp.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await registerWithPassword(
        normalizedName,
        normalizedEmail,
        password,
      );
      if (result.session) {
        await verifySession(result.session);
        router.replace("/overview");
        return;
      }
      setConfirmationEmail(normalizedEmail);
    } catch (cause) {
      clearStoredSession();
      setError(
        cause instanceof Error
          ? cause.message
          : "Không thể tạo tài khoản. Vui lòng thử lại.",
      );
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
          <div><strong>NOVARIS</strong><span>Q‑SHIELD</span></div>
        </div>
        <Link className="auth-back" href="/">
          <ArrowLeft size={19} />
          Quay lại trang chủ
        </Link>
      </header>

      <div className="auth-layout auth-layout-register">
        <section className="auth-intro auth-register-intro">
          <p className="auth-kicker">JOIN THE QUANTUM WORKSPACE</p>
          <h1>Quantum Access</h1>
          <h2>Tạo không gian phân tích của bạn</h2>
          <p>
            Đăng ký một tài khoản bảo mật để truy cập workflow mô phỏng rủi ro và bằng
            chứng tối ưu của Q‑SHIELD.
          </p>
        </section>

        <section className="auth-card auth-card-register" aria-labelledby="register-title">
          <div className="auth-card-glow" />
          {confirmationEmail ? (
            <div className="auth-confirmation" role="status">
              <span><CheckCircle2 size={36} /></span>
              <p className="auth-card-kicker">REGISTRATION COMPLETE</p>
              <h2>Kiểm tra email của bạn</h2>
              <p>
                Liên kết xác nhận đã được gửi tới <strong>{confirmationEmail}</strong>.
                Xác nhận email rồi quay lại đăng nhập.
              </p>
              <Link className="auth-submit" href="/login">
                Đến trang đăng nhập <ArrowRight size={19} />
              </Link>
            </div>
          ) : (
            <>
              <QuantumShieldIcon />
              <div className="auth-card-heading">
                <p className="auth-card-kicker">CREATE SECURE ACCESS</p>
                <h2 id="register-title">Đăng ký tài khoản</h2>
                <p>Bắt đầu truy cập không gian dữ liệu và công nghệ tiên tiến</p>
              </div>

              <form className="auth-form auth-register-form" onSubmit={handleSubmit} noValidate>
                <AuthField
                  id={nameId}
                  label="Họ và tên"
                  icon={<UserRound size={19} />}
                  input={
                    <input
                      id={nameId}
                      type="text"
                      autoComplete="name"
                      placeholder="Nhập họ và tên của bạn"
                      value={displayName}
                      onChange={(event) => setDisplayName(event.target.value)}
                      disabled={submitting}
                      required
                    />
                  }
                />
                <AuthField
                  id={emailId}
                  label="Email"
                  icon={<Mail size={19} />}
                  input={
                    <input
                      id={emailId}
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      placeholder="Nhập email của bạn"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      disabled={submitting}
                      required
                    />
                  }
                />
                <AuthField
                  id={passwordId}
                  label="Mật khẩu"
                  icon={<LockKeyhole size={19} />}
                  action={
                    <button
                      className="auth-password-toggle"
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                    >
                      {showPassword ? <EyeOff size={19} /> : <Eye size={19} />}
                    </button>
                  }
                  input={
                    <input
                      id={passwordId}
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="Tối thiểu 8 ký tự"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      disabled={submitting}
                      required
                    />
                  }
                />
                <AuthField
                  id={confirmId}
                  label="Xác nhận mật khẩu"
                  icon={<ShieldCheck size={19} />}
                  input={
                    <input
                      id={confirmId}
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="Nhập lại mật khẩu"
                      value={confirmation}
                      onChange={(event) => setConfirmation(event.target.value)}
                      disabled={submitting}
                      required
                    />
                  }
                />

                {error ? <div className="auth-error" role="alert">{error}</div> : null}

                <button className="auth-submit" type="submit" disabled={submitting}>
                  <span>{submitting ? "Đang tạo tài khoản…" : "Tạo tài khoản"}</span>
                  {submitting ? (
                    <LoaderCircle className="auth-spin" size={20} />
                  ) : (
                    <ArrowRight size={21} />
                  )}
                </button>
                <p className="auth-switch">
                  Đã có tài khoản? <Link href="/login">Đăng nhập</Link>
                </p>
              </form>
            </>
          )}
        </section>
      </div>
    </main>
  );
}

function AuthField({
  id,
  label,
  icon,
  input,
  action,
}: {
  id: string;
  label: string;
  icon: React.ReactNode;
  input: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="auth-field">
      <label htmlFor={id}>{label}</label>
      <div className="auth-input-wrap">
        {icon}
        {input}
        {action}
      </div>
    </div>
  );
}
