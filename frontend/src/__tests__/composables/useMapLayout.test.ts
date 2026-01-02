/**
 * Tests for composables/useMapLayout.ts
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useMapLayout } from '../../composables/useMapLayout';
import type { TreeNode } from '../../types/network';
import type { SavedLayout } from '../../types/layout';

describe('useMapLayout', () => {
  // Get fresh composable for each test to reset internal state
  let applySavedPositions: ReturnType<typeof useMapLayout>['applySavedPositions'];
  let clearPositions: ReturnType<typeof useMapLayout>['clearPositions'];
  let exportLayout: ReturnType<typeof useMapLayout>['exportLayout'];
  let updatePosition: ReturnType<typeof useMapLayout>['updatePosition'];
  let importLayout: ReturnType<typeof useMapLayout>['importLayout'];
  let cleanUpLayout: ReturnType<typeof useMapLayout>['cleanUpLayout'];
  let positions: ReturnType<typeof useMapLayout>['positions'];

  beforeEach(() => {
    const layout = useMapLayout();
    applySavedPositions = layout.applySavedPositions;
    clearPositions = layout.clearPositions;
    exportLayout = layout.exportLayout;
    updatePosition = layout.updatePosition;
    importLayout = layout.importLayout;
    cleanUpLayout = layout.cleanUpLayout;
    positions = layout.positions;
    // Clear any shared state
    clearPositions();
  });

  describe('applySavedPositions', () => {
    it('applies saved fx/fy positions to matching nodes', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          { id: '192.168.1.1', name: 'Router', role: 'gateway/router' },
          { id: '192.168.1.2', name: 'Server', role: 'server' },
        ],
      };

      const saved: SavedLayout = {
        version: 1,
        timestamp: new Date().toISOString(),
        positions: {
          '192.168.1.1': { x: 100, y: 200 },
          '192.168.1.2': { x: 300, y: 400 },
        },
        root: root,
      };

      applySavedPositions(root, saved);

      expect(root.children![0].fx).toBe(100);
      expect(root.children![0].fy).toBe(200);
      expect(root.children![1].fx).toBe(300);
      expect(root.children![1].fy).toBe(400);
    });

    it('does not modify nodes without saved positions', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [{ id: '192.168.1.1', name: 'Router', role: 'gateway/router' }],
      };

      const saved: SavedLayout = {
        version: 1,
        timestamp: new Date().toISOString(),
        positions: {
          '192.168.1.2': { x: 100, y: 200 }, // Different ID
        },
        root: root,
      };

      applySavedPositions(root, saved);

      expect(root.children![0].fx).toBeUndefined();
      expect(root.children![0].fy).toBeUndefined();
    });

    it('handles undefined saved layout', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [{ id: '192.168.1.1', name: 'Router', role: 'gateway/router' }],
      };

      // Should not throw
      applySavedPositions(root, undefined);
      expect(root.children![0].fx).toBeUndefined();
    });
  });

  describe('clearPositions', () => {
    it('clears the internal positions map', () => {
      // Add some positions
      updatePosition('node1', 100, 200);
      updatePosition('node2', 300, 400);

      expect(positions.size).toBe(2);

      clearPositions();

      expect(positions.size).toBe(0);
    });
  });

  describe('exportLayout', () => {
    it('exports all node positions from fx/fy', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        fx: 0,
        fy: 0,
        children: [
          { id: '192.168.1.1', name: 'Router', fx: 100, fy: 200 },
          { id: '192.168.1.2', name: 'Server', fx: 300, fy: 400 },
        ],
      };

      const layout = exportLayout(root);

      expect(layout.positions['root']).toEqual({ x: 0, y: 0 });
      expect(layout.positions['192.168.1.1']).toEqual({ x: 100, y: 200 });
      expect(layout.positions['192.168.1.2']).toEqual({ x: 300, y: 400 });
    });

    it('skips nodes without positions', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        fx: 0,
        fy: 0,
        children: [
          { id: '192.168.1.1', name: 'Router', fx: 100, fy: 200 },
          { id: '192.168.1.2', name: 'Server' }, // No fx/fy
        ],
      };

      const layout = exportLayout(root);

      expect(layout.positions['192.168.1.1']).toBeDefined();
      expect(layout.positions['192.168.1.2']).toBeUndefined();
    });

    it('includes positions from internal map', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [{ id: '192.168.1.1', name: 'Router' }],
      };

      // Add position via updatePosition
      updatePosition('192.168.1.1', 500, 600);

      const layout = exportLayout(root);

      expect(layout.positions['192.168.1.1']).toEqual({ x: 500, y: 600 });
    });

    it('includes version and timestamp', () => {
      const root: TreeNode = { id: 'root', name: 'Network' };
      const layout = exportLayout(root);

      expect(layout.version).toBe(1);
      expect(layout.timestamp).toBeDefined();
    });
  });

  describe('updatePosition', () => {
    it('stores position in internal map', () => {
      updatePosition('node1', 100, 200);

      expect(positions.get('node1')).toEqual({ x: 100, y: 200 });
    });

    it('overwrites existing position', () => {
      updatePosition('node1', 100, 200);
      updatePosition('node1', 300, 400);

      expect(positions.get('node1')).toEqual({ x: 300, y: 400 });
    });
  });

  describe('importLayout', () => {
    it('parses valid JSON layout', () => {
      const layoutData: SavedLayout = {
        version: 1,
        timestamp: '2024-06-15T12:00:00Z',
        positions: {
          node1: { x: 100, y: 200 },
          node2: { x: 300, y: 400 },
        },
        root: { id: 'root', name: 'Network' },
      };

      const result = importLayout(JSON.stringify(layoutData));

      expect(result.version).toBe(1);
      expect(result.timestamp).toBe('2024-06-15T12:00:00Z');
      expect(result.positions['node1']).toEqual({ x: 100, y: 200 });
      expect(result.positions['node2']).toEqual({ x: 300, y: 400 });
    });

    it('throws on invalid JSON', () => {
      expect(() => importLayout('not valid json')).toThrow();
    });

    it('handles empty positions object', () => {
      const layoutData: SavedLayout = {
        version: 1,
        timestamp: '2024-06-15T12:00:00Z',
        positions: {},
        root: { id: 'root', name: 'Network' },
      };

      const result = importLayout(JSON.stringify(layoutData));
      expect(result.positions).toEqual({});
    });
  });

  describe('cleanUpLayout', () => {
    it('positions root node at the left margin', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [],
      };

      cleanUpLayout(root);

      expect((root as any).fx).toBe(60); // marginX
      expect((root as any).fy).toBe(400); // canvasHeight / 2
    });

    it('arranges direct children in a column', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group1',
            name: 'Group 1',
            role: 'group',
            children: [
              { id: '192.168.1.1', name: 'Device 1', role: 'server', parentId: 'root' },
              { id: '192.168.1.2', name: 'Device 2', role: 'server', parentId: 'root' },
            ],
          },
        ],
      };

      cleanUpLayout(root);

      // Devices should be positioned at depth 1
      const device1 = root.children![0].children![0];
      const device2 = root.children![0].children![1];

      expect((device1 as any).fx).toBe(280); // marginX + 1 * columnWidth
      expect((device2 as any).fx).toBe(280);
      // Y positions should be vertically distributed
      expect((device1 as any).fy).toBeDefined();
      expect((device2 as any).fy).toBeDefined();
    });

    it('clears existing positions before arranging', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        fx: 999,
        fy: 999,
        children: [],
      };

      // Add some positions to internal map
      updatePosition('root', 500, 500);

      cleanUpLayout(root);

      // Internal positions should be cleared
      expect(positions.size).toBe(0);
      // Root should have new position
      expect((root as any).fx).toBe(60);
    });

    it('handles nested hierarchy with parentId chain', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group1',
            name: 'Group 1',
            role: 'group',
            children: [
              { id: '192.168.1.1', name: 'Router', role: 'gateway/router', parentId: 'root' },
              { id: '192.168.1.10', name: 'Switch', role: 'switch/ap', parentId: '192.168.1.1' },
            ],
          },
        ],
      };

      cleanUpLayout(root);

      const router = root.children![0].children![0];
      const switchNode = root.children![0].children![1];

      // Router at depth 1, switch at depth 2
      expect((router as any).fx).toBe(280); // depth 1
      expect((switchNode as any).fx).toBe(500); // depth 2
    });

    it('sorts nodes by IP address within same parent', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group1',
            name: 'Group 1',
            role: 'group',
            children: [
              {
                id: '192.168.1.100',
                name: 'Device C',
                ip: '192.168.1.100',
                role: 'server',
                parentId: 'root',
              },
              {
                id: '192.168.1.1',
                name: 'Device A',
                ip: '192.168.1.1',
                role: 'server',
                parentId: 'root',
              },
              {
                id: '192.168.1.50',
                name: 'Device B',
                ip: '192.168.1.50',
                role: 'server',
                parentId: 'root',
              },
            ],
          },
        ],
      };

      cleanUpLayout(root);

      const devices = root.children![0].children!;
      // After sorting by IP, order should be: .1, .50, .100
      // The one with lowest Y should be first in sort order
      const sortedByY = [...devices].sort((a, b) => (a as any).fy - (b as any).fy);
      expect(sortedByY[0].ip).toBe('192.168.1.1');
      expect(sortedByY[1].ip).toBe('192.168.1.50');
      expect(sortedByY[2].ip).toBe('192.168.1.100');
    });

    it('handles empty children array', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [],
      };

      // Should not throw
      expect(() => cleanUpLayout(root)).not.toThrow();
      expect((root as any).fx).toBe(60);
    });

    it('handles circular parentId references gracefully', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group1',
            name: 'Group 1',
            role: 'group',
            children: [
              { id: 'node1', name: 'Node 1', role: 'server', parentId: 'node2' },
              { id: 'node2', name: 'Node 2', role: 'server', parentId: 'node1' },
            ],
          },
        ],
      };

      // Should not throw or infinite loop
      expect(() => cleanUpLayout(root)).not.toThrow();
    });

    it('handles nodes without parentId', () => {
      const root: TreeNode = {
        id: 'root',
        name: 'Network',
        children: [
          {
            id: 'group1',
            name: 'Group 1',
            role: 'group',
            children: [
              { id: '192.168.1.1', name: 'Device 1', role: 'server' }, // No parentId
            ],
          },
        ],
      };

      // Should not throw
      expect(() => cleanUpLayout(root)).not.toThrow();
      const device = root.children![0].children![0];
      expect((device as any).fx).toBeDefined();
    });
  });
});
