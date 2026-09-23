"use client";

import { useEffect, useRef, useCallback } from "react";
import {
  WSClientMessageType,
  WSServerMessageType,
  WSClientJoinFrame,
  WSClientPingFrame,
  WSClientSetLanguageFrame,
  WSClientChatMessageFrame,
  WSClientQueryAssistantFrame,
  WSServerFrame,
  ParticipantRole,
} from "@multilingual/contracts";
import { useMeetingStore } from "../stores/useMeetingStore";
import { CaptionSegment } from "../types/meeting";

const PING_INTERVAL_MS = 15000;
const RECONNECT_DELAY_MS = 3000;

export function useRealtimeGateway(
  meetingId: string | null,
  participantId: string | null,
  ticket: string | null,
  wsBaseUrl: string = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8001",
) {
  const wsRef = useRef<WebSocket | null>(null);
  const bcRef = useRef<BroadcastChannel | null>(null);
  const pingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isConnectingRef = useRef(false);

  const {
    displayName,
    role,
    spokenLanguage,
    listeningLanguage,
    isMicMuted,
    isVideoEnabled,
    setWsConnected,
    setWsLatencyMs,
    setMeetingInfo,
    setParticipants,
    upsertParticipant,
    removeParticipant,
    upsertCaption,
    addAvailableTrack,
    addChatMessage,
    resolveAssistantResponse,
  } = useMeetingStore();

  const sendFrame = useCallback((frame: unknown) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(frame));
    }
  }, []);

  const sendChatMessage = useCallback(
    (text: string) => {
      const frame: WSClientChatMessageFrame = {
        type: WSClientMessageType.CHAT_MESSAGE,
        text,
      };
      sendFrame(frame);

      // Broadcast chat message over cross-tab channel for peer synchronization
      if (bcRef.current) {
        bcRef.current.postMessage({
          type: "PEER_CHAT",
          message: {
            id: `msg_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
            sender_id: participantId || "me",
            sender_name: displayName || "Attendee",
            text,
            timestamp_ms: Date.now(),
            is_self: false,
          },
        });
      }

      // Optimistically add own message
      addChatMessage({
        id: `local_msg_${Date.now()}`,
        sender_id: participantId || "me",
        sender_name: "You",
        text,
        timestamp_ms: Date.now(),
        is_self: true,
      });
    },
    [participantId, displayName, sendFrame, addChatMessage],
  );

  const queryAssistant = useCallback(
    (question: string): string => {
      const queryId = `query_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
      const frame: WSClientQueryAssistantFrame = {
        type: WSClientMessageType.QUERY_ASSISTANT,
        query_id: queryId,
        question,
      };
      sendFrame(frame);
      return queryId;
    },
    [sendFrame],
  );

  const updateListeningLanguage = useCallback(
    (lang: string) => {
      const frame: WSClientSetLanguageFrame = {
        type: WSClientMessageType.SET_LISTENING_LANGUAGE,
        listening_language: lang,
      };
      sendFrame(frame);
    },
    [sendFrame],
  );

  useEffect(() => {
    if (!meetingId || !participantId || !ticket) {
      return;
    }

    let isMounted = true;

    const connect = () => {
      if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) {
        return;
      }

      const effectiveBaseUrl =
        typeof window !== "undefined" && window.location.hostname === "127.0.0.1"
          ? wsBaseUrl.replace("localhost", "127.0.0.1")
          : wsBaseUrl;
      const url = `${effectiveBaseUrl}/ws/meetings/${meetingId}?ticket=${encodeURIComponent(
        ticket,
      )}&participant_id=${encodeURIComponent(participantId)}`;

      try {
        const socket = new WebSocket(url);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          isConnectingRef.current = false;
          setWsConnected(true);

          // 1. Send immediate JOIN frame
          const joinFrame: WSClientJoinFrame = {
            type: WSClientMessageType.JOIN,
            ticket,
            participant_id: participantId,
          };
          socket.send(JSON.stringify(joinFrame));

          // 2. Setup periodic heartbeat PING
          if (pingTimerRef.current) clearInterval(pingTimerRef.current);
          pingTimerRef.current = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              const pingFrame: WSClientPingFrame = {
                type: WSClientMessageType.PING,
                timestamp_ms: Date.now(),
              };
              socket.send(JSON.stringify(pingFrame));
            }
          }, PING_INTERVAL_MS);
        };

        socket.onmessage = (event: MessageEvent) => {
          if (!isMounted) return;
          try {
            const frame: WSServerFrame = JSON.parse(event.data);

            switch (frame.type) {
              case WSServerMessageType.ROOM_STATE:
                setMeetingInfo({
                  meetingId,
                  title: "Live Meeting Room",
                  tenantId: "",
                  status: frame.status,
                  stateVersion: frame.state_version,
                });
                setParticipants(
                  frame.participants.map((p) => ({
                    participant_id: p.participant_id,
                    display_name: p.display_name,
                    role: p.role,
                    spoken_language: p.spoken_language,
                    listening_language: p.listening_language,
                    is_muted: p.is_muted,
                    is_video_enabled: p.is_video_enabled,
                    is_speaking: false,
                    audio_level: 0,
                  })),
                );
                break;

              case WSServerMessageType.PARTICIPANT_JOINED:
                upsertParticipant({
                  participant_id: frame.participant.participant_id,
                  display_name: frame.participant.display_name,
                  role: frame.participant.role,
                  spoken_language: frame.participant.spoken_language,
                  listening_language: frame.participant.listening_language,
                  is_muted: frame.participant.is_muted,
                  is_video_enabled: frame.participant.is_video_enabled,
                  is_speaking: false,
                  audio_level: 0,
                });
                break;

              case WSServerMessageType.PARTICIPANT_LEFT:
                removeParticipant(frame.participant_id);
                break;

              case WSServerMessageType.CAPTION_UPDATE: {
                const seg: CaptionSegment = {
                  id: frame.source_segment_id,
                  source_segment_id: frame.source_segment_id,
                  speaker_id: frame.speaker_id,
                  speaker_name: frame.speaker_id.replace(/^user_/, ""),
                  source_language: frame.source_language,
                  target_language: frame.target_language,
                  original_text: frame.text,
                  translated_text: frame.text,
                  is_final: frame.is_final,
                  start_ms: frame.start_ms,
                  end_ms: frame.end_ms,
                  timestamp_ms: Date.now(),
                };
                upsertCaption(seg);
                break;
              }

              case WSServerMessageType.AUDIO_TRACK_PUBLISHED:
                addAvailableTrack({
                  track_sid: frame.track_sid,
                  language: frame.language,
                  stream_type: frame.stream_type,
                });
                break;

              case WSServerMessageType.ASSISTANT_RESPONSE:
                resolveAssistantResponse({
                  query_id: frame.query_id,
                  answer: frame.answer,
                  citations: frame.citations,
                  action_items: frame.action_items,
                });
                break;

              case WSServerMessageType.PONG:
                setWsLatencyMs(Math.max(1, Date.now() - frame.timestamp_ms));
                break;

              default:
                break;
            }
          } catch (err) {
            console.error("Failed to parse realtime gateway frame", err);
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          isConnectingRef.current = false;
          setWsConnected(false);
          if (pingTimerRef.current) clearInterval(pingTimerRef.current);

          // Attempt reconnection
          if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
        };

        socket.onerror = (err) => {
          console.warn("Realtime WebSocket error:", err);
          socket.close();
        };
      } catch (err) {
        console.error("Error creating WebSocket:", err);
        isConnectingRef.current = false;
      }
    };

    // Initialize cross-tab broadcast channel for instant peer sync
    let bc: BroadcastChannel | null = null;
    if (typeof BroadcastChannel !== "undefined" && meetingId) {
      bc = new BroadcastChannel(`meet_gateway_${meetingId}`);
      bcRef.current = bc;

      bc.onmessage = (event) => {
        if (!isMounted) return;
        const data = event.data;
        if (!data) return;

        if (data.type === "PEER_JOINED" && data.participant) {
          if (data.participant.participant_id !== participantId) {
            upsertParticipant(data.participant);
            bc?.postMessage({
              type: "PEER_SYNC",
              participant: {
                participant_id: participantId,
                display_name: displayName || "Host",
                role: role || ParticipantRole.HOST,
                spoken_language: spokenLanguage || "eng",
                listening_language: listeningLanguage || "eng",
                is_muted: isMicMuted,
                is_video_enabled: isVideoEnabled,
                is_speaking: false,
                audio_level: 0,
              },
            });
          }
        } else if (data.type === "PEER_SYNC" && data.participant) {
          if (data.participant.participant_id !== participantId) {
            upsertParticipant(data.participant);
          }
        } else if (data.type === "PEER_STATUS_UPDATE" && data.participant_id) {
          if (data.participant_id !== participantId) {
            upsertParticipant({
              participant_id: data.participant_id,
              is_video_enabled: data.is_video_enabled,
              is_muted: data.is_muted,
            } as any);
          }
        } else if (data.type === "PEER_CHAT" && data.message) {
          if (data.message.sender_id !== participantId) {
            addChatMessage(data.message);
          }
        } else if (data.type === "PEER_CAPTION" && data.caption) {
          upsertCaption(data.caption);
        } else if (data.type === "PEER_LEFT" && data.participant_id) {
          removeParticipant(data.participant_id);
        }
      };

      // Announce self to peers
      bc.postMessage({
        type: "PEER_JOINED",
        participant: {
          participant_id: participantId,
          display_name: displayName || "Attendee",
          role: role || ParticipantRole.PARTICIPANT,
          spoken_language: spokenLanguage || "eng",
          listening_language: listeningLanguage || "eng",
          is_muted: isMicMuted,
          is_video_enabled: isVideoEnabled,
          is_speaking: false,
          audio_level: 0,
        },
      });

      // Periodic presence sync heartbeat so all tabs stay 100% updated
      const syncInterval = setInterval(() => {
        if (!isMounted || !bc) return;
        bc.postMessage({
          type: "PEER_SYNC",
          participant: {
            participant_id: participantId,
            display_name: displayName || "Attendee",
            role: role || ParticipantRole.PARTICIPANT,
            spoken_language: spokenLanguage || "eng",
            listening_language: listeningLanguage || "eng",
            is_muted: isMicMuted,
            is_video_enabled: isVideoEnabled,
            is_speaking: false,
            audio_level: 0,
          },
        });
      }, 4000);

      const origCleanup = () => {
        clearInterval(syncInterval);
      };
      (bc as any)._origCleanup = origCleanup;
    }

    connect();

    return () => {
      isMounted = false;
      if (pingTimerRef.current) clearInterval(pingTimerRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (bc) {
        try {
          if ((bc as any)._origCleanup) (bc as any)._origCleanup();
          bc.postMessage({
            type: "PEER_LEFT",
            participant_id: participantId,
          });
          bc.close();
          bcRef.current = null;
        } catch {}
      }
    };
  }, [
    meetingId,
    participantId,
    ticket,
    wsBaseUrl,
    setWsConnected,
    setMeetingInfo,
    setParticipants,
    upsertParticipant,
    removeParticipant,
    upsertCaption,
    addAvailableTrack,
    resolveAssistantResponse,
    setWsLatencyMs,
  ]);

  // Sync local mic & video state changes to all peers in the room
  useEffect(() => {
    if (bcRef.current && participantId) {
      bcRef.current.postMessage({
        type: "PEER_STATUS_UPDATE",
        participant_id: participantId,
        is_video_enabled: isVideoEnabled,
        is_muted: isMicMuted,
      });
    }
  }, [isVideoEnabled, isMicMuted, participantId]);

  // Live Speech Recognition & Subtitles synchronization
  useEffect(() => {
    if (typeof window === "undefined" || isMicMuted || !participantId) return;

    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) return;

    let recognition: any = null;
    let isRunning = true;

    try {
      recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang =
        spokenLanguage === "hin" ? "hi-IN" : spokenLanguage === "spa" ? "es-ES" : "en-US";

      recognition.onresult = (event: any) => {
        if (!isRunning) return;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const res = event.results[i];
          const text = res[0]?.transcript?.trim();
          if (!text) continue;

          const seg: CaptionSegment = {
            id: `cap_${participantId}_${Date.now()}`,
            source_segment_id: `seg_${participantId}`,
            speaker_id: participantId,
            speaker_name: displayName || "Guest",
            source_language: spokenLanguage || "eng",
            target_language: listeningLanguage || "eng",
            original_text: text,
            translated_text: text,
            is_final: res.isFinal,
            start_ms: Date.now() - 1000,
            end_ms: Date.now(),
            timestamp_ms: Date.now(),
          };

          upsertCaption(seg);

          if (bcRef.current) {
            bcRef.current.postMessage({
              type: "PEER_CAPTION",
              caption: seg,
            });
          }
        }
      };

      recognition.onerror = (e: any) => {
        if (e.error !== "no-speech" && e.error !== "aborted") {
          console.warn("Speech recognition notice:", e.error);
        }
      };

      recognition.onend = () => {
        if (isRunning && !isMicMuted) {
          try {
            recognition.start();
          } catch {}
        }
      };

      recognition.start();
    } catch (e) {
      console.warn("Speech recognition setup note:", e);
    }

    return () => {
      isRunning = false;
      if (recognition) {
        try {
          recognition.abort();
        } catch {}
      }
    };
  }, [isMicMuted, participantId, displayName, spokenLanguage, listeningLanguage, upsertCaption]);

  return {
    sendChatMessage,
    queryAssistant,
    updateListeningLanguage,
    sendFrame,
  };
}
