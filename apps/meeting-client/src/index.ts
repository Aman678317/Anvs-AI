import {
  MeetingStatus,
  ParticipantContract,
  ParticipantRole,
  WSClientFrame,
  WSServerFrame,
} from "@multilingual/contracts";

export const CLIENT_VERSION = "1.0.0";

export interface MeetingClientConfig {
  serverUrl: string;
  token: string;
}

export class MeetingClient {
  private config: MeetingClientConfig;
  private state: MeetingStatus = MeetingStatus.SCHEDULED;
  private participants: Map<string, ParticipantContract> = new Map();

  constructor(config: MeetingClientConfig) {
    this.config = config;
  }

  public getConfig(): MeetingClientConfig {
    return this.config;
  }

  public getStatus(): MeetingStatus {
    return this.state;
  }

  public getParticipants(): ParticipantContract[] {
    return Array.from(this.participants.values());
  }
}

export { ParticipantRole, MeetingStatus };
export type { WSClientFrame, WSServerFrame };
