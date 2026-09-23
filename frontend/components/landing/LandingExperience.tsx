"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import {
  ArrowDown, ArrowRight, Atom, BarChart3, BrainCircuit, ChevronRight,
  Database, FileCheck2, Fingerprint, Gauge, Layers3, LockKeyhole, Menu, Orbit,
  Radar, ShieldCheck, Sparkles, X, Zap,
} from "lucide-react";
import { getStoredSession } from "@/lib/auth";
import { assetPath } from "@/lib/paths";

const capabilities = [
  { icon: Radar, title: "Risk Intelligence", text: "Nhận diện chế độ thị trường, theo dõi tín hiệu bất định và đặt rủi ro vào đúng bối cảnh." },
  { icon: Layers3, title: "Scenario Simulation", text: "Mô phỏng kịch bản cơ sở và stress để quan sát phân phối tổn thất trước khi ra quyết định." },
  { icon: Atom, title: "Decision Optimization", text: "Xếp hạng ứng viên theo ràng buộc, sau đó đối chiếu kết quả bằng thước đo rủi ro thực tế." },
];

const workflow = [
  { icon: Database, title: "Data Gate", text: "Kiểm tra độ đầy đủ và tính hợp lệ của dữ liệu đầu vào." },
  { icon: Gauge, title: "Regime Detection", text: "Xác định trạng thái thị trường và mức độ bất định hiện tại." },
  { icon: Orbit, title: "Scenario Generation", text: "Sinh tập kịch bản cơ sở, bất lợi và cực đoan để kiểm thử." },
  { icon: BarChart3, title: "Risk Evaluation", text: "Đánh giá tail-risk và so sánh tác động giữa các kịch bản." },
  { icon: BrainCircuit, title: "Optimization", text: "Tối ưu lựa chọn theo mục tiêu và các ràng buộc đã cấu hình." },
  { icon: FileCheck2, title: "Evidence & Report", text: "Lưu kết quả, lý do xếp hạng và dữ liệu phục vụ kiểm chứng." },
];

const engineSteps = [
  { icon: Database, label: "Dữ liệu thị trường", detail: "Dữ liệu và kiểm soát chất lượng" },
  { icon: Radar, label: "Phân tích chế độ", detail: "Tín hiệu, ngữ cảnh và bất định" },
  { icon: Orbit, label: "Mô phỏng kịch bản", detail: "Base case và stress scenarios" },
  { icon: Zap, label: "Q-SHIELD Engine", detail: "Đánh giá, tối ưu và tái xếp hạng" },
  { icon: FileCheck2, label: "Console & Evidence", detail: "Kết quả minh bạch, có thể đối chiếu" },
];

const principles = [
  { icon: Fingerprint, title: "Evidence-first", text: "Mỗi kết quả được trình bày cùng dữ liệu, giả định và nguyên nhân hình thành." },
  { icon: FileCheck2, title: "Reproducible", text: "Cấu hình, thời điểm chạy và kết quả được giữ nhất quán để có thể kiểm tra lại." },
  { icon: ShieldCheck, title: "Human-controlled", text: "Người dùng kiểm soát ràng buộc và luôn là người phê duyệt quyết định cuối cùng." },
];

const heroPillars = [
  { icon: Database, title: "Data Quality", text: "Kiểm soát đầu vào" },
  { icon: Gauge, title: "Market Regime", text: "Nhận diện trạng thái" },
  { icon: Orbit, title: "Stress Scenarios", text: "Kiểm thử bất lợi" },
  { icon: FileCheck2, title: "Evidence-first", text: "Kết quả kiểm chứng" },
];

const navItems = [
  { id: "home", label: "Trang chủ" },
  { id: "capabilities", label: "Năng lực" },
  { id: "workflow", label: "Quy trình" },
  { id: "how-it-works", label: "Cách hoạt động" },
  { id: "transparency", label: "Minh bạch" },
];

