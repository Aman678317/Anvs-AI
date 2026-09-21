"use client";

import { useEffect, useState } from "react";
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
import { ParticipantRole } from "@multilingual/contracts";

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

  // Auto-provision fallback credentials if directly navigated to URL
  useEffect(() => {
    if (!participantId || !wsTicket) {
      const generatedPid = `user_${Math.random().toString(36).substring(2, 7)}`;
      setLocalParticipant({
        participantId: generatedPid,
        displayName: displayName || "Guest Attendee",
        role: ParticipantRole.PARTICIPANT,
        spokenLanguage: spokenLanguage || "eng",
        listeningLanguage: listeningLanguage || "eng",
      });
      setTokens({
        wsTicket: `ticket_${generatedPid}_${Date.now()}`,
        livekitToken: `fake_lk_token_${generatedPid}`,
      });
      setMeetingInfo({
        meetingId,
        title: "Multilingual AI Meeting",
        tenantId: "tenant_default",
        status: "ACTIVE" as any,
        stateVersion: 1,
      });
    }
  }, [
    meetingId,
    participantId,
    wsTicket,
    displayName,
    spokenLanguage,
    listeningLanguage,
    setLocalParticipant,
    setTokens,
    setMeetingInfo,
  ]);

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
