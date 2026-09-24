"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  CalendarCheck,
  BarChart3,
  FileCheck2,
  Settings,
  Globe2,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { useAdminAuth } from "../context/AdminAuthContext";
import { ParticipantRole } from "@multilingual/contracts";

const NAV_ITEMS = [
  {
    name: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
  },
  {
    name: "Members & Roles",
    href: "/members",
    icon: Users,
  },
  {
    name: "Meetings & Compliance",
    href: "/meetings",
    icon: CalendarCheck,
  },
  {
    name: "Analytics & Telemetry",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    name: "Audit Trail",
    href: "/audit-logs",
    icon: FileCheck2,
  },
  {
    name: "Organization Settings",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, organization, setUserRole } = useAdminAuth();

  return (
    <aside className="w-64 border-r border-surface-200/60 bg-surface-900 flex flex-col justify-between shrink-0 h-screen select-none">
      {/* Top: Branding & Tenant Name */}
      <div>
        <div className="h-16 px-5 border-b border-surface-200/60 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-brand-primary to-brand-accent flex items-center justify-center text-white shadow-md shadow-blue-500/20">
            <Globe2 className="w-5 h-5" />
          </div>
          <div className="overflow-hidden">
            <div className="flex items-center gap-1.5">
              <span className="text-sm font-bold text-zinc-100 tracking-tight">Admin Console</span>
              <span className="text-[10px] bg-brand-primary/20 text-blue-300 font-mono px-1 rounded border border-brand-primary/30">
                PRO
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 truncate">{organization.name}</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                  isActive
                    ? "bg-brand-primary/15 text-blue-400 border border-brand-primary/30 shadow-sm"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-surface-100/80"
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? "text-blue-400" : "text-zinc-500"}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom: External Meeting Link & RBAC Demo Switcher */}
      <div className="p-3 border-t border-surface-200/60 space-y-2.5 bg-surface-800/30">
        <a
          href="http://localhost:3000"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between px-3 py-2 rounded-xl bg-surface-100/70 border border-surface-200 text-xs text-zinc-300 hover:text-white hover:bg-surface-100 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>Open Meeting Room</span>
          </div>
          <ExternalLink className="w-3 h-3 text-zinc-500" />
        </a>

        {/* RBAC Role Simulator for DoD Testing */}
        <div className="rounded-xl border border-surface-200/80 p-2.5 bg-surface-900/80 text-[11px] space-y-1.5">
          <span className="font-semibold text-zinc-400">Simulate Role (DoD Guard):</span>
          <div className="flex gap-1">
            <button
              onClick={() => setUserRole(ParticipantRole.HOST)}
              className={`flex-1 py-1 px-1.5 rounded text-[10px] font-semibold transition-colors ${
                user.role === ParticipantRole.HOST
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                  : "bg-surface-100 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Host (Admin)
            </button>
            <button
              onClick={() => setUserRole(ParticipantRole.PARTICIPANT)}
              className={`flex-1 py-1 px-1.5 rounded text-[10px] font-semibold transition-colors ${
                user.role === ParticipantRole.PARTICIPANT
                  ? "bg-red-500/20 text-red-300 border border-red-500/40"
                  : "bg-surface-100 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Participant
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
