/**
 * Auth composable
 *
 * Manages authentication state and orchestrates auth API calls.
 */

import { ref, computed, readonly } from 'vue';
import { setOnUnauthorized, extractErrorMessage } from '../api/client';
import * as authApi from '../api/auth';
import type {
  User,
  SetupStatus,
  LoginRequest,
  OwnerSetupRequest,
  UserCreateRequest,
  UserUpdateRequest,
  ChangePasswordRequest,
  AuthState,
  Invite,
  InviteCreateRequest,
  InviteTokenInfo,
  AcceptInviteRequest,
} from '../types/auth';

const AUTH_STORAGE_KEY = 'cartographer_auth';

// Reactive state
const user = ref<User | null>(null);
const token = ref<string | null>(null);
const permissions = ref<string[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);
const setupStatus = ref<SetupStatus | null>(null);

// Computed properties
const isAuthenticated = computed(() => !!token.value && !!user.value);
const isOwner = computed(() => user.value?.role === 'owner');
const canWrite = computed(() => user.value?.role === 'owner' || user.value?.role === 'admin');
const isReadOnly = computed(() => user.value?.role === 'member');

// Clear auth state
function clearAuth(): void {
  token.value = null;
  user.value = null;
  permissions.value = [];
  localStorage.removeItem(AUTH_STORAGE_KEY);
}

// Set up the unauthorized callback
setOnUnauthorized(() => {
  if (token.value) {
    console.warn('[Auth] Session invalidated, clearing');
    clearAuth();
  }
});

// Save to localStorage
function saveToStorage(authToken: string, authUser: User, expiresIn: number): void {
  const state: AuthState = {
    token: authToken,
    user: authUser,
    expiresAt: Date.now() + expiresIn * 1000,
  };
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(state));
}

// Initialize from localStorage
function initFromStorage(): void {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const state: AuthState = JSON.parse(stored);

      // Check if token is expired
      if (state.expiresAt > Date.now()) {
        token.value = state.token;
        user.value = state.user;
        console.log('[Auth] Restored session for:', state.user.username);
      } else {
        console.log('[Auth] Stored session expired, clearing');
        clearAuth();
      }
    }
  } catch (e) {
    console.error('[Auth] Failed to restore session:', e);
    clearAuth();
  }
}

// ==================== Setup & Session ====================

async function checkSetupStatus(): Promise<SetupStatus> {
  try {
    const status = await authApi.checkSetupStatus();
    setupStatus.value = status;
    return status;
  } catch (e) {
    console.error('[Auth] Failed to check setup status:', e);
    throw new Error(extractErrorMessage(e));
  }
}

async function setupOwner(request: OwnerSetupRequest): Promise<User> {
  isLoading.value = true;
  error.value = null;

  try {
    const newUser = await authApi.setupOwner(request);
    console.log('[Auth] Owner account created:', newUser.username);
    return newUser;
  } catch (e) {
    const message = extractErrorMessage(e);
    error.value = message;
    throw new Error(message);
  } finally {
    isLoading.value = false;
  }
}

async function login(request: LoginRequest): Promise<User> {
  isLoading.value = true;
  error.value = null;

  try {
    const response = await authApi.login(request);
    const { access_token, expires_in, user: authUser } = response;

    // Update state
    token.value = access_token;
    user.value = authUser;

    // Save to storage
    saveToStorage(access_token, authUser, expires_in);

    console.log('[Auth] Login successful:', authUser.username);
    return authUser;
  } catch (e) {
    const message = extractErrorMessage(e);
    error.value = message;
    throw new Error(message);
  } finally {
    isLoading.value = false;
  }
}

async function logout(): Promise<void> {
  try {
    await authApi.logout();
  } catch (e) {
    console.warn('[Auth] Logout request failed:', e);
  } finally {
    clearAuth();
    console.log('[Auth] Logged out');
  }
}

async function verifySession(): Promise<boolean> {
  if (!token.value) {
    return false;
  }

  try {
    const response = await authApi.verifySession();
    if (!response.valid) {
      clearAuth();
      return false;
    }
    return true;
  } catch (e) {
    console.warn('[Auth] Session verification failed:', e);
    clearAuth();
    return false;
  }
}

