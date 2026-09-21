"use client";

import { useEffect, useState } from "react";
import { useMeetingStore } from "../stores/useMeetingStore";
import { Activity, Users, Globe2, Volume2, Sparkles } from "lucide-react";

export function Header() {
  const {
    title,
    isWsConnected,
    isLiveKitConnected,
    wsLatencyMs,
    participants,
    audioTrackMode,
    listeningLanguage,
    spokenLanguage,
  } = useMeetingStore();

  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSec((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const formatDuration = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60)
      .toString()
      .padStart(2, "0");
    const secs = (totalSec % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const participantCount = Object.keys(participants).length + 1; // +1 for self

  return (
    <header className="h-14 border-b border-surface-200/50 bg-surface-900/80 backdrop-blur-md px-4 flex items-center justify-between z-20">
      <div className="flex items-center space-x-3">
        {/* Live Indicator */}
        <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-surface-100 border border-surface-200">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-semibold tracking-wider uppercase text-emerald-400">
            LIVE
          </span>
        </div>

        {/* Meeting Title & Timer */}
        <div className="flex items-center space-x-2">
          <h1 className="text-sm font-semibold text-zinc-100 max-w-xs truncate">
            {title || "AI Meeting Session"}
          </h1>
          <span className="text-xs text-zinc-500">|</span>
          <span className="text-xs text-zinc-400 font-mono">{formatDuration(elapsedSec)}</span>
        </div>
      </div>

      {/* Center badges: AI Translation & Audio Router */}
      <div className="hidden md:flex items-center space-x-2">
        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface-100/80 border border-surface-200/60 text-xs text-zinc-300">
          <Globe2 className="w-3.5 h-3.5 text-brand-primary" />
          <span className="font-mono text-zinc-400 uppercase">{spokenLanguage}</span>
          <span className="text-zinc-600">→</span>
          <span className="font-mono text-emerald-400 font-semibold uppercase">
            {listeningLanguage}
          </span>
        </div>

        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface-100/80 border border-surface-200/60 text-xs">
          {audioTrackMode === "translated" ? (
            <>
              <Sparkles className="w-3.5 h-3.5 text-emerald-400 animate-pulse-subtle" />
              <span className="text-emerald-400 font-medium">
                AI Voice ({listeningLanguage.toUpperCase()})
              </span>
            </>
          ) : (
            <>
              <Volume2 className="w-3.5 h-3.5 text-zinc-400" />
              <span className="text-zinc-300 font-medium">Original Audio</span>
            </>
          )}
        </div>
      </div>

      {/* Right: Network telemetry & Participants count */}
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-1.5 text-xs text-zinc-400 bg-surface-100 px-2 py-1 rounded-md border border-surface-200">
          <Activity
            className={`w-3.5 h-3.5 ${
              isWsConnected && isLiveKitConnected ? "text-emerald-400" : "text-amber-400"
            }`}
          />
          <span className="font-mono">{wsLatencyMs > 0 ? `${wsLatencyMs}ms` : "OK"}</span>
        </div>

        <div className="flex items-center space-x-1 text-xs text-zinc-300 bg-surface-100 px-2 py-1 rounded-md border border-surface-200">
          <Users className="w-3.5 h-3.5 text-zinc-400" />
          <span>{participantCount}</span>
        </div>
      </div>
    </header>
  );
}
