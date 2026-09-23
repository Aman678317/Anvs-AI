import {
  AuthTokenResponse,
  CreateMeetingRequest,
  CreateMeetingResponse,
  GetMeetingResponse,
  JoinMeetingRequest,
  JoinMeetingResponse,
  LoginRequest,
  ParticipantRole,
  RegisterRequest,
  RegisterResponse,
} from "@multilingual/contracts";

export type CreateRoomRequest = CreateMeetingRequest;
export type CreateRoomResponse = CreateMeetingResponse;
export type JoinRoomRequest = JoinMeetingRequest;
export type JoinRoomResponse = JoinMeetingResponse;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  public status: number;
  public data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `API request failed with status ${response.status}`;
    let errorData = null;
    try {
      errorData = await response.json();
      if (errorData?.detail) {
        errorDetail = errorData.detail;
      }
    } catch {
      // Non-JSON response
    }
    throw new ApiError(response.status, errorDetail, errorData);
  }

  return response.json() as Promise<T>;
}

/**
 * Acquires a user/guest bearer token from the control plane API.
 */
export async function acquireUserToken(
  displayName: string = "Guest",
  role: ParticipantRole = ParticipantRole.PARTICIPANT,
  tenantId: string = "default",
): Promise<string> {
  const sanitizedName = displayName.toLowerCase().replace(/[^a-z0-9]/g, "");
  const userId = `usr_${sanitizedName || "guest"}_${Math.random().toString(36).substring(2, 8)}`;
  const email = `${userId}@meeting.local`;

  const res = await request<AuthTokenResponse>("/api/v1/auth/token", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      tenant_id: tenantId,
      email,
      role,
    }),
  });

  return res.access_token;
}

/**
 * Creates a new meeting room in PostgreSQL and provisions the LiveKit SFU room.
 */
export async function createRoom(
  payload: CreateMeetingRequest,
  token?: string | null,
): Promise<CreateMeetingResponse> {
  const authToken = token || (await acquireUserToken(payload.title, ParticipantRole.HOST));
  return request<CreateMeetingResponse>(
    "/api/v1/rooms/create",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    authToken,
  );
}

/**
 * Joins an existing meeting room and obtains dual server-signed tokens (LiveKit SFU + WebSocket).
 */
export async function joinRoom(
  meetingId: string,
  payload: JoinMeetingRequest,
  token?: string | null,
): Promise<JoinMeetingResponse> {
  const authToken =
    token || (await acquireUserToken(payload.display_name, ParticipantRole.PARTICIPANT));
  return request<JoinMeetingResponse>(
    `/api/v1/rooms/${meetingId}/join`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    authToken,
  );
}

/**
 * Fetches meeting room details, versioning, and active participant counts.
 */
export async function getRoom(
  meetingId: string,
  token?: string | null,
): Promise<GetMeetingResponse> {
  const authToken = token || (await acquireUserToken());
  return request<GetMeetingResponse>(`/api/v1/rooms/${meetingId}`, { method: "GET" }, authToken);
}

/**
 * Ends a meeting room (Host only).
 */
export async function endRoom(
  meetingId: string,
  token: string,
  reason: string = "Host ended meeting",
): Promise<void> {
  await request<void>(
    `/api/v1/rooms/${meetingId}/end`,
    {
      method: "POST",
      body: JSON.stringify({ reason }),
    },
    token,
  );
}

/**
 * Authenticates user credentials via email and password.
 */
export async function loginUser(payload: LoginRequest): Promise<AuthTokenResponse> {
  return request<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Registers a new organization tenant and administrator.
 */
export async function registerUser(payload: RegisterRequest): Promise<RegisterResponse> {
  return request<RegisterResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
