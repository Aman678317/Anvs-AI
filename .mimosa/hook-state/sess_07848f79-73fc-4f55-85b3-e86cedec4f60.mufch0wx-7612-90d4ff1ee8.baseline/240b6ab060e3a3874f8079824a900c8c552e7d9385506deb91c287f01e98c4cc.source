"use client";

import Link from "next/link";
import {
  Video,
  Clock,
  Users,
  Languages,
  ArrowUpRight,
  ShieldCheck,
  Plus,
  FileText,
  Activity,
} from "lucide-react";
import { MeetingStatus } from "@multilingual/contracts";

const STATS = [
  {
    title: "Active Meetings",
    value: "3",
    subtext: "Live WebRTC rooms right now",
    icon: Video,
    color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    live: true,
  },
  {
    title: "Transcribed Volume",
    value: "2,480 min",
    subtext: "41.3 hours translated this month",
    icon: Clock,
    color: "text-blue-400 bg-blue-500/10 border-brand-primary/20",
  },
  {
    title: "Team Members",
    value: "24",
    subtext: "2 Hosts, 4 Moderators, 18 Members",
    icon: Users,
    color: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  },
  {
    title: "Language Coverage",
    value: "18",
    subtext: "Tier 1 & Tier 2 speech pairs",
    icon: Languages,
    color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  },
];

const RECENT_MEETINGS = [
  {
    id: "meet_001",
    title: "Global Architecture Summit: H2 Roadmap",
    status: MeetingStatus.ACTIVE,
    participantsCount: 8,
    languages: "ENG → SPA, JPN, DEU",
    duration: "42m 15s",
    created: "Today, 10:00 AM",
  },
  {
    id: "meet_002",
    title: "Executive Product Review & AI Model Evaluation",
    status: MeetingStatus.ACTIVE,
    participantsCount: 5,
    languages: "ENG → FRA, ZHO",
    duration: "18m 30s",
    created: "Today, 11:30 AM",
  },
  {
    id: "meet_003",
    title: "Sprint Retrospective & Sprint 14 Planning",
    status: MeetingStatus.ENDED,
    participantsCount: 12,
    languages: "ENG → SPA",
    duration: "55m 00s",
    created: "Yesterday, 3:00 PM",
  },
  {
    id: "meet_004",
    title: "Cross-Functional Security & Compliance Audit",
    status: MeetingStatus.ENDED,
    participantsCount: 6,
    languages: "ENG → JPN, FRA",
    duration: "1h 10m",
    created: "Sep 19, 2:00 PM",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-8 max-w-7xl mx-auto select-none">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">Organization Overview</h1>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time management for meetings, team privileges, compliance audit, and AI translation
            telemetry.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/members"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-100 hover:bg-surface-200 border border-surface-200 text-xs font-semibold text-zinc-200 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Invite Member</span>
          </Link>
          <a
            href="http://localhost:3000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-brand-primary hover:bg-blue-600 text-xs font-semibold text-white transition-colors shadow-sm shadow-blue-500/20"
          >
            <Video className="w-3.5 h-3.5" />
            <span>Join Meeting</span>
          </a>
        </div>
      </div>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {STATS.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.title}
              className="p-5 rounded-2xl border border-surface-200 bg-surface-800/50 backdrop-blur-sm space-y-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-400">{stat.title}</span>
                <div className={`p-2 rounded-xl border ${stat.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-2xl font-bold text-zinc-100 tracking-tight">
                    {stat.value}
                  </span>
                  {stat.live && (
                    <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                      LIVE
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-zinc-500 mt-1">{stat.subtext}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Invariant #1 & #2 Security Summary Banner */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-brand-primary/10 border border-brand-primary/20 text-brand-primary">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">
              Enterprise Compliance & Data Sovereignty
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              PostgreSQL Row-Level Security (RLS) active. All transcripts enforce immutable{" "}
              <code className="text-brand-primary font-mono text-[11px]">source_segment_id</code>{" "}
              lineage tags.
            </p>
          </div>
        </div>
        <Link
          href="/meetings"
          className="flex items-center gap-1 text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
        >
          <span>Review Transcripts</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Recent Meeting Activity Table */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 overflow-hidden">
        <div className="p-5 border-b border-surface-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-primary" />
            <h2 className="text-sm font-semibold text-zinc-100">Live & Recent Meetings</h2>
          </div>
          <Link
            href="/meetings"
            className="text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            View All History →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-surface-800/80 border-b border-surface-200 text-zinc-400 uppercase tracking-wider font-semibold text-[10px]">
              <tr>
                <th className="px-5 py-3">Meeting Title</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Attendees</th>
                <th className="px-5 py-3">Language Channels</th>
                <th className="px-5 py-3">Duration</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-200/50 text-zinc-300">
              {RECENT_MEETINGS.map((m) => (
                <tr key={m.id} className="hover:bg-surface-800/60 transition-colors">
                  <td className="px-5 py-3.5">
                    <div className="font-semibold text-zinc-100">{m.title}</div>
                    <div className="text-[10px] text-zinc-500">{m.created}</div>
                  </td>
                  <td className="px-5 py-3.5">
                    {m.status === MeetingStatus.ACTIVE ? (
                      <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-surface-100 text-zinc-400 border border-surface-200">
                        Completed
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3.5 text-zinc-300 font-mono">
                    {m.participantsCount} participants
                  </td>
                  <td className="px-5 py-3.5">
                    <span className="px-2 py-0.5 rounded bg-surface-100 text-blue-300 font-mono text-[10px] border border-surface-200">
                      {m.languages}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-zinc-400">{m.duration}</td>
                  <td className="px-5 py-3.5 text-right">
                    <Link
                      href={`/meetings?id=${m.id}`}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-surface-100 hover:bg-surface-200 text-zinc-300 text-[11px] transition-colors"
                    >
                      <FileText className="w-3 h-3" />
                      <span>Transcripts</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
