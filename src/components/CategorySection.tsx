"use client";

import { motion } from "framer-motion";
import type { CategoryGroup } from "@/lib/types";
import { HobbyCard } from "./HobbyCard";

interface CategorySectionProps {
  group: CategoryGroup;
  /** Card index offset across all sections so stagger is monotonic. */
  baseIndex: number;
  /** Group order, used to stagger the section header entrance. */
  order: number;
}

export function CategorySection({ group, baseIndex, order }: CategorySectionProps) {
  const color = group.hobbies[0]?.neon_color ?? "#FF3EA5";
  return (
    <section className="mb-8">
      <motion.h2
        initial={{ opacity: 0, x: -8 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.08 * order, duration: 0.3 }}
        className="text-sm font-semibold mb-3 uppercase tracking-widest"
        style={{
          color,
          textShadow: `0 0 12px ${color}88`,
        }}
      >
        {group.label}
      </motion.h2>
      <div className="grid grid-cols-2 gap-3">
        {group.hobbies.map((hobby, i) => (
          <HobbyCard key={hobby.id} hobby={hobby} index={baseIndex + i} />
        ))}
      </div>
    </section>
  );
}
