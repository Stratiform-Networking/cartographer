/**
 * Map layout composable
 *
 * Manages network map node positions, layout persistence, and layout cleanup.
 */

import type { TreeNode } from '../types/network';
import type { SavedLayout } from '../types/layout';
import { compareNodesByIp } from '../utils/networkUtils';

// Re-export type for backwards compatibility
export type { SavedLayout } from '../types/layout';

// Shared state across components
const positions: Map<string, { x: number; y: number }> = new Map();

export function useMapLayout() {
  function applySavedPositions(root: TreeNode, saved?: SavedLayout) {
    if (!saved) return;
    const walk = (n: TreeNode) => {
      const pos = saved.positions[n.id];
      if (pos) {
        n.fx = pos.x;
        n.fy = pos.y;
        positions.set(n.id, { x: pos.x, y: pos.y });
      }
      for (const c of n.children || []) walk(c);
    };
    walk(root);
  }

  function updatePosition(id: string, x: number, y: number) {
    positions.set(id, { x, y });
  }

  function exportLayout(root: TreeNode): SavedLayout {
    // Ensure we include all nodes, even those not dragged yet (use current fx/fy if set)
    const map: Record<string, { x: number; y: number }> = {};
    const walk = (n: TreeNode) => {
      const p =
        positions.get(n.id) ||
        (typeof n.fx === 'number' && typeof n.fy === 'number' ? { x: n.fx, y: n.fy } : undefined);
      if (p) map[n.id] = { x: p.x, y: p.y };
      for (const c of n.children || []) walk(c);
    };
    walk(root);
    return {
      version: 1,
      timestamp: new Date().toISOString(),
      positions: map,
      root: root,
    };
  }

  function importLayout(jsonText: string): SavedLayout {
    const parsed = JSON.parse(jsonText) as SavedLayout;
    return parsed;
  }

  function clearPositions() {
    positions.clear();
  }

  /**
   * Clean up and reorganize the layout based on network hierarchy.
   * Arranges nodes in columns by depth with consistent spacing.
   */
  function cleanUpLayout(root: TreeNode): void {
    // Clear all saved positions
    clearPositions();

    // Build a map of all nodes (including nested ones)
    const allNodes = new Map<string, TreeNode>();
    const collectNodes = (n: TreeNode) => {
      allNodes.set(n.id, n);
      for (const g of n.children || []) {
        for (const c of g.children || []) {
          allNodes.set(c.id, c);
        }
      }
    };
    collectNodes(root);

    // Calculate depth for each node based on parentId chain
    const getDepth = (nodeId: string, visited = new Set<string>()): number => {
      if (nodeId === root.id) return 0;
      if (visited.has(nodeId)) return 0; // Prevent infinite loops
      visited.add(nodeId);

      const node = allNodes.get(nodeId);
      if (!node) return 0;

      const parentId = (node as any).parentId;
      if (!parentId || parentId === root.id) {
        // Direct connection to root
        return 1;
      }

      // Recursively get parent's depth
      return getDepth(parentId, visited) + 1;
    };

    // Group nodes by depth
    const nodesByDepth = new Map<number, TreeNode[]>();
    allNodes.forEach((node, id) => {
      if (id === root.id) return; // Skip root itself
      const depth = getDepth(id);
      if (!nodesByDepth.has(depth)) {
        nodesByDepth.set(depth, []);
      }
      nodesByDepth.get(depth)!.push(node);
    });

    // Track node sort order for parent-based sorting
    const nodeSortOrder = new Map<string, number>();
    nodeSortOrder.set(root.id, 0);

    // Sort each depth level, considering parent positions
    const maxDepthForSort = Math.max(...Array.from(nodesByDepth.keys()), 0);
    for (let depth = 1; depth <= maxDepthForSort; depth++) {
      const nodesAtDepth = nodesByDepth.get(depth) || [];
      if (nodesAtDepth.length === 0) continue;

      // Sort by: 1) parent's sort order, 2) IP address
      nodesAtDepth.sort((a, b) => {
        const parentIdA = (a as any).parentId || root.id;
        const parentIdB = (b as any).parentId || root.id;
        const parentOrderA = nodeSortOrder.get(parentIdA) ?? 999999;
        const parentOrderB = nodeSortOrder.get(parentIdB) ?? 999999;

        // First, compare by parent position
        if (parentOrderA !== parentOrderB) {
          return parentOrderA - parentOrderB;
        }

        // Within same parent group, sort by IP
        return compareNodesByIp(a, b);
      });

      // Record sort order for this depth (for next depth's sorting)
      nodesAtDepth.forEach((node, index) => {
        nodeSortOrder.set(node.id, index);
      });
    }

    // Layout parameters
    const columnWidth = 220;
    const nodeGapY = 100;
    const marginX = 60;
    const canvasHeight = 800; // Approximate canvas height

    // Clear all positions
    const clearNodePositions = (n: TreeNode) => {
      delete (n as any).fx;
      delete (n as any).fy;
      for (const c of n.children || []) {
        clearNodePositions(c);
      }
    };
    clearNodePositions(root);

    // Position root
    (root as any).fx = marginX;
    (root as any).fy = canvasHeight / 2;

    // Position nodes by depth
    const maxDepth = Math.max(...Array.from(nodesByDepth.keys()), 0);
    for (let depth = 1; depth <= maxDepth; depth++) {
      const nodesAtDepth = nodesByDepth.get(depth) || [];
      if (nodesAtDepth.length === 0) continue;

      const columnX = marginX + depth * columnWidth;
      const totalHeight = Math.max(0, (nodesAtDepth.length - 1) * nodeGapY);
      const startY = (canvasHeight - totalHeight) / 2;

      nodesAtDepth.forEach((node, idx) => {
        (node as any).fx = columnX;
        (node as any).fy = startY + idx * nodeGapY;
      });
    }
  }

  return {
    positions,
    applySavedPositions,
    updatePosition,
    exportLayout,
    importLayout,
    clearPositions,
    cleanUpLayout,
  };
}
