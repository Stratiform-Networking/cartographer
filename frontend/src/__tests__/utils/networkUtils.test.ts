/**
 * Tests for utils/networkUtils.ts
 */

import { describe, it, expect } from 'vitest';
import {
  parseIpAddress,
  compareIpAddresses,
  compareNodesByIp,
  isValidIpv4,
  getSubnet,
} from '../../utils/networkUtils';

describe('networkUtils', () => {
  describe('parseIpAddress', () => {
    it('parses a valid IP address', () => {
      expect(parseIpAddress('192.168.1.100')).toEqual([192, 168, 1, 100]);
    });

    it('parses IP with single digit octets', () => {
      expect(parseIpAddress('10.0.0.1')).toEqual([10, 0, 0, 1]);
    });

    it('parses IP with max values', () => {
      expect(parseIpAddress('255.255.255.255')).toEqual([255, 255, 255, 255]);
    });

    it('returns [0,0,0,0] for invalid IP', () => {
      expect(parseIpAddress('invalid')).toEqual([0, 0, 0, 0]);
      expect(parseIpAddress('192.168.1')).toEqual([0, 0, 0, 0]);
      expect(parseIpAddress('')).toEqual([0, 0, 0, 0]);
    });

    it('extracts IP from string with extra text', () => {
      expect(parseIpAddress('IP: 192.168.1.1 is active')).toEqual([192, 168, 1, 1]);
    });
  });

  describe('compareIpAddresses', () => {
    it('returns 0 for equal IPs', () => {
      expect(compareIpAddresses('192.168.1.1', '192.168.1.1')).toBe(0);
    });

    it('compares first octet correctly', () => {
      expect(compareIpAddresses('10.0.0.1', '192.0.0.1')).toBeLessThan(0);
      expect(compareIpAddresses('192.0.0.1', '10.0.0.1')).toBeGreaterThan(0);
    });

    it('compares second octet correctly', () => {
      expect(compareIpAddresses('192.100.0.1', '192.200.0.1')).toBeLessThan(0);
    });

    it('compares third octet correctly', () => {
      expect(compareIpAddresses('192.168.1.1', '192.168.2.1')).toBeLessThan(0);
    });

    it('compares fourth octet correctly', () => {
      expect(compareIpAddresses('192.168.1.1', '192.168.1.2')).toBeLessThan(0);
      expect(compareIpAddresses('192.168.1.10', '192.168.1.2')).toBeGreaterThan(0);
    });

    it('handles numeric sorting (not string sorting)', () => {
      // String sort: "192.168.1.2" > "192.168.1.10"
      // Numeric sort: 192.168.1.2 < 192.168.1.10
      expect(compareIpAddresses('192.168.1.2', '192.168.1.10')).toBeLessThan(0);
    });
  });

  describe('compareNodesByIp', () => {
    it('compares nodes by IP when available', () => {
      const a = { id: 'node-a', ip: '192.168.1.1' };
      const b = { id: 'node-b', ip: '192.168.1.2' };
      expect(compareNodesByIp(a, b)).toBeLessThan(0);
    });

    it('falls back to id when IP not available', () => {
      const a = { id: '192.168.1.1' };
      const b = { id: '192.168.1.2' };
      expect(compareNodesByIp(a, b)).toBeLessThan(0);
    });

    it('handles mixed ip/id comparison', () => {
      const a = { id: 'node-a', ip: '192.168.1.10' };
      const b = { id: '192.168.1.2' };
      expect(compareNodesByIp(a, b)).toBeGreaterThan(0);
    });

    it('can be used with Array.sort()', () => {
      const nodes = [
        { id: 'c', ip: '192.168.1.10' },
        { id: 'a', ip: '192.168.1.1' },
        { id: 'b', ip: '192.168.1.2' },
      ];
      const sorted = [...nodes].sort(compareNodesByIp);
      expect(sorted.map((n) => n.id)).toEqual(['a', 'b', 'c']);
    });
  });

  describe('isValidIpv4', () => {
    it('returns true for valid IP addresses', () => {
      expect(isValidIpv4('192.168.1.1')).toBe(true);
      expect(isValidIpv4('10.0.0.1')).toBe(true);
      expect(isValidIpv4('255.255.255.255')).toBe(true);
      expect(isValidIpv4('0.0.0.0')).toBe(true);
    });

    it('returns false for invalid IP addresses', () => {
      expect(isValidIpv4('192.168.1')).toBe(false); // Missing octet
      expect(isValidIpv4('192.168.1.256')).toBe(false); // Out of range
      expect(isValidIpv4('192.168.1.-1')).toBe(false); // Negative
      expect(isValidIpv4('192.168.1.1.1')).toBe(false); // Too many octets
      expect(isValidIpv4('abc.def.ghi.jkl')).toBe(false); // Not numbers
      expect(isValidIpv4('')).toBe(false); // Empty
    });

    it('returns false for leading zeros (strict validation)', () => {
      expect(isValidIpv4('192.168.001.001')).toBe(false);
      expect(isValidIpv4('192.168.01.1')).toBe(false);
    });
  });

  describe('getSubnet', () => {
    it('returns first 3 octets for valid IP', () => {
      expect(getSubnet('192.168.1.100')).toBe('192.168.1');
      expect(getSubnet('10.0.0.1')).toBe('10.0.0');
    });

    it('returns empty string for invalid IP', () => {
      expect(getSubnet('invalid')).toBe('');
      expect(getSubnet('')).toBe('');
    });
  });
});
