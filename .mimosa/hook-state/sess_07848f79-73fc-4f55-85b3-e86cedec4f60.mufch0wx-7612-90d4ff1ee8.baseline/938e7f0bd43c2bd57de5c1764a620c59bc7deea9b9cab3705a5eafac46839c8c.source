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
} from "lucide-react";
import { SUPPORTED_LANGUAGES, ParticipantRole, MeetingStatus } from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";
import { createRoom, joinRoom, ApiError } from "../lib/api";

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
    setVideoEnabled,
    setMicMuted,
  } = useMeetingStore();

  const [displayName, setDisplayName] = useState("Alex Johnson");
  const [meetingCode, setMeetingCode] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [isJoining, setIsJoining] = useState(false);
  const [cameraEnabled, setCameraEnabled] = useState(true);
  const [micEnabled, setMicEnabled] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Pre-fill meeting code if shared via URL query (e.g. ?room=meet_abc123)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const room = urlParams.get("room") || urlParams.get("code") || urlParams.get("join");
      if (room) {
        setMeetingCode(room);
      }
    }
  }, []);

  const videoPreviewRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Setup local hardware preview
  useEffect(() => {
    let cancelled = false;

    async function setupPreview() {
      if (!cameraEnabled) {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach((t) => t.stop());
          streamRef.current = null;
        }
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = null;
        }
        return;
      }

      // If active stream already has live tracks, keep using it
      if (
        streamRef.current &&
        streamRef.current.getVideoTracks().some((t) => t.readyState === "live")
      ) {
        if (videoPreviewRef.current && videoPreviewRef.current.srcObject !== streamRef.current) {
          videoPreviewRef.current.srcObject = streamRef.current;
          videoPreviewRef.current.muted = true;
          videoPreviewRef.current.play().catch(() => {});
        }
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: "user",
          },
          audio: false,
        });

        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        streamRef.current = stream;
        if (videoPreviewRef.current) {
          videoPreviewRef.current.srcObject = stream;
          videoPreviewRef.current.muted = true;
          videoPreviewRef.current.play().catch(() => {});
        }
      } catch (err: unknown) {
        console.warn("Retrying camera with default constraints:", err);
        try {
          if (cancelled) return;
          const fallbackStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: false,
          });
          if (cancelled) {
            fallbackStream.getTracks().forEach((t) => t.stop());
            return;
          }
          streamRef.current = fallbackStream;
          if (videoPreviewRef.current) {
            videoPreviewRef.current.srcObject = fallbackStream;
            videoPreviewRef.current.muted = true;
            videoPreviewRef.current.play().catch(() => {});
          }
        } catch (fallbackErr) {
          console.error("Camera access failed:", fallbackErr);
        }
      }
    }

    setupPreview();

    return () => {
      cancelled = true;
    };
  }, [cameraEnabled]);

  // Clean up camera hardware tracks when navigating away from lobby
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  const handleStartMeeting = async () => {
    setIsCreating(true);
    setErrorMessage(null);

    try {
      // 1. Create meeting in backend API & provision LiveKit SFU room
      const meetingTitle = `${displayName || "Host"}'s AI Meeting`;
      const createRes = await createRoom({
        title: meetingTitle,
        host_spoken_language: spokenLanguage,
        host_listening_language: listeningLanguage,
      });

      // 2. Join the created meeting room to acquire real signed tokens
      const joinRes = await joinRoom(createRes.meeting_id, {
        display_name: displayName || "Host",
        spoken_language: spokenLanguage,
        listening_language: listeningLanguage,
      });

      // 3. Populate store with genuine credentials
      setLocalParticipant({
        participantId: joinRes.participant_id,
        displayName: joinRes.display_name,
        role: joinRes.role || ParticipantRole.HOST,
        spokenLanguage,
        listeningLanguage,
      });

      setTokens({
        wsTicket: joinRes.ws_ticket,
        livekitToken: joinRes.livekit_token,
      });

      setMeetingInfo({
        meetingId: joinRes.meeting_id,
        title: meetingTitle,
        tenantId: createRes.tenant_id,
        status: createRes.status,
        stateVersion: joinRes.state_version || 1,
      });

      // Synchronize hardware controls selected in lobby
      setVideoEnabled(cameraEnabled);
      setMicMuted(!micEnabled);

      // Explicitly stop lobby preview track to release camera hardware lock
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      router.push(`/meeting/${joinRes.meeting_id}`);
    } catch (err: unknown) {
      console.error("Failed to start meeting:", err);
      let msg = "Failed to create meeting room. Please check backend connectivity.";
      if (err instanceof ApiError) {
        if (err.status === 401) {
          msg = "Authentication failed (401): Invalid or expired credentials. Please log in.";
        } else if (err.status === 403) {
          msg =
            "Authorization error (403): You do not have permission to host meetings in this tenant.";
        } else if (err.status === 422) {
          msg = `Validation error (422): ${err.message}`;
        } else {
          msg = `Server error (${err.status}): ${err.message}`;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setErrorMessage(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleJoinMeeting = async () => {
    const code = meetingCode.trim();
    if (!code) return;
    setIsJoining(true);
    setErrorMessage(null);

    try {
      // Join existing room via backend API to acquire real signed tokens
      const joinRes = await joinRoom(code, {
        display_name: displayName || "Attendee",
        spoken_language: spokenLanguage,
        listening_language: listeningLanguage,
      });

      setLocalParticipant({
        participantId: joinRes.participant_id,
        displayName: joinRes.display_name,
        role: joinRes.role || ParticipantRole.PARTICIPANT,
        spokenLanguage,
        listeningLanguage,
      });

      setTokens({
        wsTicket: joinRes.ws_ticket,
        livekitToken: joinRes.livekit_token,
      });

      setMeetingInfo({
        meetingId: joinRes.meeting_id,
        title: "Multilingual AI Meeting",
        tenantId: "default",
        status: MeetingStatus.ACTIVE,
        stateVersion: joinRes.state_version || 1,
      });

      // Synchronize hardware controls selected in lobby
      setVideoEnabled(cameraEnabled);
      setMicMuted(!micEnabled);

      // Explicitly stop lobby preview track to release camera hardware lock
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
        streamRef.current = null;
      }

      router.push(`/meeting/${code}`);
    } catch (err: unknown) {
      console.error("Failed to join meeting:", err);
      let msg = "Failed to join meeting room. Please check meeting ID and passcode.";
      if (err instanceof ApiError) {
        if (err.status === 401) {
          msg = "Authentication failed (401): Invalid or expired credentials.";
        } else if (err.status === 403) {
          msg = "Access denied (403): You are not authorized to join this meeting room.";
        } else if (err.status === 404) {
          msg = "Meeting room not found (404). Please verify the meeting ID.";
        } else if (err.status === 422) {
          msg = `Validation error (422): ${err.message}`;
        } else {
          msg = `Server error (${err.status}): ${err.message}`;
        }
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setErrorMessage(msg);
    } finally {
      setIsJoining(false);
    }
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
            <h1 className="text-lg font-bold text-zinc-100">Multilingual AI Meeting Platform</h1>
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

      {/* Error Alert Banner */}
      {errorMessage && (
        <div className="max-w-4xl w-full mb-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm flex items-center justify-between">
          <span>{errorMessage}</span>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs text-rose-400 hover:text-rose-200 underline ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Grid: Device Preview & Room Entry */}
      <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Left: Device Hardware Preview (7 cols) */}
        <div className="md:col-span-7 flex flex-col space-y-4">
          <div className="relative aspect-video w-full rounded-2xl overflow-hidden bg-surface-800 border border-surface-200 shadow-2xl flex items-center justify-center">
            {cameraEnabled ? (
              <video
                ref={(el) => {
                  videoPreviewRef.current = el;
                  if (el && streamRef.current && el.srcObject !== streamRef.current) {
                    el.srcObject = streamRef.current;
                    el.muted = true;
                    el.play().catch(() => {});
                  }
                }}
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
