/**
 * Network data composable
 *
 * Pure transformation logic for parsing network map data and node manipulation.
 * No API calls - this is a utility composable.
 */

import type {
  DeviceEntry,
  DeviceRole,
  GatewayInfo,
  ParsedNetworkMap,
  TreeNode,
  NodeVersion,
} from '../types/network';

// ==================== Parsing Helpers ====================

function parseGateway(section: string): GatewayInfo | undefined {
  const ipHost = /Gateway:\s*([0-9.]+)\s*\(([^)]+)\)/i.exec(section);
  const lanIf = /LAN Interface:\s*([^\n]+)/i.exec(section);
  const subnet = /Subnet:\s*([^\n]+)/i.exec(section);
  if (!ipHost) return undefined;
  return {
    ip: ipHost[1],
    hostname: ipHost[2],
    lanInterface: lanIf?.[1]?.trim(),
    subnet: subnet?.[1]?.trim(),
  };
}

function parseDevices(section: string): DeviceEntry[] {
  const devices: DeviceEntry[] = [];
  const lines = section.split('\n');
  for (const line of lines) {
    // 172.16.191.1    | routerboard.com.lan                 | role=gateway/router  | depth=0
    const m = /^\s*([0-9.]+)\s*\|\s*([^\|]+?)\s*\|\s*role=([a-z\/-]+)\s*\|\s*depth=(\d+)/i.exec(
      line
    );
    if (m) {
      const ip = m[1].trim();
      const hostnameRaw = m[2].trim();
      const role = m[3].trim() as DeviceRole;
      const depth = parseInt(m[4].trim(), 10);
      devices.push({
        ip,
        hostname: hostnameRaw === 'Unknown' ? 'Unknown' : hostnameRaw,
        role,
        depth,
      });
    }
  }
  return devices;
}

function parseHeuristicTree(
  section: string
): Record<string, { ip: string; hostname: string; role: DeviceRole }[]> {
  const groups: Record<string, { ip: string; hostname: string; role: DeviceRole }[]> = {};
  let currentKey: string | null = null;

  const roleFromBracket = (s: string): DeviceRole => {
    const r = s.toLowerCase();
    if (r.includes('gateway')) return 'gateway/router';
    if (r.includes('switch')) return 'switch/ap';
    if (r.includes('firewall')) return 'firewall';
    if (r.includes('server')) return 'server';
    if (r.includes('service')) return 'service';
    if (r.includes('nas')) return 'nas';
    if (r.includes('client')) return 'client';
    return 'unknown';
  };

  for (const line of section.split('\n')) {
    const header = /^\s*([A-Za-z \/()0-9:\-]+):\s*$/.exec(line);
    if (header) {
      currentKey = header[1].trim();
      groups[currentKey] = [];
      continue;
    }
    //  - 172.16.191.106  (tl-sg108e.lan) [switch/ap]
    const item = /^\s*-\s*([0-9.]+)\s*\(([^)]+)\)\s*\[([^\]]+)\]/.exec(line);
    if (currentKey && item) {
      groups[currentKey].push({
        ip: item[1],
        hostname: item[2],
        role: roleFromBracket(item[3]),
      });
    }
  }
  return groups;
}

// ==================== Version Management ====================

/**
 * Initialize version tracking for a node.
 */
function initializeNodeVersion(node: TreeNode, source: 'manual' | 'mapper' = 'manual'): void {
  const now = new Date().toISOString();
  if (!node.createdAt) {
    node.createdAt = now;
    node.version = 1;
    node.history = [
      {
        version: 1,
        timestamp: now,
        changes: [`Node created (${source})`],
      },
    ];
  }
  node.updatedAt = now;
}

/**
 * Update version tracking for a node with change history.
 */
function updateNodeVersion(node: TreeNode, changes: string[]): void {
  const now = new Date().toISOString();
  const newVersion = (node.version || 1) + 1;

  // Initialize if not already done
  if (!node.createdAt) {
    node.createdAt = now;
  }

  node.updatedAt = now;
  node.version = newVersion;

  // Add to history (keep last 20 versions to avoid bloat)
  if (!node.history) {
    node.history = [];
  }
  node.history.push({
    version: newVersion,
    timestamp: now,
    changes,
  });
  if (node.history.length > 20) {
    node.history = node.history.slice(-20);
  }
}

/**
 * Ensure all nodes in a tree have version tracking.
 */
function ensureAllNodesVersioned(root: TreeNode, source: 'manual' | 'mapper' = 'mapper'): void {
  const walk = (n: TreeNode) => {
    if (n.role !== 'group') {
      initializeNodeVersion(n, source);
    }
    for (const c of n.children || []) walk(c);
  };
  walk(root);
}

// ==================== Node Manipulation ====================

/**
 * Find a node by ID in the tree (recursive).
 */
function findNodeById(root: TreeNode, id?: string): TreeNode | undefined {
  if (!id) return undefined;
  if (root.id === id) return root;
  for (const c of root.children || []) {
    const f = findNodeById(c, id);
    if (f) return f;
  }
  return undefined;
}

/**
 * Flatten all device nodes from a tree (excludes groups).
 * Deduplicates by IP/ID to avoid counting the same device twice.
 */
function flattenDevices(root: TreeNode): TreeNode[] {
  const res: TreeNode[] = [];
  const seen = new Set<string>();
  const walk = (n: TreeNode) => {
    // Include ALL non-group nodes, including the root if it's a real device (e.g., gateway/router)
    // Deduplicate by IP/ID to avoid counting the same device twice (root might also exist as a child)
    if (n.role !== 'group') {
      const key = n.ip || n.id;
      if (!seen.has(key)) {
        seen.add(key);
        res.push(n);
      }
    }
    for (const c of n.children || []) walk(c);
  };
  walk(root);
  return res;
}

