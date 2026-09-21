"use client";

import "./globals.css";
import { AdminAuthProvider, useAdminAuth } from "../context/AdminAuthContext";
import { Sidebar } from "../components/Sidebar";
import { AdminHeader } from "../components/AdminHeader";
import { ShieldAlert, ArrowLeft } from "lucide-react";
import { ParticipantRole } from "@multilingual/contracts";

function AdminLayoutContent({ children }: { children: React.ReactNode }) {
  const { isAdmin, user, setUserRole } = useAdminAuth();

  // Role-Based Route Protection Guard (DoD Invariant)
  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-surface-900 p-6 text-center select-none">
        <div className="max-w-md w-full rounded-2xl border border-red-500/30 bg-surface-800/80 backdrop-blur-md p-8 shadow-2xl space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-red-500/20 text-red-400 border border-red-500/30 mx-auto flex items-center justify-center">
            <ShieldAlert className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <h1 className="text-xl font-bold text-zinc-100">403 - Forbidden</h1>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Administrative privileges are required to access this console. Your active role is{" "}
              <span className="font-semibold text-red-400 uppercase">[{user.role}]</span>.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-surface-900/90 border border-surface-200 text-left text-xs space-y-1">
            <div className="font-semibold text-zinc-300">RBAC Security Invariant:</div>
            <div className="text-zinc-500">
              Only users with <span className="text-amber-300 font-semibold">HOST (Admin)</span>{" "}
              permissions can view organization settings, team rosters, and compliance logs.
            </div>
          </div>

          <button
            onClick={() => setUserRole(ParticipantRole.HOST)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-brand-primary hover:bg-blue-600 text-white text-xs font-semibold transition-colors shadow-lg shadow-blue-500/20"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Switch back to Host (Admin)</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-surface-900 text-zinc-100">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <AdminHeader />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8 bg-surface-900">{children}</main>
      </div>
    </div>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <title>Enterprise Admin Console | Multilingual AI Platform</title>
        <meta
          name="description"
          content="Organization settings, member roles, compliance transcripts, and real-time usage telemetry."
        />
      </head>
      <body className="min-h-screen bg-surface-900 antialiased selection:bg-brand-primary selection:text-white">
        <AdminAuthProvider>
          <AdminLayoutContent>{children}</AdminLayoutContent>
        </AdminAuthProvider>
      </body>
    </html>
  );
}
