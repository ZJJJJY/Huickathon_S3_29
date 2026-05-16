"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import type { HobbyMeta } from "@/lib/types";

interface HobbyCardProps {
  hobby: HobbyMeta;
  index: number;
}

export function HobbyCard({ hobby, index }: HobbyCardProps) {
  return (
    <Link href={`/report/${hobby.id}`} prefetch>
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{
          delay: 0.04 * index,
          duration: 0.35,
          ease: "easeOut",
        }}
        whileTap={{ scale: 0.95 }}
        whileHover={{
          scale: 1.03,
          boxShadow: `0 0 18px ${hobby.neon_color}`,
        }}
        className="relative rounded-2xl bg-bgCard p-4 cursor-pointer h-full flex flex-col gap-2 border"
        style={{
          borderColor: `${hobby.neon_color}55`,
        }}
      >
        <div className="text-3xl leading-none">{hobby.emoji}</div>
        <div
          className="font-semibold text-base"
          style={{ color: hobby.neon_color }}
        >
          {hobby.name}
        </div>
        <div className="text-textMuted text-xs leading-snug">
          {hobby.one_liner}
        </div>
      </motion.div>
    </Link>
  );
}
