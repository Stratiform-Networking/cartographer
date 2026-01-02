/**
 * Tests for utils/authHelpers.ts
 */

import { describe, it, expect } from 'vitest';
import {
  getFullName,
  canWrite,
  canManageUsers,
  getRoleLabel,
  getRoleDescription,
  getInviteStatusLabel,
  getInviteStatusClass,
} from '../../utils/authHelpers';
import type { User, UserRole, InviteStatus } from '../../types/auth';

describe('authHelpers', () => {
  describe('getFullName', () => {
    it('returns full name from user object', () => {
      const user = {
        id: '1',
        username: 'johndoe',
        email: 'john@example.com',
        first_name: 'John',
        last_name: 'Doe',
        role: 'member' as UserRole,
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
      } satisfies User;
      expect(getFullName(user)).toBe('John Doe');
    });
  });

  describe('canWrite', () => {
    it('returns true for owner', () => {
      expect(canWrite('owner')).toBe(true);
    });

    it('returns true for admin', () => {
      expect(canWrite('admin')).toBe(true);
    });

    it('returns false for member', () => {
      expect(canWrite('member')).toBe(false);
    });
  });

  describe('canManageUsers', () => {
    it('returns true for owner', () => {
      expect(canManageUsers('owner')).toBe(true);
    });

    it('returns false for admin', () => {
      expect(canManageUsers('admin')).toBe(false);
    });

    it('returns false for member', () => {
      expect(canManageUsers('member')).toBe(false);
    });
  });

  describe('getRoleLabel', () => {
    it('returns correct labels for each role', () => {
      expect(getRoleLabel('owner')).toBe('Owner');
      expect(getRoleLabel('admin')).toBe('Admin');
      expect(getRoleLabel('member')).toBe('Member');
    });

    it('returns role string for unknown role', () => {
      expect(getRoleLabel('unknown' as UserRole)).toBe('unknown');
    });
  });

  describe('getRoleDescription', () => {
    it('returns description for owner', () => {
      expect(getRoleDescription('owner')).toContain('Full access');
    });

    it('returns description for admin', () => {
      expect(getRoleDescription('admin')).toContain('Admin');
    });

    it('returns description for member', () => {
      expect(getRoleDescription('member')).toContain('view');
    });

    it('returns empty string for unknown role', () => {
      expect(getRoleDescription('unknown' as UserRole)).toBe('');
    });
  });

  describe('getInviteStatusLabel', () => {
    it('returns correct labels for each status', () => {
      expect(getInviteStatusLabel('pending')).toBe('Pending');
      expect(getInviteStatusLabel('accepted')).toBe('Accepted');
      expect(getInviteStatusLabel('expired')).toBe('Expired');
      expect(getInviteStatusLabel('revoked')).toBe('Revoked');
    });

    it('returns status string for unknown status', () => {
      expect(getInviteStatusLabel('unknown' as InviteStatus)).toBe('unknown');
    });
  });

  describe('getInviteStatusClass', () => {
    it('returns amber classes for pending', () => {
      const classes = getInviteStatusClass('pending');
      expect(classes).toContain('amber');
    });

    it('returns green classes for accepted', () => {
      const classes = getInviteStatusClass('accepted');
      expect(classes).toContain('green');
    });

    it('returns slate classes for expired', () => {
      const classes = getInviteStatusClass('expired');
      expect(classes).toContain('slate');
    });

    it('returns red classes for revoked', () => {
      const classes = getInviteStatusClass('revoked');
      expect(classes).toContain('red');
    });

    it('returns default classes for unknown status', () => {
      const classes = getInviteStatusClass('unknown' as InviteStatus);
      expect(classes).toContain('slate');
    });
  });
});
