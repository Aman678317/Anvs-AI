"use client";

import { X, Mic, MicOff, Video, VideoOff, Shield, User } from "lucide-react";
import { ParticipantRole } from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";

interface ParticipantsPanelProps {
  onClose: () => void;
}

export function ParticipantsPanel({ onClose }: ParticipantsPanelProps) {
  const {
    displayName,
    role,
    spokenLanguage,
    listeningLanguage,
    isMicMuted,
    isVideoEnabled,
    participants,
  } = useMeetingStore();

  const remoteList = Object.values(participants);
  const totalCount = remoteList.length + 1;

  const renderRoleBadge = (r: ParticipantRole) => {
    switch (r) {
      case ParticipantRole.HOST:
        return (
          <span className="flex items-center space-x-1 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-semibold border border-amber-500/30">
            <Shield className="w-2.5 h-2.5" />
            <span>Host</span>
          </span>
        );
      case ParticipantRole.MODERATOR:
        return (
          <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 text-[10px] font-semibold border border-blue-500/30">
            Moderator
          </span>
        );
      default:
        return (
          <span className="px-1.5 py-0.5 rounded bg-surface-100 text-zinc-400 text-[10px] font-mono">
            {r}
          </span>
        );
    }
  };

  return (
    <aside className="w-80 md:w-96 h-full border-l border-surface-200/60 bg-surface-900/95 backdrop-blur-md flex flex-col z-30">
      {/* Header */}
      <div className="h-14 px-4 border-b border-surface-200 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-100">
          Participants ({totalCount})
        </h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-surface-100 text-zinc-400 hover:text-zinc-200"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Participants List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {/* Local Self Entry */}
        <div className="flex items-center justify-between p-2.5 rounded-xl bg-surface-100/70 border border-surface-200">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-full bg-brand-primary/30 text-blue-300 flex items-center justify-center text-xs font-bold border border-brand-primary/40">
              {displayName.slice(0, 2).toUpperCase() || <User className="w-4 h-4" />}
            </div>
            <div>
              <div className="flex items-center space-x-1.5">
                <span className="text-xs font-semibold text-zinc-200">
                  {displayName} (You)
                </span>
                {renderRoleBadge(role)}
              </div>
              <span className="text-[10px] text-zinc-500 font-mono">
                {spokenLanguage.toUpperCase()} → {listeningLanguage.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-1.5 text-zinc-400">
            {isMicMuted ? (
              <MicOff className="w-3.5 h-3.5 text-red-400" />
            ) : (
              <Mic className="w-3.5 h-3.5 text-emerald-400" />
            )}
            {isVideoEnabled ? (
              <Video className="w-3.5 h-3.5 text-zinc-300" />
            ) : (
              <VideoOff className="w-3.5 h-3.5 text-red-400" />
            )}
          </div>
        </div>

        {/* Remote Attendees */}
        {remoteList.map((p) => (
          <div
            key={p.participant_id}
            className="flex items-center justify-between p-2.5 rounded-xl bg-surface-800/40 border border-surface-200/50 hover:bg-surface-800 transition-colors"
          >
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-full bg-surface-100 text-zinc-300 flex items-center justify-center text-xs font-bold border border-surface-200">
                {p.display_name.slice(0, 2).toUpperCase() || <User className="w-4 h-4" />}
              </div>
              <div>
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-semibold text-zinc-200">
                    {p.display_name}
                  </span>
                  {renderRoleBadge(p.role)}
                </div>
                <span className="text-[10px] text-zinc-500 font-mono">
                  {p.spoken_language.toUpperCase()} → {p.listening_language.toUpperCase()}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-1.5 text-zinc-400">
              {p.is_muted ? (
                <MicOff className="w-3.5 h-3.5 text-red-400" />
              ) : (
                <Mic className="w-3.5 h-3.5 text-emerald-400" />
              )}
              {p.is_video_enabled ? (
                <Video className="w-3.5 h-3.5 text-zinc-300" />
              ) : (
                <VideoOff className="w-3.5 h-3.5 text-red-400" />
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
