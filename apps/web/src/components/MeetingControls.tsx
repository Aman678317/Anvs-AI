"use client";

import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  ScreenShare,
  MessageSquare,
  Bot,
  Users,
  Globe,
  PhoneOff,
  Volume2,
  Sparkles,
} from "lucide-react";
import { useMeetingStore } from "../stores/useMeetingStore";

interface MeetingControlsProps {
  onToggleMic: () => void;
  onToggleVideo: () => void;
  onToggleScreenShare: () => void;
  onOpenLanguageModal: () => void;
  onLeaveMeeting: () => void;
}

export function MeetingControls({
  onToggleMic,
  onToggleVideo,
  onToggleScreenShare,
  onOpenLanguageModal,
  onLeaveMeeting,
}: MeetingControlsProps) {
  const {
    isMicMuted,
    isVideoEnabled,
    isScreenSharing,
    audioTrackMode,
    setAudioTrackMode,
    listeningLanguage,
    activePanel,
    setActivePanel,
    unreadChatCount,
    unreadAssistantCount,
  } = useMeetingStore();

  const togglePanel = (panel: "chat" | "assistant" | "participants") => {
    setActivePanel(activePanel === panel ? "none" : panel);
  };

  const toggleAudioMode = () => {
    setAudioTrackMode(audioTrackMode === "original" ? "translated" : "original");
  };

  return (
    <div className="h-16 border-t border-surface-200/50 bg-surface-900/90 backdrop-blur-md px-4 flex items-center justify-between z-20">
      {/* Left: Device Hardware Controls (Mic, Camera, ScreenShare) */}
      <div className="flex items-center space-x-2">
        <button
          onClick={onToggleMic}
          className={`p-3 rounded-xl border transition-all duration-150 flex items-center justify-center ${
            isMicMuted
              ? "bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title={isMicMuted ? "Unmute Microphone" : "Mute Microphone"}
        >
          {isMicMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>

        <button
          onClick={onToggleVideo}
          className={`p-3 rounded-xl border transition-all duration-150 flex items-center justify-center ${
            !isVideoEnabled
              ? "bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title={isVideoEnabled ? "Turn Off Camera" : "Turn On Camera"}
        >
          {!isVideoEnabled ? <VideoOff className="w-5 h-5" /> : <Video className="w-5 h-5" />}
        </button>

        <button
          onClick={onToggleScreenShare}
          className={`hidden sm:flex p-3 rounded-xl border transition-all duration-150 items-center justify-center ${
            isScreenSharing
              ? "bg-brand-primary/30 border-brand-primary text-blue-300"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title={isScreenSharing ? "Stop Screen Share" : "Share Screen"}
        >
          <ScreenShare className="w-5 h-5" />
        </button>
      </div>

      {/* Center: Audio Track Switcher (Original vs. AI Translated) & Language Modal */}
      <div className="flex items-center space-x-2">
        {/* Multi-Track Audio Switcher (Invariant #3 & #5) */}
        <button
          onClick={toggleAudioMode}
          className={`flex items-center space-x-2 px-3 py-2 rounded-xl border transition-all duration-200 ${
            audioTrackMode === "translated"
              ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30"
              : "bg-surface-100 border-surface-200 text-zinc-300 hover:bg-surface-200"
          }`}
          title="Switch Audio Track (Original Human vs. AI Translated)"
        >
          {audioTrackMode === "translated" ? (
            <>
              <Sparkles className="w-4 h-4 animate-pulse-subtle" />
              <span className="text-xs font-semibold uppercase tracking-wider">
                AI Voice [{listeningLanguage}]
              </span>
            </>
          ) : (
            <>
              <Volume2 className="w-4 h-4" />
              <span className="text-xs font-semibold tracking-wider">Original</span>
            </>
          )}
        </button>

        {/* Language Selector Modal Trigger */}
        <button
          onClick={onOpenLanguageModal}
          className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-surface-100 border border-surface-200 text-xs font-medium text-zinc-200 hover:bg-surface-200 transition-colors"
          title="Change Spoken / Listening Language"
        >
          <Globe className="w-4 h-4 text-brand-primary" />
          <span className="hidden md:inline">Languages</span>
        </button>
      </div>

      {/* Right: Panels (Chat, AI Copilot, Participants) & Leave Button */}
      <div className="flex items-center space-x-2">
        <button
          onClick={() => togglePanel("chat")}
          className={`relative p-3 rounded-xl border transition-all duration-150 flex items-center justify-center ${
            activePanel === "chat"
              ? "bg-brand-primary/30 border-brand-primary text-blue-300"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title="Meeting Chat"
        >
          <MessageSquare className="w-5 h-5" />
          {unreadChatCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand-primary px-1 text-[10px] font-bold text-white">
              {unreadChatCount}
            </span>
          )}
        </button>

        <button
          onClick={() => togglePanel("assistant")}
          className={`relative p-3 rounded-xl border transition-all duration-150 flex items-center justify-center ${
            activePanel === "assistant"
              ? "bg-brand-accent/30 border-brand-accent text-purple-300"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title="In-Meeting AI Copilot"
        >
          <Bot className="w-5 h-5" />
          {unreadAssistantCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-brand-accent px-1 text-[10px] font-bold text-white">
              {unreadAssistantCount}
            </span>
          )}
        </button>

        <button
          onClick={() => togglePanel("participants")}
          className={`p-3 rounded-xl border transition-all duration-150 flex items-center justify-center ${
            activePanel === "participants"
              ? "bg-brand-primary/30 border-brand-primary text-blue-300"
              : "bg-surface-100 border-surface-200 text-zinc-100 hover:bg-surface-200"
          }`}
          title="Participants Roster"
        >
          <Users className="w-5 h-5" />
        </button>

        {/* Leave Meeting Button */}
        <button
          onClick={onLeaveMeeting}
          className="p-3 rounded-xl bg-red-600 hover:bg-red-700 text-white font-semibold transition-colors flex items-center justify-center shadow-lg shadow-red-900/20"
          title="Leave Meeting"
        >
          <PhoneOff className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
