import type { Metadata } from "next";
import LandingExperience from "@/components/landing/LandingExperience";

export const metadata: Metadata = {
  title: "NOVARIS Q-SHIELD — Quantum Risk Intelligence",
  description:
    "Nền tảng phân tích chế độ thị trường, mô phỏng stress và hỗ trợ quyết định có bằng chứng.",
};

export default function LandingPage() {
  return <LandingExperience />;
}
