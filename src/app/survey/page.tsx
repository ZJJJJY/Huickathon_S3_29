"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Search, X } from "lucide-react";

type Budget = "low" | "medium" | "high";
type TimeBudget = "fragment" | "weekly" | "deep";
type Onboarding = "1week" | "1month" | "3month" | "flexible";

interface SurveyState {
  city: string;
  budget: Budget | "";
  time: TimeBudget | "";
  onboarding: Onboarding | "";
}

const CITIES: { name: string; pinyin: string; tier: string }[] = [
  { name: "北京", pinyin: "beijing", tier: "T1" },
  { name: "上海", pinyin: "shanghai", tier: "T1" },
  { name: "广州", pinyin: "guangzhou", tier: "T1" },
  { name: "深圳", pinyin: "shenzhen", tier: "T1" },
  { name: "成都", pinyin: "chengdu", tier: "T1.5" },
  { name: "杭州", pinyin: "hangzhou", tier: "T1.5" },
  { name: "武汉", pinyin: "wuhan", tier: "T1.5" },
  { name: "重庆", pinyin: "chongqing", tier: "T1.5" },
  { name: "西安", pinyin: "xian", tier: "T1.5" },
  { name: "南京", pinyin: "nanjing", tier: "T1.5" },
  { name: "苏州", pinyin: "suzhou", tier: "T2" },
  { name: "长沙", pinyin: "changsha", tier: "T2" },
  { name: "郑州", pinyin: "zhengzhou", tier: "T2" },
  { name: "青岛", pinyin: "qingdao", tier: "T2" },
  { name: "天津", pinyin: "tianjin", tier: "T1.5" },
  { name: "合肥", pinyin: "hefei", tier: "T2" },
  { name: "福州", pinyin: "fuzhou", tier: "T2" },
  { name: "厦门", pinyin: "xiamen", tier: "T2" },
  { name: "宁波", pinyin: "ningbo", tier: "T2" },
  { name: "昆明", pinyin: "kunming", tier: "T2" },
];

const BUDGET_OPTIONS: { value: Budget; emoji: string; title: string; desc: string }[] = [
  { value: "low", emoji: "💰", title: "尝鲜就好，能省则省", desc: "500 元以内，先试试再说" },
  { value: "medium", emoji: "💳", title: "正常投入，认真开始", desc: "500 – 3000 元，买基础装备" },
  { value: "high", emoji: "🏆", title: "玩就玩好的", desc: "3000 元以上，一步到位" },
];

const TIME_OPTIONS: { value: TimeBudget; emoji: string; title: string; desc: string }[] = [
  { value: "fragment", emoji: "⚡", title: "碎片时间，随缘", desc: "每周 1-2 小时，见缝插针" },
  { value: "weekly", emoji: "📅", title: "周末出动", desc: "每周 3-6 小时，周末集中" },
  { value: "deep", emoji: "🎯", title: "认真投入", desc: "每周 6 小时以上，当作新习惯" },
];

const ONBOARDING_OPTIONS: { value: Onboarding; emoji: string; title: string; desc: string }[] = [
  { value: "1week", emoji: "🚀", title: "一周内就想上手", desc: "冲动要趁热，越快越好" },
  { value: "1month", emoji: "📈", title: "一个月内入门", desc: "稳步推进，不着急" },
  { value: "3month", emoji: "🌱", title: "三个月慢慢来", desc: "先了解，再决定要不要投入" },
  { value: "flexible", emoji: "🎈", title: "随缘，佛系", desc: "没有时间表，感觉对了就行" },
];

const TOTAL_STEPS = 4;

