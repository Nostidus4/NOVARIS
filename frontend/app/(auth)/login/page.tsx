import type { Metadata } from "next";
import { LoginForm } from "@/components/auth/LoginForm";

export const metadata: Metadata = {
  title: "Đăng nhập — NOVARIS Q-SHIELD",
  description: "Đăng nhập an toàn vào Q-SHIELD Risk Intelligence Console",
};

export default function LoginPage() {
  return <LoginForm />;
}
