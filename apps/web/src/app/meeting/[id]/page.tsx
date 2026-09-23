"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Header } from "../../../components/Header";
import { VideoGrid } from "../../../components/VideoGrid";
import { CaptionOverlay } from "../../../components/CaptionOverlay";
import { MeetingControls } from "../../../components/MeetingControls";
import { ChatPanel } from "../../../components/ChatPanel";
import { AssistantPanel } from "../../../components/AssistantPanel";
import { ParticipantsPanel } from "../../../components/ParticipantsPanel";
import { LanguageSelectorModal } from "../../../components/LanguageSelectorModal";
import { useMeetingStore } from "../../../stores/useMeetingStore";
import { useRealtimeGateway } from "../../../hooks/useRealtimeGateway";
import { useLiveKitRoom } from "../../../hooks/useLiveKitRoom";
import { useAudioRouter } from "../../../hooks/useAudioRouter";
import { joinRoom } from "../../../lib/api";
import { MeetingStatus } from "@multilingual/contracts";

export default function MeetingRoomPage() {
  const params = useParams();
  const router = useRouter();
  const meetingId = (params?.id as string) || "default-meeting";

  const {
    participantId,
    displayName,
    wsTicket,
    livekitToken,
    activePanel,
    setActivePanel,
    setLocalParticipant,
    setTokens,
    setMeetingInfo,
    spokenLanguage,
    listeningLanguage,
  } = useMeetingStore();

  const [isLanguageModalOpen, setIsLanguageModalOpen] = useState(false);
  const [isJoining, setIsJoining] = useState(!participantId || !wsTicket || !livekitToken);
  const [joinError, setJoinError] = useState<string | null>(null);

  // Authenticate and join room via backend API to obtain real signed LiveKit & WebSocket tokens
  const handleJoin = useCallback(async () => {
    setIsJoining(true);
    setJoinError(null);
    try {
      const resp = await joinRoom(meetingId, {
        display_name: displayName || "Guest Attendee",
        spoken_language: spokenLanguage || "eng",
        listening_language: listeningLanguage || "eng",
      });

      setLocalParticipant({
        participantId: resp.participant_id,
        displayName: resp.display_name,
        role: resp.role,
        spokenLanguage: spokenLanguage || "eng",
        listeningLanguage: listeningLanguage || "eng",
      });
      setTokens({
        wsTicket: resp.ws_ticket,
        livekitToken: resp.livekit_token,
      });
      setMeetingInfo({
        meetingId: resp.meeting_id,
        title: "Multilingual AI Meeting",
        tenantId: "tenant_default",
        status: MeetingStatus.ACTIVE,
        stateVersion: resp.state_version,
      });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to join meeting room. Check backend connection.";
      console.error("Failed to join meeting room:", err);
      setJoinError(msg);
    } finally {
      setIsJoining(false);
    }
  }, [
    meetingId,
    displayName,
    spokenLanguage,
    listeningLanguage,
    setLocalParticipant,
    setTokens,
    setMeetingInfo,
  ]);

  useEffect(() => {
    if (!participantId || !wsTicket || !livekitToken) {
      handleJoin();
    }
  }, [participantId, wsTicket, livekitToken, handleJoin]);

  // 1. Initialize Realtime WebSocket Gateway (Invariant #4 & #5)
  const { sendChatMessage, queryAssistant, updateListeningLanguage } = useRealtimeGateway(
    meetingId,
    participantId,
    wsTicket,
  );

  // 2. Initialize LiveKit WebRTC SFU Media Connection
  const { room, localVideoTrack, screenTrack, toggleMic, toggleVideo, toggleScreenShare } =
    useLiveKitRoom(undefined, livekitToken);

  // 3. Initialize Multi-Track Audio Router (Invariant #3 & #5)
  useAudioRouter(room);

  if (isJoining) {
    return (
      <div className="flex flex-col items-center justify-center h-screen w-screen bg-surface-900 text-zinc-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500 mb-4" />
        <h2 className="text-xl font-semibold">Connecting to Meeting Room...</h2>
        <p className="text-sm text-zinc-400 mt-2">
          Provisioning secure SFU credentials and data streams
        </p>
      </div>
    );
  }

  if (joinError) {
    return (
      <div className="flex flex-col items-center justify-center h-screen w-screen bg-surface-900 text-zinc-100 p-6">
        <div className="bg-red-950/40 border border-red-700/50 rounded-2xl p-8 max-w-md w-full text-center backdrop-blur-md">
          <div className="w-12 h-12 rounded-full bg-red-900/60 text-red-400 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-red-200 mb-2">Connection Failed</h2>
          <p className="text-sm text-zinc-400 mb-6">{joinError}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => router.push("/")}
              className="px-4 py-2 bg-surface-800 hover:bg-surface-700 rounded-lg text-sm text-zinc-300 font-medium transition"
            >
              Return Home
            </button>
            <button
              onClick={() => handleJoin()}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm text-white font-medium transition shadow-lg shadow-indigo-600/30"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-surface-900 text-zinc-100 overflow-hidden select-none">
      {/* Top Header & Telemetry */}
      <Header />

      {/* Center Layout: Video Grid + Sliding Drawers */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Main Video & Media Grid */}
        <main className="flex-1 flex flex-col relative overflow-hidden">
          <VideoGrid localVideoTrack={localVideoTrack} screenTrack={screenTrack} />

          {/* Subtitles & Captions Overlay (Invariant #2 Lineage) */}
          <CaptionOverlay />
        </main>

        {/* Side Panels */}
        {activePanel === "chat" && (
          <ChatPanel onSendMessage={sendChatMessage} onClose={() => setActivePanel("none")} />
        )}

        {activePanel === "assistant" && (
          <AssistantPanel onAskQuery={queryAssistant} onClose={() => setActivePanel("none")} />
        )}

        {activePanel === "participants" && (
          <ParticipantsPanel onClose={() => setActivePanel("none")} />
        )}
      </div>

      {/* Bottom Meeting Controls */}
      <MeetingControls
        onToggleMic={toggleMic}
        onToggleVideo={toggleVideo}
        onToggleScreenShare={toggleScreenShare}
        onOpenLanguageModal={() => setIsLanguageModalOpen(true)}
        onLeaveMeeting={() => router.push("/")}
      />

      {/* Language Preference Configuration Modal */}
      <LanguageSelectorModal
        isOpen={isLanguageModalOpen}
        onClose={() => setIsLanguageModalOpen(false)}
        onLanguageChanged={updateListeningLanguage}
      />
    </div>
  );
}
