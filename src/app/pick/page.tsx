"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Dices, Loader2 } from "lucide-react";
import type { HobbiesJSON } from "@/lib/types";
import { CategorySection } from "@/components/CategorySection";

export default function PickPage() {
  const router = useRouter();
  const [data, setData] = useState<HobbiesJSON | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/hobbies")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<HobbiesJSON>;
      })
      .then((json) => {
        if (!cancelled) setData(json);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function rollRandom() {
    if (rolling) return;
    setRolling(true);
    try {
      const res = await fetch("/api/random", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { hobby_id } = (await res.json()) as { hobby_id: string };
      router.push(`/report/${hobby_id}`);
    } catch (err) {
      setRolling(false);
      setError(err instanceof Error ? err.message : "random failed");
    }
  }

  return (
    <div className="min-h-screen px-5 pt-8 pb-32">
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold mb-1">挑一个想试试的</h1>
        <p className="text-textMuted text-sm">选个爱好，30 秒看它适不适合你</p>
      </motion.header>

      {error && (
        <div className="rounded-xl border border-neon-pink/40 bg-neon-pink/10 text-neon-pink text-sm p-3 mb-4">
          加载失败：{error}
        </div>
      )}

      {!data && !error && (
        <div className="flex items-center justify-center text-textMuted py-20 gap-2">
          <Loader2 className="animate-spin" size={16} />
          <span className="text-sm">读取爱好清单…</span>
        </div>
      )}

      {data &&
        data.map((group, idx) => {
          const baseIndex = data
            .slice(0, idx)
            .reduce((acc, g) => acc + g.hobbies.length, 0);
          return (
            <CategorySection
              key={group.category}
              group={group}
              baseIndex={baseIndex}
              order={idx}
            />
          );
        })}

      {/* Floating random button */}
      <div className="fixed bottom-6 left-0 right-0 flex justify-center px-5 pointer-events-none">
        <motion.button
          type="button"
          onClick={rollRandom}
          disabled={rolling || !data}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          whileTap={{ scale: 0.96 }}
          className="pointer-events-auto inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neon-pink text-bg font-semibold disabled:opacity-60"
          style={{ boxShadow: "0 0 20px rgba(255,62,165,0.55)" }}
        >
          {rolling ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <Dices size={18} />
          )}
          {rolling ? "正在抽签" : "随便来一个"}
        </motion.button>
      </div>
    </div>
  );
}
