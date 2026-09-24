"use client";

import { BarChart3, Zap, Globe2, ShieldCheck, Cpu } from "lucide-react";

const LATENCY_METRICS = [
  {
    stage: "Speech-to-Text (STT) TTFT",
    value: "285 ms",
    target: "< 350 ms",
    status: "Optimal",
    color: "text-emerald-400",
  },
  {
    stage: "Neural Machine Translation (NMT)",
    value: "142 ms",
    target: "< 200 ms",
    status: "Optimal",
    color: "text-emerald-400",
  },
  {
    stage: "Text-to-Speech (TTS) Synthesis",
    value: "310 ms",
    target: "< 400 ms",
    status: "Optimal",
    color: "text-emerald-400",
  },
  {
    stage: "Total End-to-End Translation Pipeline",
    value: "737 ms",
    target: "< 1200 ms",
    status: "Tier 1 Compliant",
    color: "text-blue-400 font-bold",
  },
];

const LANGUAGE_SHARE = [
  { code: "ENG", name: "English", share: 44, count: "1,091 min", tier: "Tier 1" },
  { code: "SPA", name: "Spanish", share: 22, count: "545 min", tier: "Tier 1" },
  { code: "JPN", name: "Japanese", share: 14, count: "347 min", tier: "Tier 1" },
  { code: "FRA", name: "French", share: 10, count: "248 min", tier: "Tier 1" },
  { code: "DEU", name: "German", share: 6, count: "148 min", tier: "Tier 1" },
  { code: "ZHO", name: "Mandarin Chinese", share: 4, count: "99 min", tier: "Tier 2" },
];

export default function AnalyticsPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-brand-primary" />
          <h1 className="text-xl font-bold text-zinc-100">Live AI Telemetry & Usage Analytics</h1>
        </div>
        <p className="text-xs text-zinc-400 mt-1">
          Monitor end-to-end translation latency, AI worker load, and global language distribution.
        </p>
      </div>

      {/* Latency Pipeline Card */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-zinc-100">
              Pipeline Stage Latency Telemetry (Prometheus Histograms)
            </h2>
          </div>
          <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
            Realtime SLA: 99.8% Healthy
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {LATENCY_METRICS.map((metric) => (
            <div
              key={metric.stage}
              className="rounded-xl border border-surface-200 bg-surface-900/80 p-4 space-y-2"
            >
              <div className="text-[11px] text-zinc-400">{metric.stage}</div>
              <div className="flex items-baseline justify-between">
                <span className={`text-xl font-bold font-mono ${metric.color}`}>
                  {metric.value}
                </span>
                <span className="text-[10px] font-mono text-zinc-500">Target: {metric.target}</span>
              </div>
              <div className="text-[10px] text-emerald-400 font-semibold">{metric.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Language Breakdown & Acoustic Watermark */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Language Share Breakdown */}
        <div className="lg:col-span-2 rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe2 className="w-4 h-4 text-brand-primary" />
              <h2 className="text-sm font-semibold text-zinc-100">Language Channel Distribution</h2>
            </div>
            <span className="text-xs text-zinc-500 font-mono">Total: 2,480 min translated</span>
          </div>

          <div className="space-y-3 pt-2">
            {LANGUAGE_SHARE.map((item) => (
              <div key={item.code} className="space-y-1.5 text-xs">
                <div className="flex items-center justify-between text-zinc-300">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-zinc-100">{item.code}</span>
                    <span className="text-zinc-400">({item.name})</span>
                    <span className="text-[10px] bg-surface-100 px-1.5 py-0.2 rounded text-zinc-400 font-mono border border-surface-200">
                      {item.tier}
                    </span>
                  </div>
                  <div className="font-mono text-zinc-400">
                    {item.count} ({item.share}%)
                  </div>
                </div>

                <div className="h-2 w-full rounded-full bg-surface-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-brand-primary to-blue-400 transition-all duration-500"
                    style={{ width: `${item.share}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Invariant #3 Verification Card */}
        <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
              <h2 className="text-sm font-semibold text-zinc-100">
                Acoustic Watermark Invariant (PR-08)
              </h2>
            </div>
            <p className="text-xs text-zinc-400 mt-2 leading-relaxed">
              Every synthetic voice stream emitted by the TTS worker fleet embeds an inaudible 20
              kHz acoustic watermark to guarantee traceability and content authenticity.
            </p>

            <div className="mt-4 p-3 rounded-xl bg-surface-900 border border-surface-200 space-y-2 text-xs">
              <div className="flex justify-between font-mono">
                <span className="text-zinc-400">Watermark Carrier:</span>
                <span className="text-emerald-400 font-bold">20,000 Hz</span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-400">Verification Rate:</span>
                <span className="text-emerald-400 font-bold">100.0%</span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-zinc-400">Tamper Status:</span>
                <span className="text-zinc-200">Untampered</span>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-brand-primary/10 border border-brand-primary/20 text-xs text-blue-300 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-brand-primary shrink-0" />
            <span>AI Fleet GPU Cluster: 6 active worker pods healthy.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
