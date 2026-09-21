"use client";

import { useState } from "react";
import { Users, UserPlus, Search, Check, X, Trash2, AlertCircle } from "lucide-react";
import { ParticipantRole } from "@multilingual/contracts";
import { RoleBadge } from "../../components/RoleBadge";

interface MemberItem {
  userId: string;
  email: string;
  fullName: string;
  role: ParticipantRole;
  isActive: boolean;
  createdAt: string;
}

const INITIAL_MEMBERS: MemberItem[] = [
  {
    userId: "usr_001",
    email: "admin@acme-enterprise.org",
    fullName: "Devon Vance",
    role: ParticipantRole.HOST,
    isActive: true,
    createdAt: "2026-08-01",
  },
  {
    userId: "usr_002",
    email: "kenji.sato@acme-enterprise.org",
    fullName: "Kenji Sato",
    role: ParticipantRole.HOST,
    isActive: true,
    createdAt: "2026-08-10",
  },
  {
    userId: "usr_003",
    email: "elena.rostova@acme-enterprise.org",
    fullName: "Elena Rostova",
    role: ParticipantRole.MODERATOR,
    isActive: true,
    createdAt: "2026-08-15",
  },
  {
    userId: "usr_004",
    email: "marcus.vance@acme-enterprise.org",
    fullName: "Marcus Vance",
    role: ParticipantRole.MODERATOR,
    isActive: true,
    createdAt: "2026-08-20",
  },
  {
    userId: "usr_005",
    email: "sarah.chen@acme-enterprise.org",
    fullName: "Sarah Chen",
    role: ParticipantRole.PARTICIPANT,
    isActive: true,
    createdAt: "2026-09-01",
  },
  {
    userId: "usr_006",
    email: "lucas.silva@acme-enterprise.org",
    fullName: "Lucas Silva",
    role: ParticipantRole.PARTICIPANT,
    isActive: false,
    createdAt: "2026-09-05",
  },
];

