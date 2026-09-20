export const CLIENT_VERSION = "1.0.0";

export interface MeetingClientConfig {
  serverUrl: string;
  token: string;
}

export class MeetingClient {
  private config: MeetingClientConfig;

  constructor(config: MeetingClientConfig) {
    this.config = config;
  }

  public getConfig(): MeetingClientConfig {
    return this.config;
  }
}
