/**
 * Auth-related helper functions
 *
 * UI display helpers for auth types. Moved from types/auth.ts
 * to keep types pure (only type definitions, no runtime code).
 */

import type { User, UserRole, InviteStatus } from '../types/auth';

// ==================== User Helpers ====================

/**
 * Get the full name of a user.
 *
 * @param user - User object
 * @returns Full name string
 */
export function getFullName(user: User): string {
  return `${user.first_name} ${user.last_name}`;
}

// ==================== Role Helpers ====================

/**
 * Check if a role has write permissions.
 *
 * @param role - User role
 * @returns true if role can write
 */
export function canWrite(role: UserRole): boolean {
  return role === 'owner' || role === 'admin';
}

/**
 * Check if a role can manage users.
 *
 * @param role - User role
 * @returns true if role can manage users
 */
export function canManageUsers(role: UserRole): boolean {
  return role === 'owner';
}

/**
 * Get a human-readable label for a role.
 *
 * @param role - User role
 * @returns Display label
 */
export function getRoleLabel(role: UserRole): string {
  switch (role) {
    case 'owner':
      return 'Owner';
    case 'admin':
      return 'Admin';
    case 'member':
      return 'Member';
    default:
      return role;
  }
}

/**
 * Get a description of what a role can do.
 *
 * @param role - User role
 * @returns Description string
 */
export function getRoleDescription(role: UserRole): string {
  switch (role) {
    case 'owner':
      return 'Full access - can manage users and modify the network map';
    case 'admin':
      return 'Admin - Can view and modify the network map';
    case 'member':
      return 'Member - Can only view the network map';
    default:
      return '';
  }
}

// ==================== Invite Status Helpers ====================

/**
 * Get a human-readable label for an invite status.
 *
 * @param status - Invite status
 * @returns Display label
 */
export function getInviteStatusLabel(status: InviteStatus): string {
  switch (status) {
    case 'pending':
      return 'Pending';
    case 'accepted':
      return 'Accepted';
    case 'expired':
      return 'Expired';
    case 'revoked':
      return 'Revoked';
    default:
      return status;
  }
}

/**
 * Get Tailwind CSS classes for an invite status badge.
 *
 * @param status - Invite status
 * @returns CSS class string
 */
export function getInviteStatusClass(status: InviteStatus): string {
  switch (status) {
    case 'pending':
      return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400';
    case 'accepted':
      return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400';
    case 'expired':
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
    case 'revoked':
      return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400';
    default:
      return 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400';
  }
}
