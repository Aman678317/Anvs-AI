"use client";

import { useAdminAuth } from "../context/AdminAuthContext";
import { RoleBadge } from "./RoleBadge";
import { Bell, Activity, ShieldCheck } from "lucide-react";

export function AdminHeader() {
  const { user, organization } = useAdminAuth();

  return (
    <header className="h-16 border-b border-surface-200/60 bg-surface-900/80 backdrop-blur-md px-6 flex items-center justify-between z-10 select-none">
      {/* Left: Organization Status & Breadcrumbs */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span>Tenant: {organization.name}</span>
        </div>
        <span className="text-zinc-600">/</span>
        <div className="flex items-center gap-1.5 text-xs text-zinc-400">
          <ShieldCheck className="w-3.5 h-3.5 text-brand-primary" />
          <span>RLS Enforced: Isolated Tenant Boundary</span>
        </div>
      </div>

      {/* Right: Telemetry Notification & Admin User Info */}
      <div className="flex items-center gap-4">
        <button
          className="p-2 rounded-xl bg-surface-100 hover:bg-surface-200 border border-surface-200 text-zinc-400 hover:text-zinc-200 transition-colors relative"
          title="Compliance & Platform Alerts"
        >
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-brand-primary" />
        </button>

        <div className="h-6 w-[1px] bg-surface-200" />

        {/* User Identity & Role Badge */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-xs font-semibold text-zinc-100">{user.displayName}</div>
            <div className="text-[11px] text-zinc-400">{user.email}</div>
          </div>
          <RoleBadge role={user.role} />
        </div>
      </div>
    </header>
  );
}
