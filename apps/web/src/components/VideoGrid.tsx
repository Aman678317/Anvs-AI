"use client";

import { useMeetingStore } from "../stores/useMeetingStore";
import { ParticipantTile } from "./ParticipantTile";
import { LocalVideoTrack, RemoteVideoTrack } from "livekit-client";

interface VideoGridProps {
  localVideoTrack?: LocalVideoTrack | null;
  screenTrack?: LocalVideoTrack | null;
}

export function VideoGrid({ localVideoTrack, screenTrack }: VideoGridProps) {
  const {
    participantId,
    displayName,
    isVideoEnabled,
    isMicMuted,
    spokenLanguage,
    participants,
    activeSpeakers,
    isScreenSharing,
  } = useMeetingStore();

  const remoteList = Object.values(participants);
  const totalCount = remoteList.length + 1; // +1 for self

  // Dynamic grid configuration
  const getGridClasses = () => {
    if (isScreenSharing || screenTrack) {
      return "grid-cols-1 md:grid-cols-4";
    }
    if (totalCount === 1) return "grid-cols-1 max-w-4xl mx-auto";
    if (totalCount === 2) return "grid-cols-1 md:grid-cols-2";
    if (totalCount <= 4) return "grid-cols-1 md:grid-cols-2 lg:grid-cols-2";
    if (totalCount <= 6) return "grid-cols-2 md:grid-cols-3";
    if (totalCount <= 9) return "grid-cols-2 md:grid-cols-3 lg:grid-cols-3";
    return "grid-cols-2 md:grid-cols-4";
  };

  return (
    <div className="flex-1 w-full h-full p-3 md:p-4 overflow-hidden flex flex-col justify-center">
      {/* Screen Share Dominant Mode */}
      {screenTrack && (
        <div className="w-full h-3/4 mb-3 rounded-xl overflow-hidden border border-surface-200 bg-black flex items-center justify-center relative">
          <video
            ref={(el) => {
              if (el && screenTrack) screenTrack.attach(el);
            }}
            autoPlay
            playsInline
            className="w-full h-full object-contain"
          />
          <div className="absolute top-3 left-3 bg-black/70 px-2.5 py-1 rounded-md text-xs font-semibold text-white border border-white/10">
            Screen Share
          </div>
        </div>
      )}

      {/* Main Video Tiles Grid */}
      <div
        className={`grid gap-3 w-full h-full items-center justify-center ${getGridClasses()} ${
          screenTrack ? "h-1/4" : ""
        }`}
      >
        {/* Local Self Tile */}
        <div className="w-full h-full min-h-[160px]">
          <ParticipantTile
            participantId={participantId || "local"}
            displayName={displayName}
            isSelf={true}
            isVideoEnabled={isVideoEnabled}
            isMuted={isMicMuted}
            isSpeaking={activeSpeakers.includes(participantId || "")}
            spokenLanguage={spokenLanguage}
            videoTrack={localVideoTrack}
          />
        </div>

        {/* Remote Participant Tiles */}
        {remoteList.map((p) => (
          <div key={p.participant_id} className="w-full h-full min-h-[160px]">
            <ParticipantTile
              participantId={p.participant_id}
              displayName={p.display_name}
              isSelf={false}
              isVideoEnabled={p.is_video_enabled}
              isMuted={p.is_muted}
              isSpeaking={activeSpeakers.includes(p.participant_id)}
              spokenLanguage={p.spoken_language}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