/**
 * Walk all nodes in the tree (root + all nested children).
 */
function walkAll(root: TreeNode, fn: (n: TreeNode, parent?: TreeNode) => void): void {
  fn(root, undefined);
  for (const g of root.children || []) {
    for (const c of g.children || []) {
      fn(c, g);
    }
  }
}

/**
 * Remove a node from all groups in the tree.
 * Returns the removed node if found, undefined otherwise.
 */
function removeFromAllGroups(root: TreeNode, id: string): TreeNode | undefined {
  for (const g of root.children || []) {
    const idx = (g.children || []).findIndex((c) => c.id === id);
    if (idx !== -1) {
      const [node] = g.children!.splice(idx, 1);
      return node;
    }
  }
  return undefined;
}

/**
 * Find a group by prefix (e.g., 'infrastructure', 'servers', 'clients').
 */
function findGroupByPrefix(root: TreeNode, prefix: string): TreeNode | undefined {
  return (root.children || []).find(
    (g) => g.role === 'group' && (g.id === prefix || g.id.startsWith(`group:${prefix}`))
  );
}

/**
 * Get target group info for a given role.
 */
function getTargetGroupForRole(role: DeviceRole): { prefix: string; name: string } | undefined {
  switch (role) {
    case 'firewall':
    case 'switch/ap':
      return { prefix: 'infrastructure', name: 'Infrastructure' };
    case 'server':
    case 'service':
    case 'nas':
      return { prefix: 'servers', name: 'Servers' };
    case 'client':
    case 'unknown':
      return { prefix: 'clients', name: 'Clients' };
    default:
      return undefined; // gateway/router stays at root
  }
}

// ==================== Health Monitoring Helpers ====================

/**
 * Get all device IPs for health monitoring (includes all devices with IPs).
 * ALL devices are tracked by the health service for ML anomaly detection.
 */
function getMonitoredDeviceIPs(root: TreeNode): string[] {
  const devices = flattenDevices(root);
  return devices
    .filter((d) => d.ip) // Include ALL devices with IPs
    .map((d) => d.ip!)
    .filter((ip): ip is string => !!ip);
}

/**
 * Get IPs of devices that have monitoring disabled (for notification service silencing).
 */
function getSilencedDeviceIPs(root: TreeNode): string[] {
  const devices = flattenDevices(root);
  return devices
    .filter((d) => d.ip && d.monitoringEnabled === false) // Only include nodes with monitoring explicitly disabled
    .map((d) => d.ip!)
    .filter((ip): ip is string => !!ip);
}

// ==================== Tree Building ====================

function buildTree(
  gateway: GatewayInfo | undefined,
  groups: Record<string, { ip: string; hostname: string; role: DeviceRole }[]>
): TreeNode {
  const now = new Date().toISOString();
  const root: TreeNode = {
    id: gateway ? gateway.ip : 'root',
    name: gateway ? `${gateway.ip} (${gateway.hostname})` : 'Network',
    role: gateway ? 'gateway/router' : 'group',
    ip: gateway?.ip,
    hostname: gateway?.hostname,
    children: [],
    createdAt: now,
    updatedAt: now,
    version: 1,
    history: [
      {
        version: 1,
        timestamp: now,
        changes: ['Gateway discovered by network mapper'],
      },
    ],
  };

  for (const [groupName, items] of Object.entries(groups)) {
    if (!items.length) continue;
    const groupNode: TreeNode = {
      id: `group:${groupName}`,
      name: groupName,
      role: 'group',
      children: [],
    };
    for (const it of items) {
      const deviceNode: TreeNode = {
        id: it.ip,
        name: `${it.ip} (${it.hostname})`,
        role: it.role,
        ip: it.ip,
        hostname: it.hostname,
        children: [],
      };
      initializeNodeVersion(deviceNode, 'mapper');
      groupNode.children!.push(deviceNode);
    }
    root.children!.push(groupNode);
  }
  return root;
}

// ==================== Main Composable Export ====================

export function useNetworkData() {
  function parseNetworkMap(raw: string): ParsedNetworkMap {
    const gatewaySection = raw;
    const devicesSection = (() => {
      const start = raw.indexOf('=== Devices Found ===');
      if (start === -1) return '';
      const rest = raw.slice(start);
      const endIdx = rest.indexOf('\n\n');
      const seg = endIdx === -1 ? rest : rest.slice(0, endIdx);
      return seg;
    })();
    const heuristicSection = (() => {
      const start = raw.indexOf('=== Heuristic Topology Tree ===');
      if (start === -1) return '';
      return raw.slice(start);
    })();

    const gateway = parseGateway(gatewaySection);
    const devices = parseDevices(devicesSection);
    const groups = parseHeuristicTree(heuristicSection);
    const root = buildTree(gateway, groups);
    return {
      raw,
      gateway,
      devices,
      root,
    };
  }

  return {
    // Parsing
    parseNetworkMap,

    // Version management
    initializeNodeVersion,
    updateNodeVersion,
    ensureAllNodesVersioned,

    // Node manipulation
    findNodeById,
    flattenDevices,
    walkAll,
    removeFromAllGroups,
    findGroupByPrefix,
    getTargetGroupForRole,

    // Health monitoring helpers
    getMonitoredDeviceIPs,
    getSilencedDeviceIPs,
  };
}
