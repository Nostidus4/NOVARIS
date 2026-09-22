import type { Metadata } from "next";
import { RegisterForm } from "@/components/auth/RegisterForm";

export const metadata: Metadata = {
  title: "Đăng ký — NOVARIS Q-SHIELD",
  description: "Tạo tài khoản truy cập Q-SHIELD Risk Intelligence Console",
};

export default function RegisterPage() {
  return <RegisterForm />;
}
