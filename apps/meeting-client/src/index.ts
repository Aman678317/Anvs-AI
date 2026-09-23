import {
  AudioStreamType,
  MeetingStatus,
  ParticipantContract,
  ParticipantRole,
  WSClientChatMessageFrame,
  WSClientFrame,
  WSClientJoinFrame,
  WSClientMessageType,
  WSClientPingFrame,
  WSClientQueryAssistantFrame,
  WSClientSetLanguageFrame,
  WSServerAssistantFrame,
  WSServerAudioTrackFrame,
  WSServerCaptionFrame,
  WSServerErrorFrame,
  WSServerFrame,
  WSServerMessageType,
  WSServerParticipantJoinedFrame,
  WSServerParticipantLeftFrame,
  WSServerPongFrame,
  WSServerRoomStateFrame,
} from "@multilingual/contracts";
import { Room } from "livekit-client";

export const CLIENT_VERSION = "1.0.0";

export interface MeetingClientConfig {
  wsUrl?: string;
  meetingId?: string;
  participantId?: string;
  ticket?: string;
  livekitUrl?: string;
  livekitToken?: string;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelayMs?: number;
  pingIntervalMs?: number;
  WebSocketClass?: any;

  // Backward compatibility aliases
  serverUrl?: string;
  token?: string;
}

export interface ChatMessageEvent {
  sender_id: string;
  text: string;
  timestamp_ms: number;
}

export type MeetingEventMap = {
  connected: () => void;
  disconnected: (info: { code: number; reason: string }) => void;
  roomState: (frame: WSServerRoomStateFrame) => void;
  participantJoined: (frame: WSServerParticipantJoinedFrame) => void;
  participantLeft: (frame: WSServerParticipantLeftFrame) => void;
  caption: (frame: WSServerCaptionFrame) => void;
  audioTrack: (frame: WSServerAudioTrackFrame) => void;
  assistantResponse: (frame: WSServerAssistantFrame) => void;
  chatMessage: (msg: ChatMessageEvent) => void;
  pong: (latencyMs: number) => void;
  error: (err: WSServerErrorFrame | Error) => void;
};

export type MeetingEventListener<K extends keyof MeetingEventMap> = MeetingEventMap[K];

export class MeetingClient {
  private config: MeetingClientConfig;
  private ws: any = null;
  private livekitRoom: Room | null = null;
  private state: MeetingStatus = MeetingStatus.SCHEDULED;
  private stateVersion: number = 0;
  private participants: Map<string, ParticipantContract> = new Map();
  private listeners: Map<keyof MeetingEventMap, Set<Function>> = new Map();
  private pingTimer: any = null;
  private reconnectTimer: any = null;
  private reconnectAttempts: number = 0;
  private isExplicitDisconnect: boolean = false;
  private latencyMs: number = 0;

  constructor(config: MeetingClientConfig) {
    this.config = {
      wsUrl: config.wsUrl || config.serverUrl || "ws://localhost:8001",
      meetingId: config.meetingId || "default-meeting",
      participantId: config.participantId || `client_${Math.random().toString(36).substring(2, 8)}`,
      ticket: config.ticket || config.token || "",
      livekitUrl: config.livekitUrl || "ws://localhost:7880",
      livekitToken: config.livekitToken || "",
      autoReconnect: config.autoReconnect ?? true,
      maxReconnectAttempts: config.maxReconnectAttempts ?? 5,
      reconnectDelayMs: config.reconnectDelayMs ?? 3000,
      pingIntervalMs: config.pingIntervalMs ?? 15000,
      WebSocketClass: config.WebSocketClass,
      ...config,
    };
  }

  public getConfig(): MeetingClientConfig {
    return { ...this.config };
  }

  public getStatus(): MeetingStatus {
    return this.state;
  }

  public getStateVersion(): number {
    return this.stateVersion;
  }