export default function SurveyPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [state, setState] = useState<SurveyState>({
    city: "",
    budget: "",
    time: "",
    onboarding: "",
  });
  const [cityQuery, setCityQuery] = useState("");

  const filteredCities = useMemo(() => {
    const q = cityQuery.trim().toLowerCase();
    if (!q) return CITIES.slice(0, 6);
    return CITIES.filter(
      (c) => c.name.includes(q) || c.pinyin.startsWith(q)
    ).slice(0, 8);
  }, [cityQuery]);

  function canProceed(): boolean {
    if (step === 0) return state.city !== "";
    if (step === 1) return state.budget !== "";
    if (step === 2) return state.time !== "";
    if (step === 3) return state.onboarding !== "";
    return false;
  }

  function next() {
    if (!canProceed()) return;
    if (step < TOTAL_STEPS - 1) {
      setStep(step + 1);
      return;
    }
    // Last step: persist and go to /pick
    try {
      sessionStorage.setItem("spark.profile", JSON.stringify(state));
    } catch {
      // sessionStorage may be unavailable; ignore
    }
    router.push("/pick");
  }

  function back() {
    if (step === 0) {
      router.push("/");
      return;
    }
    setStep(step - 1);
  }

  return (
    <div className="min-h-screen px-5 pt-6 pb-32 flex flex-col">
      {/* Header: back + progress dots */}
      <div className="flex items-center gap-3 mb-6">
        <button
          type="button"
          onClick={back}
          className="inline-flex items-center gap-1 text-textMuted text-sm hover:text-text"
        >
          <ArrowLeft size={16} />
          返回
        </button>
        <div className="flex-1 flex items-center justify-center gap-2">
          {Array.from({ length: TOTAL_STEPS }).map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i <= step
                  ? "bg-neon-pink w-6"
                  : "bg-textMuted/30 w-3"
              }`}
              style={
                i <= step
                  ? { boxShadow: "0 0 8px rgba(255,62,165,0.6)" }
                  : undefined
              }
            />
          ))}
        </div>
        <span className="text-textMuted text-xs w-12 text-right">
          Q{step + 1} / {TOTAL_STEPS}
        </span>
      </div>

      {/* Step content */}
      <div className="flex-1">
        <AnimatePresence mode="wait">
          {step === 0 && (
            <StepWrap key="q1">
              <StepHeader
                title="你在哪个城市？"
                subtitle="城市会影响场馆资源和本地成本估算"
              />
              <CitySearch
                query={cityQuery}
                setQuery={setCityQuery}
                selected={state.city}
                cities={filteredCities}
                onSelect={(name) => {
                  setState((s) => ({ ...s, city: name }));
                  setCityQuery("");
                }}
                onClear={() => setState((s) => ({ ...s, city: "" }))}
              />
            </StepWrap>
          )}

          {step === 1 && (
            <StepWrap key="q2">
              <StepHeader
                title="你愿意为这个爱好花多少钱？"
                subtitle="指初期入门阶段的总预算"
              />
              <OptionList
                options={BUDGET_OPTIONS}
                selected={state.budget}
                onPick={(v) => setState((s) => ({ ...s, budget: v }))}
              />
            </StepWrap>
          )}

          {step === 2 && (
            <StepWrap key="q3">
              <StepHeader
                title="每周大概能投入多少时间？"
                subtitle="帮助判断入门节奏和进步速度"
              />
              <OptionList
                options={TIME_OPTIONS}
                selected={state.time}
                onPick={(v) => setState((s) => ({ ...s, time: v }))}
              />
            </StepWrap>
          )}

          {step === 3 && (
            <StepWrap key="q4">
              <StepHeader
                title="你希望多久入门上手？"
                subtitle="帮助匹配适合你节奏的入门路径"
              />
              <OptionList
                options={ONBOARDING_OPTIONS}
                selected={state.onboarding}
                onPick={(v) => setState((s) => ({ ...s, onboarding: v }))}
              />
            </StepWrap>
          )}
        </AnimatePresence>
      </div>

      {/* Bottom action button */}
      <div className="fixed bottom-6 left-0 right-0 flex justify-center px-5 pointer-events-none">
        <motion.button
          type="button"
          onClick={next}
          disabled={!canProceed()}
          whileTap={{ scale: 0.96 }}
          className="pointer-events-auto inline-flex items-center gap-2 px-6 py-3 rounded-full bg-neon-pink text-bg font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ boxShadow: "0 0 20px rgba(255,62,165,0.55)" }}
        >
          {step < TOTAL_STEPS - 1 ? "下一步" : "去挑爱好"}
          <ArrowRight size={18} />
        </motion.button>
      </div>

      {/* Skip link for development convenience */}
      <div className="fixed top-4 right-4 z-10">
        <Link
          href="/pick"
          className="text-[11px] text-textMuted/60 hover:text-textMuted underline-offset-2 hover:underline"
        >
          跳过
        </Link>
      </div>
    </div>
  );
}

function StepWrap({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

function StepHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="mb-6">
      <h2 className="text-2xl font-bold leading-snug mb-2">{title}</h2>
      <p className="text-textMuted text-sm">{subtitle}</p>
    </div>
  );
}

function CitySearch({
  query,
  setQuery,
  selected,
  cities,
  onSelect,
  onClear,
}: {
  query: string;
  setQuery: (v: string) => void;
  selected: string;
  cities: { name: string; pinyin: string; tier: string }[];
  onSelect: (name: string) => void;
  onClear: () => void;
}) {
  return (
    <div>
      {selected ? (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 rounded-2xl border border-neon-pink/40 bg-neon-pink/10 px-4 py-3 mb-3"
          style={{ boxShadow: "0 0 16px rgba(255,62,165,0.25)" }}
        >
          <span>📍</span>
          <span className="font-medium">{selected}</span>
          <button
            type="button"
            onClick={onClear}
            className="ml-auto text-textMuted hover:text-text"
            aria-label="清除城市"
          >
            <X size={16} />
          </button>
        </motion.div>
      ) : (
        <>
          <div className="relative mb-3">
            <Search
              size={16}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-textMuted"
            />
            <input
              type="text"
              autoComplete="off"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="搜索城市（支持拼音）"
              className="w-full rounded-2xl bg-bgCard border border-textMuted/20 pl-9 pr-3 py-3 text-sm placeholder:text-textMuted focus:outline-none focus:border-neon-cyan/60"
            />
          </div>
          <div className="rounded-2xl bg-bgCard border border-textMuted/15 divide-y divide-textMuted/10 overflow-hidden">
            {cities.length === 0 && (
              <div className="px-4 py-3 text-sm text-textMuted">
                没有找到匹配城市
              </div>
            )}
            {cities.map((c) => (
              <button
                key={c.name}
                type="button"
                onClick={() => onSelect(c.name)}
                className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-white/5 transition-colors"
              >
                <span className="text-sm">{c.name}</span>
                <span className="text-[10px] text-textMuted px-1.5 py-0.5 rounded border border-textMuted/30">
                  {c.tier}
                </span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function OptionList<T extends string>({
  options,
  selected,
  onPick,
}: {
  options: { value: T; emoji: string; title: string; desc: string }[];
  selected: T | "";
  onPick: (v: T) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {options.map((opt) => {
        const isOn = selected === opt.value;
        return (
          <motion.button
            key={opt.value}
            type="button"
            onClick={() => onPick(opt.value)}
            whileTap={{ scale: 0.98 }}
            className={`flex items-start gap-3 rounded-2xl px-4 py-4 text-left border transition-colors ${
              isOn
                ? "border-neon-pink bg-neon-pink/10"
                : "border-textMuted/15 bg-bgCard hover:border-textMuted/30"
            }`}
            style={
              isOn
                ? { boxShadow: "0 0 18px rgba(255,62,165,0.35)" }
                : undefined
            }
          >
            <span className="text-2xl leading-none">{opt.emoji}</span>
            <div className="flex-1">
              <div className="font-medium">{opt.title}</div>
              <div className="text-textMuted text-xs mt-1">{opt.desc}</div>
            </div>
          </motion.button>
        );
      })}
    </div>
  );
}
