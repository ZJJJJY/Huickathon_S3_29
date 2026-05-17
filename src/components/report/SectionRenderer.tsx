"use client";

import { motion } from "framer-motion";
import type { Evidence, ReportSection, VideoRef } from "@/lib/types";
import MarkdownBlock from "./MarkdownBlock";
import BudgetTiers from "./BudgetTiers";
import Timeline from "./Timeline";
import Checklist from "./Checklist";
import Cards from "./Cards";
import QA from "./QA";
import Citations from "./Citations";
import VideoRefCard from "./VideoRefCard";

interface Props {
  section: ReportSection;
  evidence: Record<string, Evidence>;
  videos: Record<string, VideoRef>;
  neonColor: string;
  index: number;
}

export default function SectionRenderer({
  section,
  evidence,
  videos,
  neonColor,
  index,
}: Props) {
  const { content } = section;
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.05 * index, duration: 0.35 }}
      className="rounded-2xl bg-bgCard border border-textMuted/15 p-4 mb-4"
    >
      <h2
        className="text-xs uppercase tracking-widest mb-3 font-semibold"
        style={{ color: neonColor }}
      >
        {section.title}
      </h2>

      {content.type === "markdown" && <MarkdownBlock content={content} />}
      {content.type === "budget_tiers" && (
        <BudgetTiers content={content} neonColor={neonColor} />
      )}
      {content.type === "timeline" && (
        <Timeline content={content} neonColor={neonColor} />
      )}
      {content.type === "checklist" && (
        <Checklist content={content} neonColor={neonColor} />
      )}
      {content.type === "cards" && (
        <Cards content={content} neonColor={neonColor} />
      )}
      {content.type === "qa" && <QA content={content} neonColor={neonColor} />}

      <Citations
        ids={section.citations}
        evidence={evidence}
        neonColor={neonColor}
      />

      {section.video_refs?.map((vid) =>
        videos[vid] ? (
          <VideoRefCard key={vid} video={videos[vid]} sectionTitle={section.title} neonColor={neonColor} />
        ) : null
      )}
    </motion.section>
  );
}
