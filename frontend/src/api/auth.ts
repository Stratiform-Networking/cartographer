/**
 * Auth API module
 *
 * All authentication and user management API calls.
 */

import client from './client';
import type {
  User,
  SetupStatus,
  LoginRequest,
  LoginResponse,
  OwnerSetupRequest,
  UserCreateRequest,
  UserUpdateRequest,
  SessionInfo,
  ChangePasswordRequest,
  PasswordResetRequest,
  PasswordResetConfirmRequest,
  Invite,
  InviteCreateRequest,
  InviteTokenInfo,
  AcceptInviteRequest,
  AuthConfig,
} from '../types/auth';

// ==================== Setup & Session ====================

export async function checkSetupStatus(): Promise<SetupStatus> {
  const response = await client.get<SetupStatus>('/api/auth/setup/status');
  return response.data;
}

export async function getAuthConfig(): Promise<AuthConfig> {
  const response = await client.get<AuthConfig>('/api/auth/config');
  return response.data;
}

export async function setupOwner(request: OwnerSetupRequest): Promise<User> {
  const response = await client.post<User>('/api/auth/setup/owner', request);
  return response.data;
}

export async function login(request: LoginRequest): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>('/api/auth/login', request);
  return response.data;
}

export async function logout(): Promise<void> {
  await client.post('/api/auth/logout');
}

export async function verifySession(): Promise<{ valid: boolean }> {
  const response = await client.post<{ valid: boolean }>('/api/auth/verify');
  return response.data;
}

export async function exchangeClerkToken(clerkToken: string): Promise<LoginResponse> {
  const response = await client.post<LoginResponse>('/api/auth/clerk/exchange', null, {
    headers: {
      Authorization: `Bearer ${clerkToken}`,
    },
  });
  return response.data;
}

export async function getSessionInfo(): Promise<SessionInfo> {
  const response = await client.get<SessionInfo>('/api/auth/session');
  return response.data;
}

// ==================== User Management ====================

export async function listUsers(): Promise<User[]> {
  const response = await client.get<User[]>('/api/auth/users');
  return response.data;
}

export async function createUser(request: UserCreateRequest): Promise<User> {
  const response = await client.post<User>('/api/auth/users', request);
  return response.data;
}

export async function updateUser(userId: string, request: UserUpdateRequest): Promise<User> {
  const response = await client.patch<User>(`/api/auth/users/${userId}`, request);
  return response.data;
}

export async function deleteUser(userId: string): Promise<void> {
  await client.delete(`/api/auth/users/${userId}`);
}

export async function changePassword(request: ChangePasswordRequest): Promise<void> {
  await client.post('/api/auth/me/change-password', request);
}

export async function requestPasswordReset(request: PasswordResetRequest): Promise<void> {
  await client.post('/api/auth/password-reset/request', request);
}

export async function confirmPasswordReset(request: PasswordResetConfirmRequest): Promise<void> {
  await client.post('/api/auth/password-reset/confirm', request);
}

// ==================== Invitation Management ====================

export async function listInvites(): Promise<Invite[]> {
  const response = await client.get<Invite[]>('/api/auth/invites');
  return response.data;
}

export async function createInvite(request: InviteCreateRequest): Promise<Invite> {
  const response = await client.post<Invite>('/api/auth/invites', request);
  return response.data;
}

export async function revokeInvite(inviteId: string): Promise<void> {
  await client.delete(`/api/auth/invites/${inviteId}`);
}

export async function resendInvite(inviteId: string): Promise<void> {
  await client.post(`/api/auth/invites/${inviteId}/resend`);
}

export async function verifyInviteToken(token: string): Promise<InviteTokenInfo> {
  const response = await client.get<InviteTokenInfo>(`/api/auth/invite/verify/${token}`);
  return response.data;
}

export async function acceptInvite(request: AcceptInviteRequest): Promise<User> {
  const response = await client.post<User>('/api/auth/invite/accept', request);
  return response.data;
}

// ==================== User Preferences ====================

export interface UserPreferences {
  dark_mode?: boolean;
}

export async function getPreferences(): Promise<UserPreferences> {
  const response = await client.get<UserPreferences>('/api/auth/me/preferences');
  return response.data;
}

export async function updatePreferences(
  preferences: Partial<UserPreferences>
): Promise<UserPreferences> {
  const response = await client.patch<UserPreferences>('/api/auth/me/preferences', preferences);
  return response.data;
}
