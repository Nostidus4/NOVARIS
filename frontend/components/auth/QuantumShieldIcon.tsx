import { LockKeyhole, Shield } from "lucide-react";

export function QuantumShieldIcon() {
  return (
    <div className="auth-emblem" aria-hidden="true">
      <span className="auth-orbit auth-orbit-one" />
      <span className="auth-orbit auth-orbit-two" />
      <Shield className="auth-shield" size={54} strokeWidth={1.45} />
      <LockKeyhole className="auth-lock" size={19} strokeWidth={1.8} />
    </div>
  );
}
