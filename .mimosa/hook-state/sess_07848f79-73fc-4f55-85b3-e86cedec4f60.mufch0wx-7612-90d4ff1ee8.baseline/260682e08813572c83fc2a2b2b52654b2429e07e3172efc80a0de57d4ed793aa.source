"use client";

import { useState } from "react";
import { FileCheck2, Search, Download, ShieldCheck } from "lucide-react";

interface AuditEventItem {
  id: string;
  eventType: string;
  actorEmail: string;
  target: string;
  timestamp: string;
  details: string;
}

const AUDIT_EVENTS: AuditEventItem[] = [
  {
    id: "aud_9001",
    eventType: "TRANSCRIPT_EXPORT",
    actorEmail: "admin@acme-enterprise.org",
    target: "meet_001 (Global Architecture Summit)",
    timestamp: "2026-09-21 11:45:12 UTC",
    details: "Format: JSON, Invariant: source_segment_id, records: 142",
  },
  {
    id: "aud_9002",
    eventType: "MEMBER_INVITED",
    actorEmail: "admin@acme-enterprise.org",
    target: "new.hire@acme-enterprise.org",
    timestamp: "2026-09-21 10:15:00 UTC",
    details: "Role assigned: MODERATOR, Tenant: org_acme_enterprise",
  },
  {
    id: "aud_9003",
    eventType: "ROLE_UPDATED",
    actorEmail: "admin@acme-enterprise.org",
    target: "elena.rostova@acme-enterprise.org",
    timestamp: "2026-09-20 16:30:22 UTC",
    details: "Role updated: PARTICIPANT → MODERATOR",
  },
  {
    id: "aud_9004",
    eventType: "AUTH_CONSOLE_ACCESS",
    actorEmail: "admin@acme-enterprise.org",
    target: "AdminConsoleSession",
    timestamp: "2026-09-20 09:00:01 UTC",
    details: "IP: 192.168.1.42, Role: HOST, Method: Supabase JWT",
  },
  {
    id: "aud_9005",
    eventType: "MEETING_TERMINATED",
    actorEmail: "kenji.sato@acme-enterprise.org",
    target: "meet_003 (Sprint Retrospective)",
    timestamp: "2026-09-19 15:55:00 UTC",
    details: "Reason: Scheduled meeting end, Duration: 55m",
  },
];

export default function AuditLogsPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredLogs = AUDIT_EVENTS.filter(
    (log) =>
      log.eventType.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.actorEmail.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.target.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleExportLogs = () => {
    const dataStr =
      "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(filteredLogs, null, 2));
    const downloadAnchor = document.createElement("a");
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `audit_log_export_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-5 h-5 text-brand-primary" />
            <h1 className="text-xl font-bold text-zinc-100">Security & Compliance Audit Trail</h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Immutable log of all administrative actions, data exports, member invites, and tenant
            access.
          </p>
        </div>

        <button
          onClick={handleExportLogs}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-surface-100 hover:bg-surface-200 border border-surface-200 text-xs font-semibold text-zinc-200 transition-colors self-start sm:self-auto"
        >
          <Download className="w-4 h-4" />
          <span>Export Audit Log (JSON)</span>
        </button>
      </div>

      {/* RLS Enforcement Notice */}
      <div className="p-4 rounded-xl bg-surface-800/40 border border-surface-200 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 text-zinc-300">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>
            Audit logs are tenant-isolated and stored with write-once retention for enterprise
            regulatory compliance (SOC 2, GDPR).
          </span>
        </div>
        <span className="font-mono text-zinc-500 text-[11px]">Retention: 365 Days</span>
      </div>

      {/* Search Toolbar */}
      <div className="flex items-center justify-between gap-4 bg-surface-800/40 p-3 rounded-xl border border-surface-200">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by event type, actor email, or target..."
            className="w-full bg-surface-100 border border-surface-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
          />
        </div>
        <div className="text-xs text-zinc-400 font-mono">Showing {filteredLogs.length} events</div>
      </div>

      {/* Audit Log Table */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-800/80 border-b border-surface-200 text-zinc-400 uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-5 py-3">Event Type</th>
              <th className="px-5 py-3">Actor</th>
              <th className="px-5 py-3">Target Resource</th>
              <th className="px-5 py-3">Timestamp (UTC)</th>
              <th className="px-5 py-3">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200/50 text-zinc-300">
            {filteredLogs.map((log) => (
              <tr key={log.id} className="hover:bg-surface-800/60 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-brand-primary/15 text-blue-300 border border-brand-primary/30">
                    {log.eventType}
                  </span>
                </td>
                <td className="px-5 py-3.5 font-semibold text-zinc-200">{log.actorEmail}</td>
                <td className="px-5 py-3.5 text-zinc-300 font-mono text-[11px]">{log.target}</td>
                <td className="px-5 py-3.5 font-mono text-zinc-400 text-[11px]">{log.timestamp}</td>
                <td className="px-5 py-3.5 text-zinc-400 font-mono text-[11px] truncate max-w-xs">
                  {log.details}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