async function refreshSession(): Promise<{ user: User; permissions: string[] } | null> {
  if (!token.value) {
    return null;
  }

  try {
    const sessionInfo = await authApi.getSessionInfo();
    user.value = sessionInfo.user;
    permissions.value = sessionInfo.permissions;
    return sessionInfo;
  } catch (e: unknown) {
    const axiosError = e as { response?: { status?: number } };
    if (axiosError.response?.status === 401) {
      clearAuth();
    }
    return null;
  }
}

// ==================== User Management ====================

async function listUsers(): Promise<User[]> {
  try {
    return await authApi.listUsers();
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function createUser(request: UserCreateRequest): Promise<User> {
  try {
    const newUser = await authApi.createUser(request);
    console.log('[Auth] User created:', newUser.username);
    return newUser;
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function updateUser(userId: string, request: UserUpdateRequest): Promise<User> {
  try {
    const updatedUser = await authApi.updateUser(userId, request);

    // Update local user if it's the current user
    if (user.value && user.value.id === userId) {
      user.value = updatedUser;
    }

    return updatedUser;
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function deleteUser(userId: string): Promise<void> {
  try {
    await authApi.deleteUser(userId);
    console.log('[Auth] User deleted:', userId);
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function changePassword(request: ChangePasswordRequest): Promise<void> {
  try {
    await authApi.changePassword(request);
    console.log('[Auth] Password changed');
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

// ==================== Invitation Management ====================

async function listInvites(): Promise<Invite[]> {
  try {
    return await authApi.listInvites();
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function createInvite(request: InviteCreateRequest): Promise<Invite> {
  try {
    const invite = await authApi.createInvite(request);
    console.log('[Auth] Invitation created for:', request.email);
    return invite;
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function revokeInvite(inviteId: string): Promise<void> {
  try {
    await authApi.revokeInvite(inviteId);
    console.log('[Auth] Invitation revoked:', inviteId);
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function resendInvite(inviteId: string): Promise<void> {
  try {
    await authApi.resendInvite(inviteId);
    console.log('[Auth] Invitation resent:', inviteId);
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function verifyInviteToken(inviteToken: string): Promise<InviteTokenInfo> {
  try {
    return await authApi.verifyInviteToken(inviteToken);
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

async function acceptInvite(request: AcceptInviteRequest): Promise<User> {
  try {
    const newUser = await authApi.acceptInvite(request);
    console.log('[Auth] Invitation accepted, user created:', newUser.username);
    return newUser;
  } catch (e) {
    throw new Error(extractErrorMessage(e));
  }
}

/**
 * Helper for common auth initialization pattern.
 * Checks setup status and verifies session if setup is complete.
 * Used by pages that need to check setup and verify session.
 */
export async function initAuthState(): Promise<{ needsSetup: boolean }> {
  try {
    const status = await checkSetupStatus();
    const requiresSetup = !status.is_setup_complete;

    if (status.is_setup_complete) {
      await verifySession();
    }

    return { needsSetup: requiresSetup };
  } catch (e) {
    console.error('[Auth] Failed to check setup status:', e);
    return { needsSetup: false };
  }
}

// Main composable export
export function useAuth() {
  // Initialize from storage on first use
  if (!token.value) {
    initFromStorage();
  }

  return {
    // State (readonly)
    user: readonly(user),
    token: readonly(token),
    permissions: readonly(permissions),
    isLoading: readonly(isLoading),
    error: readonly(error),
    setupStatus: readonly(setupStatus),

    // Computed
    isAuthenticated,
    isOwner,
    canWrite,
    isReadOnly,

    // Actions
    checkSetupStatus,
    setupOwner,
    login,
    logout,
    verifySession,
    refreshSession,
    initAuthState,

    // User management
    listUsers,
    createUser,
    updateUser,
    deleteUser,
    changePassword,

    // Invitation management
    listInvites,
    createInvite,
    revokeInvite,
    resendInvite,
    verifyInviteToken,
    acceptInvite,
  };
}
