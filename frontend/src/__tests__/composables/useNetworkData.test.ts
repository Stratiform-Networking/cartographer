/**
 * Tests for composables/useNetworkData.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useNetworkData } from '../../composables/useNetworkData';
import type { TreeNode } from '../../types/network';

describe('useNetworkData', () => {
  const {
    parseNetworkMap,
    initializeNodeVersion,
    updateNodeVersion,
    findNodeById,
    flattenDevices,
    walkAll,
    removeFromAllGroups,
    findGroupByPrefix,
    getTargetGroupForRole,
    getMonitoredDeviceIPs,
    getSilencedDeviceIPs,
  } = useNetworkData();

  // Use fixed dates for version tracking tests
  const NOW = new Date('2024-06-15T12:00:00Z');

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('parseNetworkMap', () => {
    it('parses gateway information', () => {
      const raw = `
=== NETWORK TOPOLOGY ===
Gateway: 192.168.1.1 (router.lan)
LAN Interface: eth0
Subnet: 192.168.1.0/24
`;

      const result = parseNetworkMap(raw);

      expect(result.raw).toBe(raw);
      expect(result.gateway?.ip).toBe('192.168.1.1');
      expect(result.gateway?.hostname).toBe('router.lan');
      expect(result.gateway?.lanInterface).toBe('eth0');
      expect(result.gateway?.subnet).toBe('192.168.1.0/24');
    });

    it('handles missing gateway section', () => {
      const raw = `Some random text without gateway`;
      const result = parseNetworkMap(raw);
      expect(result.gateway).toBeUndefined();
    });

    it('returns a root node', () => {
      const raw = `
=== NETWORK TOPOLOGY ===
Gateway: 192.168.1.1 (router.lan)
`;
      const result = parseNetworkMap(raw);
      expect(result.root).toBeDefined();
      expect(result.root.id).toBeDefined();
    });
  });

  describe('initializeNodeVersion', () => {
    it('initializes version tracking on a node', () => {
      const node: TreeNode = { id: '192.168.1.1', name: 'Test', role: 'server' };

      initializeNodeVersion(node, 'manual');

      expect(node.createdAt).toBe(NOW.toISOString());
      expect(node.updatedAt).toBe(NOW.toISOString());
      expect(node.version).toBe(1);
      expect(node.history).toHaveLength(1);
      expect(node.history![0].changes[0]).toContain('manual');
    });

    it('preserves existing createdAt', () => {
      const existingDate = '2024-01-01T00:00:00Z';
      const node: TreeNode = {
        id: '192.168.1.1',
        name: 'Test',
        role: 'server',
        createdAt: existingDate,
      };

      initializeNodeVersion(node, 'mapper');

      expect(node.createdAt).toBe(existingDate);
      expect(node.updatedAt).toBe(NOW.toISOString());
    });
  });

  describe('updateNodeVersion', () => {
    it('increments version and adds history', () => {
      const node: TreeNode = {
        id: '192.168.1.1',
        name: 'Test',
        role: 'server',
        version: 1,
        history: [],
      };

      updateNodeVersion(node, ['Changed name']);

      expect(node.version).toBe(2);
      expect(node.history).toHaveLength(1);
      expect(node.history![0].version).toBe(2);
      expect(node.history![0].changes).toEqual(['Changed name']);
    });

    it('limits history to 20 entries', () => {
      const node: TreeNode = {
        id: '192.168.1.1',
        name: 'Test',
        role: 'server',
        version: 25,
        history: Array.from({ length: 25 }, (_, i) => ({
          version: i + 1,
          timestamp: NOW.toISOString(),
          changes: [`Change ${i + 1}`],
        })),
      };

      updateNodeVersion(node, ['New change']);

      expect(node.history).toHaveLength(20);
      expect(node.history![19].version).toBe(26);
    });
  });

  describe('findNodeById', () => {
    const root: TreeNode = {
      id: 'root',
      name: 'Network',
      children: [
        {
          id: 'infra',
          name: 'Infrastructure',
          role: 'group',
          children: [{ id: '192.168.1.1', name: 'Router', role: 'gateway/router' }],
        },
        { id: '192.168.1.100', name: 'Server', role: 'server' },
      ],
    };

    it('finds node at root level', () => {
      const node = findNodeById(root, '192.168.1.100');
      expect(node?.name).toBe('Server');
    });

    it('finds node in nested group', () => {
      const node = findNodeById(root, '192.168.1.1');
      expect(node?.name).toBe('Router');
    });

    it('returns undefined for non-existent node', () => {
      const node = findNodeById(root, 'non-existent');
      expect(node).toBeUndefined();
    });

    it('finds the root itself', () => {
      const node = findNodeById(root, 'root');
      expect(node?.name).toBe('Network');
    });
  });

  describe('flattenDevices', () => {
    it('returns all non-group nodes including root if it has a role', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        role: 'group', // This makes root a group, so it won't be included
        children: [
          {
            id: 'infra',
            name: 'Infrastructure',
            role: 'group',
            children: [{ id: '192.168.1.1', name: 'Router', role: 'gateway/router' }],
          },
          { id: '192.168.1.100', name: 'Server', role: 'server' },
        ],
      };

      const devices = flattenDevices(root);
      expect(devices).toHaveLength(2);
      expect(devices.map((d) => d.id)).toContain('192.168.1.1');
      expect(devices.map((d) => d.id)).toContain('192.168.1.100');
    });

    it('excludes group nodes', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        role: 'group',
        children: [{ id: 'infra', name: 'Infrastructure', role: 'group', children: [] }],
      };

      const devices = flattenDevices(root);
      expect(devices.find((d) => d.id === 'infra')).toBeUndefined();
    });

    it('deduplicates by IP', () => {
      const root: TreeNode = {
        id: '192.168.1.1',
        name: 'Gateway',
        role: 'gateway/router',
        ip: '192.168.1.1',
        children: [
          {
            id: 'infra',
            name: 'Infrastructure',
            role: 'group',
            children: [
              {
                id: 'dup-192.168.1.1',
                name: 'Gateway Duplicate',
                role: 'gateway/router',
                ip: '192.168.1.1',
              },
            ],
          },
        ],
      };

      const devices = flattenDevices(root);
      // Should only have 1 device with IP 192.168.1.1
      expect(devices.filter((d) => d.ip === '192.168.1.1')).toHaveLength(1);
    });
  });

  describe('walkAll', () => {
    it('visits root and children of groups', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group',
            name: 'Group',
            role: 'group',
            children: [{ id: 'nested', name: 'Nested' }],
          },
        ],
      };

      const visited: string[] = [];
      walkAll(root, (node) => visited.push(node.id));

      // walkAll visits: root, then for each group, visits its children (not the group itself)
      expect(visited).toContain('root');
      expect(visited).toContain('nested');
    });
  });

  describe('getMonitoredDeviceIPs', () => {
    it('returns ALL device IPs for health service tracking', () => {
      // Note: getMonitoredDeviceIPs returns ALL devices with IPs
      // The ML anomaly detection needs all devices tracked
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        role: 'group',
        children: [
          { id: '1', name: 'A', ip: '192.168.1.1', role: 'server', monitoringEnabled: true },
          { id: '2', name: 'B', ip: '192.168.1.2', role: 'server', monitoringEnabled: false },
          { id: '3', name: 'C', ip: '192.168.1.3', role: 'server' },
        ],
      };

      const ips = getMonitoredDeviceIPs(root);

      // All devices with IPs are returned
      expect(ips).toContain('192.168.1.1');
      expect(ips).toContain('192.168.1.2');
      expect(ips).toContain('192.168.1.3');
      expect(ips).toHaveLength(3);
    });

    it('excludes group nodes', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        role: 'group',
        ip: '192.168.1.0',
        children: [],
      };

      const ips = getMonitoredDeviceIPs(root);
      expect(ips).not.toContain('192.168.1.0');
    });
  });

  describe('getSilencedDeviceIPs', () => {
    it('returns IPs of devices with monitoring explicitly disabled', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        role: 'group',
        children: [
          { id: '1', name: 'A', ip: '192.168.1.1', role: 'server', monitoringEnabled: true },
          { id: '2', name: 'B', ip: '192.168.1.2', role: 'server', monitoringEnabled: false },
          { id: '3', name: 'C', ip: '192.168.1.3', role: 'server' }, // undefined = enabled
        ],
      };

      const ips = getSilencedDeviceIPs(root);

      expect(ips).not.toContain('192.168.1.1');
      expect(ips).toContain('192.168.1.2');
      expect(ips).not.toContain('192.168.1.3');
      expect(ips).toHaveLength(1);
    });
  });

  describe('findGroupByPrefix', () => {
    it('finds group by exact ID match', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          { id: 'infrastructure', name: 'Infrastructure', role: 'group', children: [] },
          { id: 'servers', name: 'Servers', role: 'group', children: [] },
        ],
      };

      const group = findGroupByPrefix(root, 'infrastructure');
      expect(group?.id).toBe('infrastructure');
    });

    it('finds group by group:prefix pattern', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [{ id: 'group:infra', name: 'Infrastructure', role: 'group', children: [] }],
      };

      const group = findGroupByPrefix(root, 'infra');
      expect(group?.id).toBe('group:infra');
    });

    it('returns undefined for no match', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [{ id: 'infrastructure', name: 'Infrastructure', role: 'group', children: [] }],
      };

      const group = findGroupByPrefix(root, 'nonexistent');
      expect(group).toBeUndefined();
    });
  });

  describe('getTargetGroupForRole', () => {
    it('returns undefined for gateway/router (stays at root)', () => {
      const result = getTargetGroupForRole('gateway/router');
      expect(result).toBeUndefined();
    });

    it('returns infrastructure info for switch/ap', () => {
      const result = getTargetGroupForRole('switch/ap');
      expect(result?.prefix).toBe('infrastructure');
      expect(result?.name).toBe('Infrastructure');
    });

    it('returns servers info for server role', () => {
      const result = getTargetGroupForRole('server');
      expect(result?.prefix).toBe('servers');
      expect(result?.name).toBe('Servers');
    });

    it('returns clients info for client role', () => {
      const result = getTargetGroupForRole('client');
      expect(result?.prefix).toBe('clients');
      expect(result?.name).toBe('Clients');
    });
  });

  describe('removeFromAllGroups', () => {
    it('removes node from group and returns it', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'servers',
            name: 'Servers',
            role: 'group',
            children: [
              { id: '192.168.1.1', name: 'Server1', role: 'server' },
              { id: '192.168.1.2', name: 'Server2', role: 'server' },
            ],
          },
        ],
      };

      const removed = removeFromAllGroups(root, '192.168.1.1');
      expect(removed?.name).toBe('Server1');
      expect(root.children![0].children).toHaveLength(1);
    });

    it('returns undefined if node not found', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [],
      };

      const removed = removeFromAllGroups(root, 'non-existent');
      expect(removed).toBeUndefined();
    });
  });
});
