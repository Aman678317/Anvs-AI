"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Globe2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  PlusCircle,
  LogIn,
} from "lucide-react";
import { SUPPORTED_LANGUAGES, ParticipantRole } from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";

export default function LobbyPage() {
  const router = useRouter();
  const {
    setLocalParticipant,
    setMeetingInfo,
    setTokens,
    spokenLanguage,
    listeningLanguage,
    setSpokenLanguage,
    setListeningLanguage,
  } = useMeetingStore();

  const [displayName, setDisplayName] = useState("Alex Johnson");
  const [meetingCode, setMeetingCode] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(true);
  const [micEnabled, setMicEnabled] = useState(true);

  const videoPreviewRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Setup local hardware preview
  useEffect(() => {
    let active = true;

    async function setupPreview() {
      try {
        if (cameraEnabled || micEnabled) {
          const stream = await navigator.mediaDevices.getUserMedia({
            video: cameraEnabled,
            audio: micEnabled,
          });
          if (!active) {
            stream.getTracks().forEach((t) => t.stop());
            return;
          }
          streamRef.current = stream;
          if (videoPreviewRef.current && cameraEnabled) {
            videoPreviewRef.current.srcObject = stream;
          }
        } else {
          if (streamRef.current) {
            streamRef.current.getTracks().forEach((t) => t.stop());
            streamRef.current = null;
          }
        }
      } catch (err) {
        console.warn("Media device preview unavailable:", err);
      }
    }

    setupPreview();

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, [cameraEnabled, micEnabled]);

  const handleStartMeeting = async () => {
    setIsCreating(true);
    const newMeetingId = `meet_${Math.random().toString(36).substring(2, 9)}`;
    const newParticipantId = `user_${Math.random().toString(36).substring(2, 7)}`;

    // Store local identity
    setLocalParticipant({
      participantId: newParticipantId,
      displayName: displayName || "Host",
      role: ParticipantRole.HOST,
      spokenLanguage,
      listeningLanguage,
    });

    // Provide dual tokens for local dev/testing
    setTokens({
      wsTicket: `ticket_${newParticipantId}_${Date.now()}`,
      livekitToken: `fake_lk_token_${newParticipantId}`,
    });

    setMeetingInfo({
      meetingId: newMeetingId,
      title: `${displayName}'s AI Meeting`,
      tenantId: "tenant_default",
      status: "ACTIVE" as any,
      stateVersion: 1,
    });

    router.push(`/meeting/${newMeetingId}`);
  };

  const handleJoinMeeting = async () => {
    if (!meetingCode.trim()) return;
    setIsJoining(true);

    const participantId = `user_${Math.random().toString(36).substring(2, 7)}`;

    setLocalParticipant({
      participantId,
      displayName: displayName || "Attendee",
      role: ParticipantRole.PARTICIPANT,
      spokenLanguage,
      listeningLanguage,
    });

    setTokens({
      wsTicket: `ticket_${participantId}_${Date.now()}`,
      livekitToken: `fake_lk_token_${participantId}`,
    });

    router.push(`/meeting/${meetingCode.trim()}`);
  };

  const languagesList = Object.values(SUPPORTED_LANGUAGES);

  return (
    <main className="min-h-screen bg-surface-900 flex flex-col items-center justify-center p-4 md:p-8">
      {/* Top Banner */}
      <div className="max-w-4xl w-full flex items-center justify-between pb-8">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-primary to-brand-accent flex items-center justify-center text-white shadow-lg">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-zinc-100">
              Multilingual AI Meeting Platform
            </h1>
            <p className="text-xs text-zinc-400">
              Zero-latency speech translation & grounded RAG copilot
            </p>
          </div>
        </div>

        <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1 rounded-full bg-surface-100 border border-surface-200 text-xs text-zinc-400">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>PostgreSQL RLS & E2E Isolated</span>
        </div>
      </div>

      {/* Main Grid: Device Preview & Room Entry */}
      <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Left: Device Hardware Preview (7 cols) */}
        <div className="md:col-span-7 flex flex-col space-y-4">
          <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-surface-800 border border-surface-200 shadow-2xl flex items-center justify-center">
            {cameraEnabled ? (
              <video
                ref={videoPreviewRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover scale-x-[-1]"
              />
            ) : (
              <div className="flex flex-col items-center space-y-2 text-zinc-500">
                <VideoOff className="w-12 h-12 stroke-[1.5]" />
                <span className="text-xs">Camera is turned off</span>
              </div>
            )}

            {/* Quick Toggle Overlay */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center space-x-3 bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-full border border-white/10">
              <button
                onClick={() => setMicEnabled(!micEnabled)}
                className={`p-2 rounded-full transition-colors ${
                  micEnabled
                    ? "bg-surface-100 text-zinc-200 hover:bg-surface-200"
                    : "bg-red-500/30 text-red-400"
                }`}
                title={micEnabled ? "Mute Mic" : "Unmute Mic"}
              >
                {micEnabled ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
              </button>

              <button
                onClick={() => setCameraEnabled(!cameraEnabled)}
                className={`p-2 rounded-full transition-colors ${
                  cameraEnabled
                    ? "bg-surface-100 text-zinc-200 hover:bg-surface-200"
                    : "bg-red-500/30 text-red-400"
                }`}
                title={cameraEnabled ? "Turn Off Camera" : "Turn On Camera"}
              >
                {cameraEnabled ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Language Pair Selectors */}
          <div className="p-4 rounded-xl bg-surface-800/80 border border-surface-200 grid grid-cols-2 gap-3 text-xs">
            <div>
              <label className="text-zinc-400 font-medium flex items-center space-x-1 mb-1.5">
                <Globe2 className="w-3.5 h-3.5 text-brand-primary" />
                <span>My Spoken Language</span>
              </label>
              <select
                value={spokenLanguage}
                onChange={(e) => setSpokenLanguage(e.target.value)}
                className="w-full bg-surface-100 border border-surface-200 rounded-lg px-2.5 py-2 text-zinc-100 focus:outline-none focus:border-brand-primary"
              >
                {languagesList.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.code.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-zinc-400 font-medium flex items-center space-x-1 mb-1.5">
                <Globe2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>My Subtitle Language</span>
              </label>
              <select
                value={listeningLanguage}
                onChange={(e) => setListeningLanguage(e.target.value)}
                className="w-full bg-surface-100 border border-surface-200 rounded-lg px-2.5 py-2 text-zinc-100 focus:outline-none focus:border-emerald-500"
              >
                {languagesList.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.name_en} ({l.code.toUpperCase()})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Right: Join & Create Forms (5 cols) */}
        <div className="md:col-span-5 flex flex-col space-y-4">
          <div className="p-5 rounded-2xl bg-surface-800 border border-surface-200 shadow-xl space-y-4">
            <div>
              <label className="block text-xs font-semibold text-zinc-300 mb-1.5">
                Your Display Name
              </label>
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g. Sarah Connor"
                className="w-full bg-surface-100 border border-surface-200 rounded-xl px-3 py-2.5 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
              />
            </div>

            {/* Instant Meeting Action */}
            <button
              onClick={handleStartMeeting}
              disabled={isCreating || !displayName.trim()}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-brand-primary to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white font-semibold text-sm transition-all flex items-center justify-center space-x-2 shadow-lg shadow-blue-500/20 disabled:opacity-50"
            >
              <PlusCircle className="w-4 h-4" />
              <span>{isCreating ? "Starting..." : "Start Instant Meeting"}</span>
            </button>

            <div className="relative flex items-center justify-center">
              <div className="border-t border-surface-200 w-full" />
              <span className="bg-surface-800 px-2 text-[11px] text-zinc-500 uppercase tracking-wider absolute">
                or join with code
              </span>
            </div>

            {/* Join by Code Action */}
            <div className="flex space-x-2">
              <input
                type="text"
                value={meetingCode}
                onChange={(e) => setMeetingCode(e.target.value)}
                placeholder="Enter room ID (e.g. meet_abc123)"
                className="flex-1 bg-surface-100 border border-surface-200 rounded-xl px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-brand-primary"
              />
              <button
                onClick={handleJoinMeeting}
                disabled={isJoining || !meetingCode.trim() || !displayName.trim()}
                className="px-4 py-2 rounded-xl bg-surface-100 hover:bg-surface-200 border border-surface-200 text-zinc-100 text-xs font-semibold flex items-center space-x-1.5 disabled:opacity-40 transition-colors"
              >
                <span>Join</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
