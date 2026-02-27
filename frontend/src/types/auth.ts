/**
 * Auth types
 *
 * Type definitions for authentication and user management.
 * Helper functions have been moved to utils/authHelpers.ts.
 */

// ==================== User Types ====================

export type UserRole = 'owner' | 'admin' | 'member';

export interface User {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  avatar_url?: string | null;
  role: UserRole;
  created_at: string;
  updated_at: string;
  last_login?: string;
  is_active: boolean;
}

export interface OwnerSetupRequest {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
}

export interface UserCreateRequest {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface UserUpdateRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  role?: UserRole;
  password?: string;
}

// ==================== Auth Types ====================

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SetupStatus {
  is_setup_complete: boolean;
  owner_exists: boolean;
  total_users: number;
}

export interface SessionInfo {
  user: User;
  permissions: string[];
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetConfirmRequest {
  token: string;
  new_password: string;
}

export interface AuthState {
  token: string;
  user: User;
  expiresAt: number;
}

export type AuthProvider = 'local' | 'cloud';

export interface AuthConfig {
  provider: AuthProvider;
  clerk_publishable_key: string | null;
  clerk_proxy_url: string | null;
  allow_registration: boolean;
}

// ==================== Invitation Types ====================

export type InviteStatus = 'pending' | 'accepted' | 'expired' | 'revoked';

export interface Invite {
  id: string;
  email: string;
  role: UserRole;
  status: InviteStatus;
  invited_by: string;
  invited_by_name: string;
  created_at: string;
  expires_at: string;
  accepted_at?: string;
}

export interface InviteCreateRequest {
  email: string;
  role: UserRole;
}

export interface InviteTokenInfo {
  email: string;
  role: UserRole;
  invited_by_name: string;
  expires_at: string;
  is_valid: boolean;
}

export interface AcceptInviteRequest {
  token: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
}

// ==================== Re-exports for backwards compatibility ====================
// Helper functions moved to utils/authHelpers.ts

export {
  getFullName,
  canWrite,
  canManageUsers,
  getRoleLabel,
  getRoleDescription,
  getInviteStatusLabel,
  getInviteStatusClass,
} from '../utils/authHelpers';