function subscribeToAuth(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function getAuthSnapshot() {
  return Boolean(getStoredSession());
}

export default function LandingExperience() {
  const signedIn = useSyncExternalStore(subscribeToAuth, getAuthSnapshot, () => false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState("home");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const sections = navItems
      .map(({ id }) => document.getElementById(id))
      .filter((section): section is HTMLElement => Boolean(section));
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setActiveSection(visible.target.id);
      },
      { rootMargin: "-22% 0px -55% 0px", threshold: [0, 0.2, 0.5] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  const destination = signedIn ? "/overview" : "/login?next=/overview";
  const closeMenu = () => setMenuOpen(false);

  return (
    <main className="landing-page">
      <header className={`landing-header${scrolled ? " is-scrolled" : ""}`}>
        <div className="landing-header-inner">
          <Link className="landing-brand" href="/" aria-label="NOVARIS Q-SHIELD trang chủ">
            <Image src={assetPath("/novaris-mark.png")} alt="" width={58} height={58} priority />
            <div><strong>NOVARIS</strong><span>Q-SHIELD</span></div>
          </Link>
          <nav className={`landing-nav${menuOpen ? " is-open" : ""}`} aria-label="Điều hướng chính">
            {navItems.map(({ id, label }) => (
              <a
                className={activeSection === id ? "is-active" : undefined}
                href={`#${id}`}
                onClick={closeMenu}
                key={id}
              >
                {label}
              </a>
            ))}
            <Link className="landing-nav-mobile-cta" href={destination} onClick={closeMenu}>
              {signedIn ? "Mở Console" : "Đăng nhập"}<ArrowRight size={16} />
            </Link>
          </nav>
          <div className="landing-header-actions">
            {!signedIn && <Link className="landing-text-link" href="/login">Đăng nhập</Link>}
            <Link className="landing-header-cta" href={signedIn ? "/overview" : "/register"}>
              {signedIn ? "Mở Console" : "Bắt đầu ngay"}<ArrowRight size={16} />
            </Link>
            <button className="landing-menu-button" type="button" aria-label={menuOpen ? "Đóng menu" : "Mở menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>
              {menuOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
          </div>
        </div>
      </header>

      <section className="landing-hero" id="home" style={{ backgroundImage: `url(${assetPath("/Landing.png")})` }}>
        <div className="landing-hero-overlay" />
        <div className="landing-hero-content">
          <p className="landing-eyebrow"><Sparkles size={14} /> QUANTUM RISK INTELLIGENCE</p>
          <h1>Nhìn xuyên qua<br /><span>bất định thị trường</span></h1>
          <div className="landing-hero-emblem" aria-label="NOVARIS Q-SHIELD">
            <span className="landing-orbit landing-orbit-one" />
            <span className="landing-orbit landing-orbit-two" />
            <span className="landing-emblem-glow" />
            <Image src={assetPath("/novaris-mark.png")} alt="NOVARIS Q-SHIELD" width={150} height={150} priority />
          </div>
          <p className="landing-hero-description">Q-SHIELD kết nối dữ liệu, mô phỏng stress và tối ưu hóa trong một không gian hỗ trợ quyết định minh bạch, có thể kiểm chứng.</p>
          <div className="landing-actions">
            <a className="landing-primary" href="#capabilities">Khám phá nền tảng <ArrowRight size={18} /></a>
            <Link className="landing-secondary" href={destination}>{signedIn ? "Mở Console" : "Truy cập Console"}</Link>
          </div>
          <div className="landing-hero-pillars" aria-label="Các năng lực nổi bật">
            {heroPillars.map(({ icon: Icon, title, text }) => (
              <div className="landing-hero-pillar" key={title}>
                <span><Icon size={18} /></span>
                <div><strong>{title}</strong><small>{text}</small></div>
              </div>
            ))}
          </div>
        </div>
        <a className="landing-scroll" href="#capabilities" aria-label="Cuộn tới phần năng lực"><span>KHÁM PHÁ</span><ArrowDown size={17} /></a>
      </section>

      <section className="landing-section landing-capabilities" id="capabilities">
        <div className="landing-container">
          <div className="landing-section-heading">
            <p className="landing-kicker">NĂNG LỰC CỐT LÕI</p>
            <h2>Từ dữ liệu đến quyết định<br /><span>có bằng chứng.</span></h2>
            <p>Một workflow liền mạch giúp nhìn rõ rủi ro, thử nghiệm giả định và đánh giá kết quả.</p>
          </div>
          <div className="landing-capability-grid">
            {capabilities.map(({ icon: Icon, title, text }, index) => (
              <article className="landing-capability-card" key={title}>
                <div className="landing-card-top"><span className="landing-icon-box"><Icon size={23} /></span><span className="landing-card-number">0{index + 1}</span></div>
                <h3>{title}</h3><p>{text}</p><a href="#workflow">Khám phá quy trình <ChevronRight size={15} /></a>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-workflow-section" id="workflow" style={{ backgroundImage: `url(${assetPath("/Workflow.png")})` }}>
        <div className="landing-section-shade" />
        <div className="landing-container">
          <div className="landing-section-heading landing-section-heading-centered"><p className="landing-kicker">WORKFLOW</p><h2>Từ tín hiệu thị trường đến<br /><span>quyết định có thể kiểm chứng.</span></h2></div>
          <div className="landing-workflow-map">
            <svg
              className="landing-workflow-path"
              viewBox="0 0 1200 440"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <polyline points="100,229 300,176 500,246 700,180 900,238 1100,189" />
            </svg>
            {workflow.map(({ icon: Icon, title, text }, index) => (
              <article className="landing-workflow-step" key={title}>
                <div className="landing-workflow-card">
                  <div className="landing-workflow-card-head">
                    <span className="landing-workflow-icon"><Icon size={20} /></span>
                    <span className="landing-workflow-number">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                  </div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
                <span className="landing-workflow-node" aria-hidden="true"><i /></span>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-engine" id="how-it-works" style={{ backgroundImage: `url(${assetPath("/HowItWork.png")})` }}>
        <div className="landing-section-shade landing-engine-shade" />
        <div className="landing-container">
          <div className="landing-engine-intro"><p className="landing-kicker">CÁCH Q-SHIELD HOẠT ĐỘNG</p><h2>Một dòng dữ liệu.<br /><span>Một hệ thống thống nhất.</span></h2><p>Dữ liệu được kiểm tra, đặt vào bối cảnh, mô phỏng và đánh giá trước khi xuất hiện trong console dưới dạng kết quả có bằng chứng.</p></div>
          <div className="landing-engine-flow">
            {engineSteps.map(({ icon: Icon, label, detail }, index) => (
              <div className={`landing-engine-node${index === 3 ? " is-core" : ""}`} key={label}>
                <span><Icon size={index === 3 ? 25 : 20} /></span><div><strong>{label}</strong><small>{detail}</small></div>
                {index < engineSteps.length - 1 && <ChevronRight className="landing-engine-arrow" size={18} />}
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section landing-transparency" id="transparency">
        <div className="landing-container">
          <div className="landing-section-heading landing-section-heading-centered"><p className="landing-kicker">MINH BẠCH THEO THIẾT KẾ</p><h2>Không chỉ đưa ra kết quả.<br /><span>Q-SHIELD cho bạn thấy vì sao.</span></h2></div>
          <div className="landing-principle-grid">
            {principles.map(({ icon: Icon, title, text }) => <article className="landing-principle" key={title}><span><Icon size={24} /></span><h3>{title}</h3><p>{text}</p></article>)}
          </div>
          <p className="landing-disclaimer"><LockKeyhole size={15} /> Q-SHIELD là công cụ phân tích và hỗ trợ quyết định, không phải khuyến nghị đầu tư.</p>
        </div>
      </section>

      <section className="landing-cta-section">
        <div className="landing-cta-glow" />
        <div className="landing-container landing-cta-content">
          <div><p className="landing-kicker">SECURE CONSOLE</p><h2>Sẵn sàng khám phá<br />Q-SHIELD?</h2><p>Bắt đầu phân tích rủi ro trong một không gian dữ liệu minh bạch và có thể kiểm chứng.</p></div>
          <div className="landing-cta-actions"><Link className="landing-primary" href={signedIn ? "/overview" : "/register"}>{signedIn ? "Mở Console" : "Tạo tài khoản"}<ArrowRight size={18} /></Link>{!signedIn && <Link className="landing-secondary" href="/login">Đăng nhập</Link>}</div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="landing-container landing-footer-main">
          <Link className="landing-brand" href="/"><Image src={assetPath("/novaris-mark.png")} alt="" width={48} height={48} /><div><strong>NOVARIS</strong><span>Q-SHIELD</span></div></Link>
          <p>Quantum Risk Intelligence · Evidence before decisions.</p>
          <nav aria-label="Điều hướng chân trang"><a href="#capabilities">Năng lực</a><a href="#workflow">Quy trình</a><a href="#transparency">Minh bạch</a><Link href="/login">Đăng nhập</Link></nav>
        </div>
        <div className="landing-container landing-footer-bottom"><span>© {new Date().getFullYear()} NOVARIS Q-SHIELD</span><span>Built for transparent risk intelligence</span></div>
      </footer>
    </main>
  );
}