  public getLatencyMs(): number {
    return this.latencyMs;
  }

  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === 1; // 1 = OPEN
  }

  public getParticipants(): ParticipantContract[] {
    return Array.from(this.participants.values());
  }

  public getParticipant(participantId: string): ParticipantContract | undefined {
    return this.participants.get(participantId);
  }

  public getLiveKitRoom(): Room | null {
    return this.livekitRoom;
  }

  // --- Event Emitter ---

  public on<K extends keyof MeetingEventMap>(event: K, listener: MeetingEventMap[K]): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(listener);

    return () => {
      this.off(event, listener);
    };
  }

  public off<K extends keyof MeetingEventMap>(event: K, listener: MeetingEventMap[K]): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      eventListeners.delete(listener);
    }
  }

  public once<K extends keyof MeetingEventMap>(event: K, listener: MeetingEventMap[K]): void {
    const wrapped = ((...args: any[]) => {
      this.off(event, wrapped as any);
      (listener as any)(...args);
    }) as any;
    this.on(event, wrapped);
  }

  private emit<K extends keyof MeetingEventMap>(
    event: K,
    ...args: Parameters<MeetingEventMap[K]>
  ): void {
    const eventListeners = this.listeners.get(event);
    if (eventListeners) {
      for (const listener of eventListeners) {
        try {
          (listener as any)(...args);
        } catch (err) {
          console.error(`Error in MeetingClient '${event}' listener:`, err);
        }
      }
    }
  }

  // --- WebSocket Connection Handshake ---

  public async connect(): Promise<void> {
    this.isExplicitDisconnect = false;

    const WS =
      this.config.WebSocketClass ||
      (typeof WebSocket !== "undefined"
        ? WebSocket
        : typeof global !== "undefined" && (global as any).WebSocket
        ? (global as any).WebSocket
        : null);

    if (!WS) {
      throw new Error(
        "WebSocket implementation not found. Please provide WebSocketClass in MeetingClientConfig.",
      );
    }

    const { wsUrl, meetingId, participantId, ticket } = this.config;
    const url = `${wsUrl}/ws/meetings/${meetingId}?ticket=${encodeURIComponent(
      ticket || "",
    )}&participant_id=${encodeURIComponent(participantId || "")}`;

    return new Promise((resolve, reject) => {
      let isOpened = false;

      try {
        const socket = new WS(url);
        this.ws = socket;

        socket.onopen = () => {
          isOpened = true;
          this.reconnectAttempts = 0;

          // 1. Send immediate JOIN frame handshake
          const joinFrame: WSClientJoinFrame = {
            type: WSClientMessageType.JOIN,
            ticket: this.config.ticket || "",
            participant_id: this.config.participantId || "",
          };
          this.sendFrame(joinFrame);

          // 2. Start heartbeat loop
          this.startHeartbeat();

          this.emit("connected");
          resolve();
        };

        socket.onmessage = (event: any) => {
          this.handleIncomingMessage(event.data);
        };

        socket.onerror = (err: any) => {
          this.emit("error", err instanceof Error ? err : new Error(String(err)));
          if (!isOpened) {
            reject(err);
          }
        };

        socket.onclose = (event: any) => {
          this.stopHeartbeat();
          this.ws = null;
          const code = event?.code ?? 1000;
          const reason = event?.reason ?? "Connection closed";
          this.emit("disconnected", { code, reason });

          if (!this.isExplicitDisconnect && this.config.autoReconnect) {
            this.scheduleReconnect();
          }
        };
      } catch (err) {
        reject(err);
      }
    });
  }

  public disconnect(): void {
    this.isExplicitDisconnect = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      try {
        this.ws.close(1000, "Client disconnected");
      } catch {
        // ignore
      }
      this.ws = null;
    }

    if (this.livekitRoom) {
      try {
        this.livekitRoom.disconnect();
      } catch {
        // ignore
      }
      this.livekitRoom = null;
    }
  }

  // --- LiveKit WebRTC SFU Integration ---

  public async connectLiveKit(): Promise<Room | null> {
    if (!this.config.livekitToken) {
      return null;
    }
    const url = this.config.livekitUrl || "ws://localhost:7880";
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
    });

    await room.connect(url, this.config.livekitToken);
    this.livekitRoom = room;
    return room;
  }

  // --- Actions ---

  public sendFrame(frame: WSClientFrame): void {
    if (!this.isConnected()) {
      throw new Error("Cannot send frame: WebSocket is not connected.");
    }
    this.ws.send(JSON.stringify(frame));
  }

  public sendChatMessage(text: string): void {
    const frame: WSClientChatMessageFrame = {
      type: WSClientMessageType.CHAT_MESSAGE,
      text,
    };
    this.sendFrame(frame);
  }

  public queryAssistant(question: string): string {
    const queryId = `query_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;
    const frame: WSClientQueryAssistantFrame = {
      type: WSClientMessageType.QUERY_ASSISTANT,
      query_id: queryId,
      question,
    };
    this.sendFrame(frame);
    return queryId;
  }

  public setListeningLanguage(language: string): void {
    const frame: WSClientSetLanguageFrame = {
      type: WSClientMessageType.SET_LISTENING_LANGUAGE,
      listening_language: language,
    };
    this.sendFrame(frame);
  }

  // --- Internal Message Dispatcher ---

  private handleIncomingMessage(rawData: string | any): void {
    try {
      const dataStr = typeof rawData === "string" ? rawData : rawData.toString();
      const frame: WSServerFrame = JSON.parse(dataStr);

      switch (frame.type) {
        case WSServerMessageType.ROOM_STATE:
          this.state = frame.status;
          this.stateVersion = frame.state_version;
          this.participants.clear();
          for (const p of frame.participants) {
            this.participants.set(p.participant_id, p);
          }
          this.emit("roomState", frame);
          break;

        case WSServerMessageType.PARTICIPANT_JOINED:
          this.stateVersion = frame.state_version;
          this.participants.set(frame.participant.participant_id, frame.participant);
          this.emit("participantJoined", frame);
          break;

        case WSServerMessageType.PARTICIPANT_LEFT:
          this.stateVersion = frame.state_version;
          this.participants.delete(frame.participant_id);
          this.emit("participantLeft", frame);
          break;

        case WSServerMessageType.CAPTION_UPDATE:
          this.emit("caption", frame);
          break;

        case WSServerMessageType.AUDIO_TRACK_PUBLISHED:
          this.emit("audioTrack", frame);
          break;

        case WSServerMessageType.ASSISTANT_RESPONSE:
          this.emit("assistantResponse", frame);
          break;

        case WSServerMessageType.PONG:
          this.latencyMs = Math.max(0, Date.now() - frame.timestamp_ms);
          this.emit("pong", this.latencyMs);
          break;

        case WSServerMessageType.ERROR:
          this.emit("error", frame);
          break;
      }
    } catch (err) {
      console.error("Failed to parse incoming WebSocket message:", err, rawData);
    }
  }

  // --- Heartbeat & Reconnection Loops ---

  private startHeartbeat(): void {
    this.stopHeartbeat();
    const interval = this.config.pingIntervalMs || 15000;
    this.pingTimer = setInterval(() => {
      if (this.isConnected()) {
        const ping: WSClientPingFrame = {
          type: WSClientMessageType.PING,
          timestamp_ms: Date.now(),
        };
        try {
          this.ws.send(JSON.stringify(ping));
        } catch {
          // ignore socket send errors
        }
      }
    }, interval);
  }

  private stopHeartbeat(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    const maxAttempts = this.config.maxReconnectAttempts || 5;
    if (this.reconnectAttempts >= maxAttempts) {
      this.emit(
        "error",
        new Error(`Max reconnection attempts (${maxAttempts}) reached. Giving up.`),
      );
      return;
    }

    this.reconnectAttempts++;
    const delay = (this.config.reconnectDelayMs || 3000) * Math.pow(1.5, this.reconnectAttempts - 1);

    this.reconnectTimer = setTimeout(async () => {
      try {
        await this.connect();
      } catch {
        // next reconnect attempt handled by onclose
      }
    }, delay);
  }
}

export {
  AudioStreamType,
  MeetingStatus,
  ParticipantRole,
  WSClientMessageType,
  WSServerMessageType,
};
export type {
  ParticipantContract,
  WSClientFrame,
  WSClientJoinFrame,
  WSClientSetLanguageFrame,
  WSClientChatMessageFrame,
  WSClientQueryAssistantFrame,
  WSClientPingFrame,
  WSServerFrame,
  WSServerRoomStateFrame,
  WSServerParticipantJoinedFrame,
  WSServerParticipantLeftFrame,
  WSServerCaptionFrame,
  WSServerAudioTrackFrame,
  WSServerAssistantFrame,
  WSServerPongFrame,
  WSServerErrorFrame,
};
