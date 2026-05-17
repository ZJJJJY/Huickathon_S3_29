"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Dices, Loader2 } from "lucide-react";
import type { Report } from "@/lib/types";
import { categoryLabels } from "@/lib/theme";
import SectionRenderer from "@/components/report/SectionRenderer";

type FetchState =
  | { status: "loading" }
  | { status: "ok"; report: Report }
  | { status: "missing"; hobbyId: string }
  | { status: "error"; message: string };

export default function ReportPage() {
  const params = useParams<{ hobby: string }>();
  const router = useRouter();
  const hobbyId = params.hobby;
  const [state, setState] = useState<FetchState>({ status: "loading" });
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    fetch(`/api/report?hobby=${encodeURIComponent(hobbyId)}`)
      .then(async (r) => {
        if (r.status === 404) {
          if (!cancelled) setState({ status: "missing", hobbyId });
          return;
        }
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const report = (await r.json()) as Report;
        if (!cancelled) setState({ status: "ok", report });
      })
      .catch((err) => {
        if (!cancelled)
          setState({
            status: "error",
            message: err instanceof Error ? err.message : "unknown",
          });
      });
    return () => {
      cancelled = true;
    };
  }, [hobbyId]);

  async function rollRandom() {
    if (rolling) return;
    setRolling(true);
    try {
      const res = await fetch("/api/random", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const { hobby_id } = (await res.json()) as { hobby_id: string };
      router.push(`/report/${hobby_id}`);
    } catch {
      setRolling(false);
    }
  }

  return (
    <div className="min-h-screen px-5 pt-6 pb-32">
      <div className="flex items-center justify-between mb-4">
        <Link
          href="/pick"
          className="inline-flex items-center gap-1 text-textMuted text-sm hover:text-text"
        >
          <ArrowLeft size={16} /> 返回挑选
        </Link>
      </div>

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}
      {state.status === "missing" && <MissingState hobbyId={state.hobbyId} />}
      {state.status === "ok" && <ReportView report={state.report} />}

      <div className="fixed bottom-6 left-0 right-0 flex justify-center px-5 pointer-events-none">
        <motion.button
          type="button"
          onClick={rollRandom}
          disabled={rolling}
          whileTap={{ scale: 0.96 }}
          className="pointer-events-auto inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neon-pink text-bg font-semibold disabled:opacity-60"
          style={{ boxShadow: "0 0 20px rgba(255,62,165,0.55)" }}
        >
          {rolling ? (
            <Loader2 className="animate-spin" size={18} />
          ) : (
            <Dices size={18} />
          )}
          {rolling ? "正在抽签" : "再来一个"}
        </motion.button>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center justify-center text-textMuted py-24 gap-2">
      <Loader2 className="animate-spin" size={16} />
      <span className="text-sm">正在拉取报告…</span>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-neon-pink/40 bg-neon-pink/10 text-neon-pink text-sm p-4">
      报告加载失败：{message}
    </div>
  );
}

function MissingState({ hobbyId }: { hobbyId: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-textMuted/20 bg-bgCard p-6 text-center"
    >
      <div className="text-5xl mb-3">📭</div>
      <h2 className="text-lg font-semibold mb-2">这个爱好还没有报告</h2>
      <p className="text-textMuted text-sm leading-relaxed">
        <code className="text-neon-cyan">{hobbyId}</code> 的预跑报告还未生成。
        <br />
        T7 阶段离线脚本上线后会自动补齐。
      </p>
    </motion.div>
  );
}

function ReportView({ report }: { report: Report }) {
  const categoryLabel = categoryLabels[report.category];
  return (
    <div>
      {/* Hero header with neon band */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="rounded-2xl p-5 mb-5 border"
        style={{
          borderColor: `${report.neon_color}66`,
          background: `linear-gradient(135deg, ${report.neon_color}22, transparent 60%)`,
          boxShadow: `0 0 24px ${report.neon_color}33`,
        }}
      >
        <div
          className="text-xs uppercase tracking-widest mb-2"
          style={{ color: report.neon_color }}
        >
          {categoryLabel}
        </div>
        <h1 className="text-3xl font-bold">{report.hobby_name}</h1>
      </motion.div>

      {/* Sections */}
      <div>
        {report.sections.length === 0 ? (
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4 }}
            className="rounded-2xl bg-bgCard border border-textMuted/15 p-4"
          >
            <p className="text-textMuted text-sm">
              报告还没有 sections，可能离线脚本尚未跑完。
            </p>
          </motion.section>
        ) : (
          report.sections.map((section, i) => (
            <SectionRenderer
              key={section.id}
              section={section}
              evidence={report.evidence}
              neonColor={report.neon_color}
              index={i}
            />
          ))
        )}
      </div>
    </div>
  );
}
