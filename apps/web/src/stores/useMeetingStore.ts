import { create } from "zustand";
import { MeetingStatus, ParticipantRole } from "@multilingual/contracts";
import {
  AudioTrackMetadata,
  AudioTrackMode,
  CaptionSegment,
  ChatMessage,
  AssistantQueryItem,
  DrawerPanel,
  MeetingParticipant,
} from "../types/meeting";

interface MeetingStoreState {
  // Meeting metadata
  meetingId: string | null;
  title: string;
  tenantId: string | null;
  status: MeetingStatus;
  stateVersion: number;

  // Local participant
  participantId: string | null;
  displayName: string;
  role: ParticipantRole;
  spokenLanguage: string;
  listeningLanguage: string;
  wsTicket: string | null;
  livekitToken: string | null;

  // Controls & Hardware state
  isMicMuted: boolean;
  isVideoEnabled: boolean;
  isScreenSharing: boolean;

  // Audio Router state (Invariant #3 & #5)
  audioTrackMode: AudioTrackMode;
  originalGain: number;
  translatedGain: number;
  bilingualCaptions: boolean;
  availableTracks: AudioTrackMetadata[];

  // Real-time Gateway state
  isWsConnected: boolean;
  isLiveKitConnected: boolean;
  wsLatencyMs: number;

  // Remote participants
  participants: Record<string, MeetingParticipant>;
  activeSpeakers: string[];

  // Subtitles & Captions (Invariant #2 Lineage)
  captions: CaptionSegment[];

  // Chat
  chatMessages: ChatMessage[];
  unreadChatCount: number;

  // AI RAG Copilot
  assistantQueries: AssistantQueryItem[];
  meetingActionItems: string[];
  unreadAssistantCount: number;

  // Active UI side panel
  activePanel: DrawerPanel;

  // Actions
  setMeetingInfo: (info: {
    meetingId: string;
    title: string;
    tenantId: string;
    status: MeetingStatus;
    stateVersion: number;
  }) => void;
  setLocalParticipant: (participant: {
    participantId: string;
    displayName: string;
    role: ParticipantRole;
    spokenLanguage: string;
    listeningLanguage: string;
  }) => void;
  setTokens: (tokens: { wsTicket: string; livekitToken: string }) => void;
  setParticipants: (participants: MeetingParticipant[]) => void;
  upsertParticipant: (participant: MeetingParticipant) => void;
  removeParticipant: (participantId: string) => void;
  setActiveSpeakers: (speakerIds: string[]) => void;
  setMicMuted: (muted: boolean) => void;
  setVideoEnabled: (enabled: boolean) => void;
  setScreenSharing: (sharing: boolean) => void;
  setAudioTrackMode: (mode: AudioTrackMode) => void;
  setOriginalGain: (gain: number) => void;
  setTranslatedGain: (gain: number) => void;
  setBilingualCaptions: (enabled: boolean) => void;
  setAvailableTracks: (tracks: AudioTrackMetadata[]) => void;
  addAvailableTrack: (track: AudioTrackMetadata) => void;
  setWsConnected: (connected: boolean) => void;
  setLiveKitConnected: (connected: boolean) => void;
  setWsLatencyMs: (ms: number) => void;
  upsertCaption: (caption: CaptionSegment) => void;
  addChatMessage: (msg: ChatMessage) => void;
  addAssistantQuery: (query: AssistantQueryItem) => void;
  resolveAssistantResponse: (res: {
    query_id: string;
    answer: string;
    citations: string[];
    action_items: string[];
  }) => void;
  setActivePanel: (panel: DrawerPanel) => void;
  setListeningLanguage: (lang: string) => void;
  setSpokenLanguage: (lang: string) => void;
  reset: () => void;
}

const initialState = {
  meetingId: null,
  title: "Live Meeting",
  tenantId: null,
  status: MeetingStatus.SCHEDULED,
  stateVersion: 0,
  participantId: null,
  displayName: "Participant",
  role: ParticipantRole.PARTICIPANT,
  spokenLanguage: "eng",
  listeningLanguage: "eng",
  wsTicket: null,
  livekitToken: null,
  isMicMuted: false,
  isVideoEnabled: true,
  isScreenSharing: false,
  audioTrackMode: "translated" as AudioTrackMode,
  originalGain: 1.0,
  translatedGain: 1.0,
  bilingualCaptions: true,
  availableTracks: [],
  isWsConnected: false,
  isLiveKitConnected: false,
  wsLatencyMs: 0,
  participants: {},
  activeSpeakers: [],
  captions: [],
  chatMessages: [],
  unreadChatCount: 0,
  assistantQueries: [],
  meetingActionItems: [],
  unreadAssistantCount: 0,
  activePanel: "none" as DrawerPanel,
};

