"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Flame } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden">
      {/* Ambient neon blobs */}
      <motion.div
        aria-hidden
        className="absolute -top-32 -left-20 w-72 h-72 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, rgba(255,62,165,0.45), transparent)",
          filter: "blur(40px)",
        }}
        animate={{ x: [0, 20, 0], y: [0, 30, 0] }}
        transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.div
        aria-hidden
        className="absolute -bottom-32 -right-20 w-80 h-80 rounded-full"
        style={{
          background:
            "radial-gradient(closest-side, rgba(62,232,255,0.35), transparent)",
          filter: "blur(48px)",
        }}
        animate={{ x: [0, -20, 0], y: [0, -25, 0] }}
        transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }}
      />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="relative z-10 text-center"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-neon-pink/50 text-neon-pink text-xs mb-6 backdrop-blur">
          <Flame size={14} />
          <span>Three-Minute Spark</span>
        </div>
        <h1 className="text-5xl font-bold leading-tight mb-4 tracking-tight">
          即刻<span className="text-neon-pink">心动</span>
        </h1>
        <p className="text-textMuted text-base mb-12 max-w-xs mx-auto">
          刷到一个爱好，<br />30 秒看它适不适合你
        </p>

        <Link href="/survey" prefetch>
          <motion.div
            whileTap={{ scale: 0.96 }}
            whileHover={{ scale: 1.02 }}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-full bg-neon-pink text-bg font-semibold text-lg"
            style={{ boxShadow: "0 0 24px rgba(255,62,165,0.6)" }}
          >
            开始
            <ArrowRight size={20} />
          </motion.div>
        </Link>

        <p className="text-textMuted text-xs mt-8">30 秒问卷 · 无需注册</p>
      </motion.div>
    </div>
  );
}
