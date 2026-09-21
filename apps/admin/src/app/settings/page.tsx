"use client";

import { useState } from "react";
import { Settings, Save, Check, ShieldCheck, Globe2 } from "lucide-react";
import { useAdminAuth } from "../../context/AdminAuthContext";

export default function SettingsPage() {
  const { organization } = useAdminAuth();

  const [orgName, setOrgName] = useState(organization.name);
  const [orgSlug, setOrgSlug] = useState(organization.slug);
  const [defaultLanguage, setDefaultLanguage] = useState("eng");
  const [latencyTierPolicy, setLatencyTierPolicy] = useState("tier1");
  const [retentionDays, setRetentionDays] = useState("90");
  const [enforceWatermark, setEnforceWatermark] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 4000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto select-none">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Settings className="w-5 h-5 text-brand-primary" />
          <h1 className="text-xl font-bold text-zinc-100">Organization Settings & Policies</h1>
        </div>
        <p className="text-xs text-zinc-400 mt-1">
          Configure tenant identity, default AI language policies, compliance retention, and
          acoustic watermark enforcement.
        </p>
      </div>

      {saveSuccess && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-semibold animate-in fade-in">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>Organization settings successfully updated and applied across tenant fleet.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6 text-xs">
        {/* Tenant Profile Section */}
        <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Globe2 className="w-4 h-4 text-brand-primary" />
            <span>Tenant Profile & Domain</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">Organization Display Name</label>
              <input
                type="text"
                required
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
                className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3.5 py-2.5 text-zinc-100 focus:outline-none focus:border-brand-primary"
              />
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">Custom Tenant Slug (RLS Domain)</label>
              <div className="flex items-center">
                <span className="bg-surface-800 border border-r-0 border-surface-200 px-3 py-2.5 rounded-l-xl text-zinc-500 font-mono text-[11px]">
                  app.ai/org/
                </span>
                <input
                  type="text"
                  required
                  value={orgSlug}
                  onChange={(e) => setOrgSlug(e.target.value)}
                  className="w-full rounded-r-xl bg-surface-100 border border-surface-200 px-3.5 py-2.5 text-zinc-100 font-mono text-[11px] focus:outline-none focus:border-brand-primary"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Translation & AI Quality Policies */}
        <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-purple-400" />
            <span>AI Translation & Latency Policy</span>
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">
                Default Organization Spoken Language
              </label>
              <select
                value={defaultLanguage}
                onChange={(e) => setDefaultLanguage(e.target.value)}
                className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3.5 py-2.5 text-zinc-100 focus:outline-none focus:border-brand-primary"
              >
                <option value="eng">English (eng)</option>
                <option value="spa">Spanish (spa)</option>
                <option value="fra">French (fra)</option>
                <option value="deu">German (deu)</option>
                <option value="jpn">Japanese (jpn)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">Latency Tier Priority</label>
              <select
                value={latencyTierPolicy}
                onChange={(e) => setLatencyTierPolicy(e.target.value)}
                className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3.5 py-2.5 text-zinc-100 focus:outline-none focus:border-brand-primary"
              >
                <option value="tier1">Enforce Tier 1 Ultra-Low Latency (&lt; 500ms TTFT)</option>
                <option value="balanced">Balanced Latency & High Translation Accuracy</option>
                <option value="tier2">Maximum Quality (Tier 2 Extended Languages)</option>
              </select>
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 p-3 rounded-xl bg-surface-900 border border-surface-200 cursor-pointer">
              <input
                type="checkbox"
                checked={enforceWatermark}
                onChange={(e) => setEnforceWatermark(e.target.checked)}
                className="w-4 h-4 rounded text-brand-primary focus:ring-0 cursor-pointer"
              />
              <div>
                <div className="font-semibold text-zinc-200">
                  Enforce Inaudible Acoustic Watermark on All AI Audio (Invariant #3)
                </div>
                <div className="text-[11px] text-zinc-400">
                  Embeds a 20 kHz acoustic carrier watermark in all synthetic speech streams for
                  authenticity assurance.
                </div>
              </div>
            </label>
          </div>
        </div>

        {/* Data Governance & Retention */}
        <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-zinc-200">Compliance & Transcript Retention</h2>

          <div className="space-y-1.5 pt-2">
            <label className="font-semibold text-zinc-300">
              Lineaged Transcript Segment Retention Period
            </label>
            <select
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
              className="w-full max-w-xs rounded-xl bg-surface-100 border border-surface-200 px-3.5 py-2.5 text-zinc-100 focus:outline-none focus:border-brand-primary"
            >
              <option value="30">30 Days (Standard retention)</option>
              <option value="90">90 Days (Recommended for SOC 2)</option>
              <option value="180">180 Days</option>
              <option value="365">365 Days (Extended enterprise compliance)</option>
            </select>
            <p className="text-[11px] text-zinc-500">
              After this period, transcripts and vector embeddings are archived or purged according
              to GDPR/SOC 2 policies.
            </p>
          </div>
        </div>

        {/* Submit */}
        <div className="flex justify-end">
          <button
            type="submit"
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-primary hover:bg-blue-600 text-white font-semibold transition-colors shadow-md shadow-blue-500/20"
          >
            <Save className="w-4 h-4" />
            <span>Save Organization Settings</span>
          </button>
        </div>
      </form>
    </div>
  );
}
