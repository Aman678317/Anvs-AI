"use client";

import { useState } from "react";
import { useMeetingStore } from "../stores/useMeetingStore";
import { Languages, ChevronUp, ChevronDown, Sparkles } from "lucide-react";

export function CaptionOverlay() {
  const { captions, bilingualCaptions, setBilingualCaptions } = useMeetingStore();
  const [isExpanded, setIsExpanded] = useState(false);

  // Get the most recent 3 caption segments
  const activeCaptions = captions.slice(Math.max(0, captions.length - (isExpanded ? 5 : 2)));

  if (activeCaptions.length === 0) {
    return null;
  }

  return (
    <div className="absolute bottom-20 left-4 right-4 md:left-1/2 md:-translate-x-1/2 md:max-w-2xl z-30 pointer-events-auto">
      <div className="caption-glass rounded-xl p-3 md:p-4 shadow-2xl border border-white/10 transition-all duration-200">
        {/* Header toolbar */}
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10 text-xs text-zinc-400">
          <div className="flex items-center space-x-1.5 font-medium text-emerald-400">
            <Sparkles className="w-3.5 h-3.5 animate-pulse-subtle" />
            <span>AI Live Captions</span>
          </div>

          <div className="flex items-center space-x-2">
            {/* Bilingual Mode Toggle */}
            <button
              onClick={() => setBilingualCaptions(!bilingualCaptions)}
              className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[11px] transition-colors ${
                bilingualCaptions
                  ? "bg-brand-primary/30 text-blue-300 border border-brand-primary/40"
                  : "bg-surface-100 text-zinc-400 hover:text-zinc-200"
              }`}
              title="Toggle Bilingual Side-by-Side Captions"
            >
              <Languages className="w-3 h-3" />
              <span>{bilingualCaptions ? "Bilingual" : "Single"}</span>
            </button>

            {/* Expand / Collapse history */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 rounded hover:bg-white/10 text-zinc-400 hover:text-zinc-200"
              title={isExpanded ? "Collapse" : "Expand"}
            >
              {isExpanded ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronUp className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>

        {/* Captions Feed */}
        <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1">
          {activeCaptions.map((cap) => (
            <div
              key={cap.source_segment_id}
              className={`flex flex-col space-y-0.5 text-sm transition-opacity duration-150 ${
                cap.is_final ? "opacity-100" : "opacity-85 italic"
              }`}
            >
              {/* Speaker & Citation Lineage Tag (Invariant #2) */}
              <div className="flex items-center space-x-1.5 text-xs font-semibold text-zinc-300">
                <span className="text-brand-primary font-medium">{cap.speaker_name}</span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  [{cap.source_language.toUpperCase()} → {cap.target_language.toUpperCase()}]
                </span>
                {!cap.is_final && (
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                )}
              </div>

              {/* Bilingual Display: Original speech on top */}
              {bilingualCaptions && cap.original_text && (
                <p className="text-zinc-400 text-xs font-normal">
                  {cap.original_text}
                </p>
              )}

              {/* Translated Speech */}
              <p className="text-zinc-100 font-medium tracking-wide">
                {cap.translated_text}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
