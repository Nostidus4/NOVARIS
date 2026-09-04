import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Atom,
  Database,
  EyeOff,
  FileText,
  Gauge,
  Ban,
  CheckCircle2,
  Scale,
  ShieldCheck,
  ShieldHalf,
  Sigma,
  Waves,
} from "lucide-react";
import { assetPath } from "@/lib/paths";
import { LandingNav } from "@/components/landing/LandingNav";
import { Hero } from "@/components/landing/Hero";
import { Reveal } from "@/components/landing/Reveal";
import "./landing.css";

export const metadata: Metadata = {
  title: "NOVARIS Q-SHIELD — Phòng vệ rủi ro danh mục bằng QUBO",
  description:
    "Prototype mô phỏng stress thị trường VN30, đo CVaR trên phân phối lỗ và tối ưu hành động phòng vệ tiền mặt bằng QUBO/QAOA, đối chiếu exact solver.",
};

const STATS = [
  { value: "30", label: "Mã VN30 trong universe" },
  { value: "20-bit", label: "QUBO, 4 mức hành động" },
  { value: "α = 0.95", label: "CVaR — Rockafellar–Uryasev" },
  { value: "2²⁰", label: "Không gian nghiệm exact đối chiếu QAOA" },
];

const VALUES = [
  {
    icon: Activity,
    title: "Regime theo thống kê, không theo state id",
    copy: "HMM 3 trạng thái xếp hạng theo return / volatility / drawdown rồi mới gán nhãn Normal – Volatile – Stress, để tránh đảo nhãn giữa các lần chạy.",
  },
  {
    icon: Sigma,
    title: "CVaR đúng định nghĩa",
    copy: "Loss = −return, CVaR₀.₉₅ là trung bình phần đuôi của phân phối lỗ (không phải giá trị tại phân vị). Mọi so sánh trước–sau dùng cùng một quy ước dấu.",
  },
  {
    icon: ShieldCheck,
    title: "Chấm lại bằng true CVaR",
    copy: "Nghiệm QAOA không được chọn chỉ theo QUBO energy — bắt buộc rerank + local polishing (±5pp, zero-lock) trước khi đưa vào bằng chứng.",
  },
];

const PIPELINE = [
  {
    step: "01",
    title: "Data",
    icon: Database,
    href: "/data",
    copy: "Làm sạch 30 mã VN30, không forward-fill lợi suất, giá thiếu và outlier được gắn cờ, không tự xóa.",
  },
  {
    step: "02",
    title: "Regime",
    icon: Activity,
    href: "/regime",
    copy: "HMM suy luận trạng thái thị trường theo 5 đặc trưng, covariance diag.",
  },
  {
    step: "03",
    title: "Scenarios",
    icon: Waves,
    href: "/scenarios",
    copy: "Moving-block bootstrap sinh kịch bản stress, giữ nguyên tương quan chéo giữa các tài sản.",
  },
  {
    step: "04",
    title: "Risk",
    icon: ShieldHalf,
    href: "/risk",
    copy: "Tính CVaR 95% trên phân phối lỗ, chọn dynamic top-10 ứng viên phòng vệ.",
  },
  {
    step: "05",
    title: "Quantum",
    icon: Atom,
    href: "/quantum",
    copy: "QUBO 20-bit, 4 mức 0/10/20/30%; đối chiếu exact 2²⁰ và QAOA (qiskit 2.x).",
  },
  {
    step: "06",
    title: "Report",
    icon: FileText,
    href: "/report",
    copy: "Rerank/polish, đóng gói bằng chứng CVaR trước–sau cho dashboard và UAT.",
  },
];

const PRINCIPLES = [
  {
    icon: Ban,
    title: "Không tuyên bố quantum advantage",
    copy: "QAOA thua exact hay thua classical thì báo cáo trung thực, không tô hồng kết quả.",
  },
  {
    icon: CheckCircle2,
    title: "Exact solver là thước đo",
    copy: "Duyệt hết 2²⁰ tổ hợp làm ground truth chấm QAOA — không bỏ bớt để tiết kiệm thời gian.",
  },
  {
    icon: Scale,
    title: "Không dùng dữ liệu tương lai",
    copy: "Rolling feature chỉ dùng dữ liệu đến thời điểm t; scaler fit trên train, transform cho validation/test.",
  },
  {
    icon: EyeOff,
    title: "Không tự xóa outlier",
    copy: "Giá trị bất thường được gắn cờ và ghi log để review, không âm thầm loại khỏi tập dữ liệu.",
  },
];

const SCOPE_ITEMS = [
  {
    title: "Không phải tư vấn đầu tư",
    copy: "Hệ thống mô tả kịch bản rủi ro và đề xuất hành động phòng vệ để tham khảo, không phải khuyến nghị mua bán.",
  },
  {
    title: "Universe cố định 30 mã VN30",
    copy: "Đã snapshot; hành động phòng vệ giới hạn ở 4 mức 0/10/20/30% tiền mặt, tổng tỷ trọng luôn bằng 1.0.",
  },
  {
    title: "Không dữ liệu real-time, không hardware lượng tử thật",
    copy: "QAOA chạy trên simulator (StatevectorSampler); backends/hardware.py cố ý để trống theo kế hoạch.",
  },
  {
    title: "Trạng thái: NON_BASELINE_RUN",
    copy: "workflow_update giữ trạng thái này cho đến khi đủ 3 gate phê duyệt: data_gate, scenario_gate, product_gate.",
  },
];

