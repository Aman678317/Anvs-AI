import { ParticipantRole } from "@multilingual/contracts";
import { Shield, ShieldAlert, User, UserCheck } from "lucide-react";

interface RoleBadgeProps {
  role: ParticipantRole | string;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  switch (role) {
    case ParticipantRole.HOST:
    case "HOST":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
          <ShieldAlert className="w-3 h-3" />
          <span>Host / Admin</span>
        </span>
      );
    case ParticipantRole.MODERATOR:
    case "MODERATOR":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-300 border border-blue-500/30">
          <Shield className="w-3 h-3" />
          <span>Moderator</span>
        </span>
      );
    case ParticipantRole.PARTICIPANT:
    case "PARTICIPANT":
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-100 text-zinc-300 border border-surface-200">
          <UserCheck className="w-3 h-3 text-zinc-400" />
          <span>Participant</span>
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-surface-100 text-zinc-400 border border-surface-200">
          <User className="w-3 h-3 text-zinc-500" />
          <span>{role}</span>
        </span>
      );
  }
}