export const useMeetingStore = create<MeetingStoreState>((set) => ({
  ...initialState,

  setMeetingInfo: (info) =>
    set((state) => ({
      meetingId: info.meetingId,
      title: info.title,
      tenantId: info.tenantId,
      status: info.status,
      stateVersion: Math.max(state.stateVersion, info.stateVersion),
    })),

  setLocalParticipant: (p) =>
    set({
      participantId: p.participantId,
      displayName: p.displayName,
      role: p.role,
      spokenLanguage: p.spokenLanguage,
      listeningLanguage: p.listeningLanguage,
    }),

  setTokens: ({ wsTicket, livekitToken }) =>
    set({ wsTicket, livekitToken }),

  setParticipants: (list) =>
    set({
      participants: list.reduce<Record<string, MeetingParticipant>>(
        (acc, item) => {
          acc[item.participant_id] = item;
          return acc;
        },
        {}
      ),
    }),

  upsertParticipant: (p) =>
    set((state) => ({
      participants: {
        ...state.participants,
        [p.participant_id]: {
          ...state.participants[p.participant_id],
          ...p,
        },
      },
    })),

  removeParticipant: (id) =>
    set((state) => {
      const next = { ...state.participants };
      delete next[id];
      return { participants: next };
    }),

  setActiveSpeakers: (speakerIds) => set({ activeSpeakers: speakerIds }),

  setMicMuted: (isMicMuted) => set({ isMicMuted }),
  setVideoEnabled: (isVideoEnabled) => set({ isVideoEnabled }),
  setScreenSharing: (isScreenSharing) => set({ isScreenSharing }),

  setAudioTrackMode: (audioTrackMode) => set({ audioTrackMode }),
  setOriginalGain: (originalGain) => set({ originalGain }),
  setTranslatedGain: (translatedGain) => set({ translatedGain }),
  setBilingualCaptions: (bilingualCaptions) => set({ bilingualCaptions }),

  setAvailableTracks: (availableTracks) => set({ availableTracks }),
  addAvailableTrack: (track) =>
    set((state) => ({
      availableTracks: [
        ...state.availableTracks.filter((t) => t.track_sid !== track.track_sid),
        track,
      ],
    })),

  setWsConnected: (isWsConnected) => set({ isWsConnected }),
  setLiveKitConnected: (isLiveKitConnected) => set({ isLiveKitConnected }),
  setWsLatencyMs: (wsLatencyMs) => set({ wsLatencyMs }),

  upsertCaption: (caption) =>
    set((state) => {
      // Find existing segment by source_segment_id for in-place streaming update
      const existingIdx = state.captions.findIndex(
        (c) => c.source_segment_id === caption.source_segment_id
      );

      let nextCaptions: CaptionSegment[];
      if (existingIdx >= 0) {
        nextCaptions = [...state.captions];
        nextCaptions[existingIdx] = {
          ...nextCaptions[existingIdx],
          ...caption,
        };
      } else {
        nextCaptions = [...state.captions, caption];
      }

      // Maintain rolling history of latest 50 segments
      if (nextCaptions.length > 50) {
        nextCaptions = nextCaptions.slice(nextCaptions.length - 50);
      }

      return { captions: nextCaptions };
    }),

  addChatMessage: (msg) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, msg],
      unreadChatCount:
        state.activePanel === "chat"
          ? 0
          : state.unreadChatCount + (msg.is_self ? 0 : 1),
    })),

  addAssistantQuery: (query) =>
    set((state) => ({
      assistantQueries: [...state.assistantQueries, query],
    })),

  resolveAssistantResponse: (res) =>
    set((state) => {
      const nextQueries = state.assistantQueries.map((q) =>
        q.query_id === res.query_id
          ? {
              ...q,
              answer: res.answer,
              citations: res.citations,
              action_items: res.action_items,
              is_loading: false,
            }
          : q
      );

      // Merge newly extracted action items into global list
      const newItems = res.action_items.filter(
        (item) => !state.meetingActionItems.includes(item)
      );

      return {
        assistantQueries: nextQueries,
        meetingActionItems: [...state.meetingActionItems, ...newItems],
        unreadAssistantCount:
          state.activePanel === "assistant"
            ? 0
            : state.unreadAssistantCount + 1,
      };
    }),

  setActivePanel: (activePanel) =>
    set((state) => ({
      activePanel,
      unreadChatCount: activePanel === "chat" ? 0 : state.unreadChatCount,
      unreadAssistantCount:
        activePanel === "assistant" ? 0 : state.unreadAssistantCount,
    })),

  setListeningLanguage: (listeningLanguage) => set({ listeningLanguage }),
  setSpokenLanguage: (spokenLanguage) => set({ spokenLanguage }),

  reset: () => set(initialState),
}));