export default function LandingPage() {
  return (
    <div className="lp">
      <LandingNav />

      <main>
        <Hero stats={STATS} />

        <section className="lp-section">
          <div className="lp-shell">
            <Reveal className="lp-section-head">
              <div className="lp-kicker">Vì sao Q-SHIELD</div>
              <h2 className="lp-h2">Kỷ luật số trước, giao diện sau</h2>
              <p className="lp-lead">
                Ba nguyên tắc tài chính giữ cho mọi con số hiển thị trên console có thể truy vết
                lại tận artifact.
              </p>
            </Reveal>
            <div className="lp-cards-3">
              {VALUES.map((v, i) => (
                <Reveal delay={i * 0.08} key={v.title}>
                  <article className="lp-card">
                    <div className="lp-card-icon">
                      <v.icon size={19} />
                    </div>
                    <div className="lp-card-title">{v.title}</div>
                    <p className="lp-card-copy">{v.copy}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section" id="pipeline">
          <div className="lp-shell">
            <Reveal className="lp-section-head">
              <div className="lp-kicker">Quy trình</div>
              <h2 className="lp-h2">Từ dữ liệu đến quyết định, 6 chặng</h2>
              <p className="lp-lead">
                Mỗi chặng có trang bằng chứng riêng trong console — bấm vào để xem trực tiếp.
              </p>
            </Reveal>
            <div className="lp-pipeline">
              {PIPELINE.map((p, i) => (
                <Reveal delay={i * 0.06} key={p.step}>
                  <Link className="lp-node" href={p.href}>
                    <div className="lp-node-icon">
                      <p.icon size={16} />
                    </div>
                    <div className="lp-node-step">{p.step}</div>
                    <div className="lp-node-title">{p.title}</div>
                    <p className="lp-node-copy">{p.copy}</p>
                    <span className="lp-node-go">
                      Mở trang <ArrowRight size={11} />
                    </span>
                  </Link>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section" id="principles">
          <div className="lp-shell">
            <Reveal className="lp-section-head">
              <div className="lp-kicker">Cam kết minh bạch</div>
              <h2 className="lp-h2">Bốn ranh giới không được vượt qua</h2>
              <p className="lp-lead">
                Vi phạm những điều này làm sai kết quả, không chỉ làm xấu code — nên chúng được
                chốt cứng ở tầng quy tắc.
              </p>
            </Reveal>
            <div className="lp-cards-4">
              {PRINCIPLES.map((p, i) => (
                <Reveal delay={i * 0.08} key={p.title}>
                  <article className="lp-card">
                    <div className="lp-card-icon">
                      <p.icon size={18} />
                    </div>
                    <div className="lp-card-title">{p.title}</div>
                    <p className="lp-card-copy">{p.copy}</p>
                  </article>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section" id="scope">
          <div className="lp-shell">
            <Reveal className="lp-scope">
              <div>
                <span className="lp-scope-status">
                  <Gauge size={12} />
                  NON_BASELINE_RUN
                </span>
                <h2 className="lp-scope-title">Giới hạn phạm vi, nói thẳng</h2>
                <p className="lp-scope-copy">
                  Đây là prototype dự thi 7 ngày, không phải sản phẩm tư vấn đầu tư. Phạm vi được
                  đóng băng để tập trung đúng vào baseline <code>workflow_update</code>.
                </p>
              </div>
              <div className="lp-scope-list">
                {SCOPE_ITEMS.map((s) => (
                  <div className="lp-scope-item" key={s.title}>
                    <ShieldCheck size={15} />
                    <div>
                      <strong>{s.title}</strong> — {s.copy}
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </section>

        <section className="lp-cta">
          <div className="lp-shell">
            <Reveal className="lp-cta-box">
              <div className="lp-kicker">Sẵn sàng xem bằng chứng</div>
              <h2 className="lp-h2">Mở console để xem CVaR trước–sau hedge</h2>
              <p className="lp-lead">
                Toàn bộ số liệu đọc trực tiếp từ artifact của lần chạy pipeline gần nhất.
              </p>
              <div className="lp-cta-actions">
                <Link href="/overview" className="lp-btn lp-btn-primary">
                  Vào Console
                  <ArrowRight size={15} />
                </Link>
              </div>
            </Reveal>
          </div>
        </section>
      </main>

      <footer className="lp-footer" id="contact">
        <div className="lp-shell">
          <div className="lp-footer-row">
            <div>
              <div className="lp-footer-brand">
                <Image
                  src={assetPath("/novaris-mark.png")}
                  alt="NOVARIS"
                  width={24}
                  height={24}
                />
                NOVARIS Q-SHIELD
              </div>
              <p className="lp-footer-tagline">
                Risk Intelligence Console cho danh mục VN30 — mô phỏng stress, đo CVaR, tối ưu
                phòng vệ tiền mặt bằng QUBO/QAOA.
              </p>
            </div>
            <nav className="lp-footer-links">
              <Link href="/overview">Console</Link>
              <a href="#pipeline">Quy trình</a>
              <a href="#principles">Minh bạch</a>
              <a href="#scope">Giới hạn</a>
            </nav>
          </div>
          <div className="lp-footer-bottom">
            <span>© 2026 Novaris. Prototype dự thi — không phải khuyến nghị đầu tư.</span>
            <span>VN30 universe · CVaR 95% (loss) · qiskit 2.x</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
