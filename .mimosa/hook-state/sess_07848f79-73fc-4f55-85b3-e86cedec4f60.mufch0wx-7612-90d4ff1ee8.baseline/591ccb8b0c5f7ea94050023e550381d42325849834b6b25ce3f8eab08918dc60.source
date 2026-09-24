"use client";

import { useEffect, useRef } from "react";
import { Mic, MicOff, User } from "lucide-react";
import { LocalVideoTrack, RemoteVideoTrack, Track } from "livekit-client";

interface ParticipantTileProps {
  participantId: string;
  displayName: string;
  isSelf?: boolean;
  isVideoEnabled: boolean;
  isMuted: boolean;
  isSpeaking: boolean;
  spokenLanguage?: string;
  videoTrack?: LocalVideoTrack | RemoteVideoTrack | Track | MediaStreamTrack | MediaStream | null;
}

export function ParticipantTile({
  displayName,
  isSelf = false,
  isVideoEnabled,
  isMuted,
  isSpeaking,
  spokenLanguage = "eng",
  videoTrack,
}: ParticipantTileProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Helper to safely attach any track format (LiveKit track, MediaStreamTrack, or MediaStream)
  const attachTrackToElement = (
    track: LocalVideoTrack | RemoteVideoTrack | Track | MediaStreamTrack | MediaStream,
    el: HTMLVideoElement,
  ) => {
    try {
      el.muted = isSelf;
      if ("attach" in track && typeof (track as any).attach === "function") {
        (track as any).attach(el);
      } else if (
        track instanceof MediaStream ||
        (track && typeof (track as any).getTracks === "function")
      ) {
        el.srcObject = track as MediaStream;
      } else if (track && (track instanceof MediaStreamTrack || (track as any).kind === "video")) {
        el.srcObject = new MediaStream([track as MediaStreamTrack]);
      } else if (track && (track as any).mediaStreamTrack) {
        el.srcObject = new MediaStream([(track as any).mediaStreamTrack]);
      }
      el.play().catch(() => {});
    } catch (e) {
      console.warn("Could not attach video track to element:", e);
    }
  };

  const detachTrackFromElement = (
    track: LocalVideoTrack | RemoteVideoTrack | Track | MediaStreamTrack | MediaStream,
    el: HTMLVideoElement,
  ) => {
    try {
      if ("detach" in track && typeof (track as any).detach === "function") {
        (track as any).detach(el);
      }
      if (el.srcObject) {
        el.srcObject = null;
      }
    } catch (e) {
      console.warn("Could not detach video track from element:", e);
    }
  };

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !videoTrack || !isVideoEnabled) {
      return;
    }

    attachTrackToElement(videoTrack, el);

    return () => {
      detachTrackFromElement(videoTrack, el);
    };
  }, [videoTrack, isVideoEnabled, isSelf]);

  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div
      className={`relative w-full h-full rounded-xl overflow-hidden bg-surface-800 border transition-all duration-200 flex items-center justify-center ${
        isSpeaking
          ? "border-emerald-500 speaker-active-halo"
          : "border-surface-200/50 hover:border-surface-300"
      }`}
    >
      {/* Video stream rendering */}
      {isVideoEnabled && videoTrack ? (
        <video
          ref={(el) => {
            videoRef.current = el;
            if (el && videoTrack && isVideoEnabled) {
              attachTrackToElement(videoTrack, el);
            }
          }}
          autoPlay
          playsInline
          muted={isSelf}
          className={`w-full h-full object-cover ${isSelf ? "scale-x-[-1]" : ""}`}
        />
      ) : (
        /* Avatar fallback when video is disabled or track unavailable */
        <div className="flex flex-col items-center justify-center space-y-2 select-none">
          <div className="w-16 h-16 md:w-20 md:h-20 rounded-full bg-gradient-to-tr from-brand-primary/40 to-brand-accent/40 border border-surface-200 flex items-center justify-center text-zinc-200 font-bold text-lg md:text-xl shadow-inner">
            {initials || <User className="w-8 h-8 text-zinc-400" />}
          </div>
        </div>
      )}

      {/* Bottom overlay: Name and status badges */}
      <div className="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between pointer-events-none z-10">
        <div className="flex items-center space-x-1.5 px-2 py-1 rounded-md bg-black/60 backdrop-blur-md border border-white/10 text-xs font-medium text-white max-w-[70%]">
          <span className="truncate">
            {displayName} {isSelf && "(You)"}
          </span>
          {spokenLanguage && (
            <span className="text-[10px] text-zinc-400 font-mono uppercase bg-white/10 px-1 rounded">
              {spokenLanguage}
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1">
          <div
            className={`p-1.5 rounded-md backdrop-blur-md border border-white/10 ${
              isMuted ? "bg-red-500/30 text-red-400" : "bg-black/60 text-emerald-400"
            }`}
          >
            {isMuted ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
          </div>
        </div>
      </div>
    </div>
  );
}
