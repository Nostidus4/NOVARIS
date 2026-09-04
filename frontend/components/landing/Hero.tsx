"use client";

import { motion } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { assetPath } from "@/lib/paths";

const EASE = [0.16, 1, 0.3, 1] as const;

const fadeUp = {
  hidden: { opacity: 0, y: 22 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } },
};

export function Hero({ stats }: { stats: { value: string; label: string }[] }) {
  return (
    <section className="lp-hero">
      <div className="lp-hero-bg" aria-hidden>
        <motion.div
          className="lp-hero-bg-img"
          initial={{ scale: 1.14, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 1.8, ease: EASE }}
        >
          <Image src={assetPath("/Background.jpeg")} alt="" fill priority sizes="100vw" />
        </motion.div>
      </div>

      <div className="lp-shell lp-hero-inner">
        <motion.span initial="hidden" animate="show" variants={fadeUp} className="lp-eyebrow">
          <span className="lp-eyebrow-dot" />
          Prototype dự thi · Risk Intelligence Console
        </motion.span>

        <motion.h1
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.08 }}
          className="lp-hero-title"
        >
          Dò áp lực thị trường.
        </motion.h1>

        <motion.div
          className="lp-hero-mark"
          initial={{ opacity: 0, scale: 0.7, y: 12 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.2, ease: EASE }}
        >
          <motion.span
            className="lp-hero-mark-glow"
            animate={{ opacity: [0.45, 0.85, 0.45], scale: [1, 1.08, 1] }}
            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.span
            className="lp-hero-mark-ring"
            animate={{ rotate: 360 }}
            transition={{ duration: 46, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="lp-hero-mark-float"
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          >
            <Image
              src={assetPath("/novaris-mark.png")}
              alt="NOVARIS"
              width={180}
              height={180}
              priority
              className="lp-hero-mark-img"
            />
          </motion.div>
        </motion.div>

        <motion.h1
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.3 }}
          className="lp-hero-title lp-hero-title-2"
        >
          <span className="accent">Phòng vệ danh mục — mô hình hoá bằng QUBO.</span>
        </motion.h1>

        <motion.p
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.4 }}
          className="lp-hero-text"
        >
          Q-SHIELD mô phỏng kịch bản stress trên rổ VN30, đo CVaR trên phân phối lỗ, rồi tối ưu
          hành động phòng vệ tiền mặt bằng QUBO/QAOA — mọi nghiệm đều được đối chiếu với exact
          solver trước khi trở thành bằng chứng.
        </motion.p>

        <motion.div
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.48 }}
          className="lp-hero-actions"
        >
          <Link href="/overview" className="lp-btn lp-btn-primary">
            Vào Console
            <ArrowRight size={15} />
          </Link>
          <a href="#pipeline" className="lp-btn lp-btn-ghost">
            Xem quy trình
          </a>
        </motion.div>

        <motion.p
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.54 }}
          className="lp-hero-note"
        >
          Không phải khuyến nghị đầu tư — hệ thống mô tả kịch bản rủi ro, có bằng chứng đi kèm.
        </motion.p>

        <motion.div
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ ...fadeUp.show.transition, delay: 0.6 }}
          className="lp-stats"
        >
          {stats.map((s) => (
            <div className="lp-stat" key={s.label}>
              <div className="lp-stat-value">{s.value}</div>
              <div className="lp-stat-label">{s.label}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