export default function MembersPage() {
  const [members, setMembers] = useState<MemberItem[]>(INITIAL_MEMBERS);
  const [searchQuery, setSearchQuery] = useState("");
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState<ParticipantRole>(ParticipantRole.PARTICIPANT);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const filteredMembers = members.filter(
    (m) =>
      m.fullName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.role.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const handleInviteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    const newMember: MemberItem = {
      userId: `usr_${Date.now()}`,
      email: inviteEmail.trim(),
      fullName: inviteName.trim() || inviteEmail.split("@")[0],
      role: inviteRole,
      isActive: true,
      createdAt: new Date().toISOString().split("T")[0],
    };

    setMembers([newMember, ...members]);
    setIsInviteModalOpen(false);
    setInviteEmail("");
    setInviteName("");
    setInviteRole(ParticipantRole.PARTICIPANT);
    setFeedbackMsg(`Invited ${newMember.fullName} as ${newMember.role}`);
    setTimeout(() => setFeedbackMsg(null), 4000);
  };

  const handleRoleChange = (userId: string, newRole: ParticipantRole) => {
    setMembers((prev) => prev.map((m) => (m.userId === userId ? { ...m, role: newRole } : m)));
  };

  const handleToggleActive = (userId: string) => {
    setMembers((prev) =>
      prev.map((m) => (m.userId === userId ? { ...m, isActive: !m.isActive } : m)),
    );
  };

  const handleDeleteMember = (userId: string) => {
    const target = members.find((m) => m.userId === userId);
    if (!target) return;
    if (target.role === ParticipantRole.HOST) {
      const hostCount = members.filter((m) => m.role === ParticipantRole.HOST).length;
      if (hostCount <= 1) {
        alert("Cannot remove the sole active Host/Admin from the organization.");
        return;
      }
    }
    setMembers((prev) => prev.filter((m) => m.userId !== userId));
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-brand-primary" />
            <h1 className="text-xl font-bold text-zinc-100">Team Members & Role Delegation</h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Manage organization members, assign Host / Moderator permissions, and control tenant
            access.
          </p>
        </div>

        <button
          onClick={() => setIsInviteModalOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-primary hover:bg-blue-600 text-xs font-semibold text-white transition-colors shadow-sm shadow-blue-500/20 self-start sm:self-auto"
        >
          <UserPlus className="w-4 h-4" />
          <span>Invite New Member</span>
        </button>
      </div>

      {/* Success Notification */}
      {feedbackMsg && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs font-medium animate-in fade-in">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {/* Search & Filter Toolbar */}
      <div className="flex items-center justify-between gap-4 bg-surface-800/40 p-3 rounded-xl border border-surface-200">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, email, or role..."
            className="w-full bg-surface-100 border border-surface-200 rounded-lg pl-9 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
          />
        </div>
        <div className="text-xs text-zinc-400 font-mono">
          Showing {filteredMembers.length} of {members.length} members
        </div>
      </div>

      {/* Members Table */}
      <div className="rounded-2xl border border-surface-200 bg-surface-800/40 overflow-hidden">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-800/80 border-b border-surface-200 text-zinc-400 uppercase tracking-wider font-semibold text-[10px]">
            <tr>
              <th className="px-5 py-3">Member</th>
              <th className="px-5 py-3">Assigned Role</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Added Date</th>
              <th className="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-200/50 text-zinc-300">
            {filteredMembers.map((m) => (
              <tr key={m.userId} className="hover:bg-surface-800/60 transition-colors">
                {/* Member Identity */}
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-surface-100 text-zinc-200 font-bold flex items-center justify-center text-xs border border-surface-200">
                      {m.fullName.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <div className="font-semibold text-zinc-100">{m.fullName}</div>
                      <div className="text-[11px] text-zinc-400">{m.email}</div>
                    </div>
                  </div>
                </td>

                {/* Role with Dropdown */}
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <RoleBadge role={m.role} />
                    <select
                      value={m.role}
                      onChange={(e) =>
                        handleRoleChange(m.userId, e.target.value as ParticipantRole)
                      }
                      className="bg-surface-100 border border-surface-200 text-[11px] text-zinc-300 rounded px-1.5 py-0.5 focus:outline-none focus:border-brand-primary"
                    >
                      <option value={ParticipantRole.HOST}>Host</option>
                      <option value={ParticipantRole.MODERATOR}>Moderator</option>
                      <option value={ParticipantRole.PARTICIPANT}>Participant</option>
                    </select>
                  </div>
                </td>

                {/* Status Toggle */}
                <td className="px-5 py-3.5">
                  <button
                    onClick={() => handleToggleActive(m.userId)}
                    className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold transition-colors ${
                      m.isActive
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-red-500/10 text-red-400 border border-red-500/30"
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        m.isActive ? "bg-emerald-400" : "bg-red-400"
                      }`}
                    />
                    {m.isActive ? "Active" : "Suspended"}
                  </button>
                </td>

                {/* Added Date */}
                <td className="px-5 py-3.5 text-zinc-400 font-mono text-[11px]">{m.createdAt}</td>

                {/* Action Buttons */}
                <td className="px-5 py-3.5 text-right">
                  <button
                    onClick={() => handleDeleteMember(m.userId)}
                    className="p-1.5 rounded-lg hover:bg-red-500/20 text-zinc-400 hover:text-red-400 transition-colors"
                    title="Remove member"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Invite Member Modal */}
      {isInviteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md rounded-2xl border border-surface-200 bg-surface-900 shadow-2xl overflow-hidden flex flex-col">
            <div className="h-14 px-5 border-b border-surface-200 flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-100">
                <UserPlus className="w-4 h-4 text-brand-primary" />
                <span>Invite Team Member</span>
              </div>
              <button
                onClick={() => setIsInviteModalOpen(false)}
                className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleInviteSubmit} className="p-5 space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-300">Email Address *</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@acme-enterprise.org"
                  className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-300">Full Name</label>
                <input
                  type="text"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-zinc-300">Initial Role Assignment</label>
                <select
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value as ParticipantRole)}
                  className="w-full rounded-xl bg-surface-100 border border-surface-200 px-3 py-2 text-zinc-100 focus:outline-none focus:border-brand-primary"
                >
                  <option value={ParticipantRole.PARTICIPANT}>
                    Participant (Standard attendee)
                  </option>
                  <option value={ParticipantRole.MODERATOR}>
                    Moderator (Meeting control privileges)
                  </option>
                  <option value={ParticipantRole.HOST}>
                    Host / Admin (Full tenant administration)
                  </option>
                </select>
              </div>

              <div className="rounded-xl bg-surface-800 p-3 border border-surface-200 text-zinc-400 text-[11px] flex gap-2">
                <AlertCircle className="w-4 h-4 text-brand-primary shrink-0 mt-0.5" />
                <span>
                  The user will receive an automated tenant onboarding token and will be bound by
                  PostgreSQL RLS policies for this organization.
                </span>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsInviteModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-zinc-400 hover:text-zinc-200 hover:bg-surface-100 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-brand-primary hover:bg-blue-600 text-white font-semibold transition-colors shadow-sm"
                >
                  Send Invitation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
