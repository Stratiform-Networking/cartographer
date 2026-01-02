<template>
  <div class="w-full h-full relative">
    <!-- Gradient background using OKLCH color space for smoother interpolation -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <!-- OKLCH gradient with blur for smooth banding-free transitions -->
      <div class="absolute -inset-4 blur-xl transition-colors"></div>
      <!-- Blue noise dither overlay - prevents color banding -->
      <div class="absolute inset-0 blue-noise-dither"></div>
      <!-- Subtle radial accent glow with smoother falloff -->
      <div
        class="absolute inset-0"
        :class="isDark ? 'opacity-25' : 'opacity-40'"
        style="
          background: radial-gradient(
            ellipse 100% 80% at 50% 30%,
            rgba(56, 189, 248, 0.08) 0%,
            rgba(56, 189, 248, 0.02) 35%,
            transparent 55%
          );
        "
      ></div>
      <!-- Bottom corner accent with smoother falloff -->
      <div
        class="absolute inset-0"
        :class="isDark ? 'opacity-15' : 'opacity-30'"
        style="
          background: radial-gradient(
            ellipse 60% 50% at 90% 90%,
            rgba(99, 102, 241, 0.06) 0%,
            rgba(99, 102, 241, 0.015) 35%,
            transparent 55%
          );
        "
      ></div>
    </div>
    <!-- SVG with grid pattern that pans with content -->
    <svg ref="svgRef" class="relative w-full h-full transition-colors"></svg>
  </div>
</template>

<script lang="ts" setup>
import * as d3 from 'd3';
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import type { TreeNode, DeviceMetrics, HealthStatus } from '../types/network';
import { compareIpAddresses } from '../utils/networkUtils';

const props = defineProps<{
  data: TreeNode;
  sensitiveMode?: boolean;
  isDark?: boolean;
  healthMetrics?: Record<string, DeviceMetrics>;
}>();

// Get status color for health glow (using light fill colors like selection)
function getStatusColor(status?: HealthStatus, dark?: boolean): string {
  switch (status) {
    case 'healthy':
      return dark ? '#22c55e' : '#bbf7d0'; // green-500 / green-200
    case 'degraded':
      return dark ? '#f59e0b' : '#fde68a'; // amber-500 / amber-200
    case 'unhealthy':
      return dark ? '#ef4444' : '#fecaca'; // red-500 / red-200
    default:
      return 'none'; // unknown - no glow
  }
}

// Get health status for a node by IP
function getNodeHealthStatus(nodeId: string, nodeRef?: TreeNode): HealthStatus | undefined {
  if (!props.healthMetrics) return undefined;

  // Don't show status for nodes with monitoring disabled
  if ((nodeRef as any)?.monitoringEnabled === false) return undefined;

  // Try to get metrics by IP (which is usually the node id)
  const ip = (nodeRef as any)?.ip || nodeId;
  const metrics = props.healthMetrics[ip];
  return metrics?.status;
}

const svgRef = ref<SVGSVGElement | null>(null);

let cleanup: (() => void) | null = null;
let currentTransform = d3.zoomIdentity;
let currentZoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
let initialTransform: d3.ZoomTransform | null = null; // Calculated centered transform

function roleIcon(role?: string): string {
  const r = role || 'unknown';
  switch (r) {
    case 'gateway/router':
      return '📡';
    case 'firewall':
      return '🧱';
    case 'switch/ap':
      return '🔀';
    case 'server':
      return '🖥️';
    case 'service':
      return '⚙️';
    case 'nas':
      return '🗄️';
    case 'client':
      return '💻';
    default:
      return '❓';
  }
}

// Mask IP address for sensitive mode
function maskIP(ip?: string): string {
  if (!ip) return '•••.•••.•••.•••';
  // Replace numbers with bullets, keep dots
  return ip.replace(/\d/g, '•');
}

// Generate sanitized node name for sensitive mode
function getSanitizedName(node: TreeNode): string {
  if (!props.sensitiveMode) {
    return node.name;
  }

  // For sensitive mode, show role + masked identifier
  const role = node.role || 'device';
  const roleName =
    role === 'gateway/router'
      ? 'Gateway'
      : role === 'switch/ap'
        ? 'Switch/AP'
        : role === 'firewall'
          ? 'Firewall'
          : role === 'server'
            ? 'Server'
            : role === 'service'
              ? 'Service'
              : role === 'nas'
                ? 'NAS'
                : role === 'client'
                  ? 'Client'
                  : 'Device';

  // If hostname exists and doesn't contain IP-like patterns, show truncated hostname
  const hostname = node.hostname || '';
  if (hostname && !/\d+\.\d+\.\d+/.test(hostname)) {
    // Truncate hostname if too long
    const truncated = hostname.length > 15 ? hostname.substring(0, 12) + '...' : hostname;
    return `${roleName} (${truncated})`;
  }

  // Otherwise show masked IP
  return `${roleName} (${maskIP(node.ip)})`;
}

function render() {
  const svg = d3.select(svgRef.value!);
  svg.selectAll('*').remove();

  const width = svgRef.value?.clientWidth || 800;
  const height = svgRef.value?.clientHeight || 600;
  const dark = props.isDark !== false; // Default to dark if not specified

  // Define grid pattern
  const defs = svg.append('defs');
  const gridSize = 24;
  const pattern = defs
    .append('pattern')
    .attr('id', 'grid-pattern-embed')
    .attr('width', gridSize)
    .attr('height', gridSize)
    .attr('patternUnits', 'userSpaceOnUse');

  pattern
    .append('circle')
    .attr('cx', gridSize / 2)
    .attr('cy', gridSize / 2)
    .attr('r', 1)
    .attr('fill', dark ? 'rgba(148, 163, 184, 0.15)' : 'rgba(148, 163, 184, 0.35)');

  const g = svg
    .attr('viewBox', [0, 0, width, height].join(' '))
    .append('g')
    .attr('class', 'zoom-layer');

  // Add grid background that pans with content (large enough for any pan/zoom)
  g.insert('rect', ':first-child')
    .attr('class', 'grid-bg')
    .attr('x', -5000)
    .attr('y', -5000)
    .attr('width', 10000)
    .attr('height', 10000)
    .attr('fill', 'url(#grid-pattern-embed)');

  // ─────────────────────────────────────────────────────────────────────────────
  // Depth-based layout (left → right)
  // ─────────────────────────────────────────────────────────────────────────────
  const data = props.data;
  const children = data.children || [];

  type DrawNode = {
    id: string;
    name: string;
    role?: string;
    x: number;
    y: number;
    ref?: TreeNode;
    depth?: number;
  };
  type DrawLink = { source: DrawNode; target: DrawNode };

  const marginX = 60;
  const marginY = 40;
  const columnWidth = 220;
  const nodeGapY = 100;

  const nodes: DrawNode[] = [];
  const links: DrawLink[] = [];

  // Build a map of all nodes
  const allNodesMap = new Map<string, TreeNode>();
  allNodesMap.set(data.id, data);
  for (const g of children) {
    for (const c of g.children || []) {
      allNodesMap.set(c.id, c);
    }
  }

  // Calculate depth for each node based on parentId chain
  const getDepth = (nodeId: string, visited = new Set<string>()): number => {
    if (nodeId === data.id) return 0;
    if (visited.has(nodeId)) return 1;
    visited.add(nodeId);

    const node = allNodesMap.get(nodeId);
    if (!node) return 1;

    const parentId = (node as any).parentId;
    if (!parentId || parentId === data.id) {
      return 1;
    }

    return getDepth(parentId, visited) + 1;
  };

  // Collect all device nodes with their depths
  const deviceNodes: Array<{ node: TreeNode; depth: number }> = [];
  for (const g of children) {
    for (const c of g.children || []) {
      const depth = getDepth(c.id);
      deviceNodes.push({ node: c, depth });
    }
  }

  // Group by depth
  const nodesByDepth = new Map<number, TreeNode[]>();
  deviceNodes.forEach(({ node, depth }) => {
    if (!nodesByDepth.has(depth)) {
      nodesByDepth.set(depth, []);
    }
    nodesByDepth.get(depth)!.push(node);
  });

  // Sort nodes within each depth by IP address
  // IP comparison using shared utility
  const compareIps = (a: TreeNode, b: TreeNode): number => {
    const ipA = (a as any).ip || a.id;
    const ipB = (b as any).ip || b.id;
    return compareIpAddresses(ipA, ipB);
  };

  // Track node sort order for parent-based sorting
  const nodeSortOrder = new Map<string, number>();
  nodeSortOrder.set(data.id, 0);

  const maxDepthForSort = Math.max(...Array.from(nodesByDepth.keys()), 0);
  for (let depth = 1; depth <= maxDepthForSort; depth++) {
    const nodesAtDepth = nodesByDepth.get(depth) || [];
    if (nodesAtDepth.length === 0) continue;

    nodesAtDepth.sort((a, b) => {
      const parentIdA = (a as any).parentId || data.id;
      const parentIdB = (b as any).parentId || data.id;
      const parentOrderA = nodeSortOrder.get(parentIdA) ?? 999999;
      const parentOrderB = nodeSortOrder.get(parentIdB) ?? 999999;

      if (parentOrderA !== parentOrderB) {
        return parentOrderA - parentOrderB;
      }

      return compareIps(a, b);
    });

    nodesAtDepth.forEach((node, index) => {
      nodeSortOrder.set(node.id, index);
    });
  }

  // Helper for vertical centering
  const centerColumnY = (count: number) => {
    const total = Math.max(0, (count - 1) * nodeGapY);
    return (height - marginY * 2 - total) / 2 + marginY;
  };

  // Place root node (depth 0)
  const router: DrawNode = {
    id: data.id,
    name: getSanitizedName(data),
    role: data.role,
    x: typeof (data as any).fx === 'number' ? (data as any).fx : marginX,
    y: typeof (data as any).fy === 'number' ? (data as any).fy : height / 2,
    ref: data,
    depth: 0,
  };
  nodes.push(router);

  // Place nodes by depth
  const maxDepth = Math.max(...Array.from(nodesByDepth.keys()), 0);
  for (let depth = 1; depth <= maxDepth; depth++) {
    const nodesAtDepth = nodesByDepth.get(depth) || [];
    if (nodesAtDepth.length === 0) continue;

    const columnX = marginX + depth * columnWidth;
    const startY = centerColumnY(nodesAtDepth.length);

    nodesAtDepth.forEach((c, idx) => {
      const dev: DrawNode = {
        id: c.id,
        name: getSanitizedName(c),
        role: c.role,
        x: typeof (c as any).fx === 'number' ? (c as any).fx : columnX,
        y: typeof (c as any).fy === 'number' ? (c as any).fy : startY + idx * nodeGapY,
        ref: c,
        depth: depth,
      };
      nodes.push(dev);
    });
  }

  // Build id → DrawNode map
  const idToNode = new Map<string, DrawNode>();
  nodes.forEach((n) => {
    idToNode.set(n.id, n);
  });

  // Calculate bounding box of all nodes to center the view
  if (nodes.length > 0) {
    const minX = Math.min(...nodes.map((n) => n.x));
    const maxX = Math.max(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxY = Math.max(...nodes.map((n) => n.y));

    // Calculate the center of the network
    const networkCenterX = (minX + maxX) / 2;
    const networkCenterY = (minY + maxY) / 2;

    // Calculate translation to center the network in the viewport
    const translateX = width / 2 - networkCenterX;
    const translateY = height / 2 - networkCenterY;

    // Store as initial transform (only set once per data load)
    if (!initialTransform) {
      initialTransform = d3.zoomIdentity.translate(translateX, translateY);
      currentTransform = initialTransform;
    }
  }

  // Set up zoom behavior (after center is calculated)
  const zoom = d3
    .zoom<SVGSVGElement, unknown>()
    .scaleExtent([0.1, 4])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
      currentTransform = event.transform;
    });

  currentZoom = zoom;
  svg.call(zoom).call(zoom.transform, currentTransform);

  // Disable double-click zoom for cleaner experience
  svg.on('dblclick.zoom', null);

  // Build links based on parentId
  for (const n of nodes) {
    if (n.id === router.id) continue;
    const ref = n.ref as any;
    const parentId = ref?.parentId as string | undefined;

    let parent: DrawNode | undefined;
    if (parentId) {
      parent = idToNode.get(parentId);
    }

    if (!parent && n.depth === 1) {
      parent = router;
    }

    if (!parent && n.depth && n.depth > 1) {
      parent = router;
    }

    if (parent) {
      links.push({ source: parent, target: n });
    }
  }

  // Draw links (curved, horizontal routing)
  const linkPath = (s: DrawNode, t: DrawNode) => {
    const mx = (s.x + t.x) / 2;
    return `M${s.x},${s.y} C ${mx},${s.y} ${mx},${t.y} ${t.x},${t.y}`;
  };

  const getBezierAngle = (s: DrawNode, t: DrawNode) => {
    const dx = 0.75 * (t.x - s.x);
    const dy = 1.5 * (t.y - s.y);
    let angle = Math.atan2(dy, dx) * (180 / Math.PI);
    if (angle > 90 || angle < -90) {
      angle += 180;
    }
    return angle;
  };

  // Theme-aware colors (dark already defined at top of render)
  g.append('g')
    .selectAll('path.link')
    .data(links)
    .join('path')
    .attr('class', 'link animated-link')
    .attr('fill', 'none')
    .attr('stroke', dark ? '#38bdf8' : '#0ea5e9')
    .attr('stroke-width', 2)
    .attr('stroke-dasharray', '8,4')
    .attr('opacity', dark ? 0.6 : 0.5)
    .attr('d', (d: any) => linkPath(d.source, d.target));

  // Draw nodes
  const node = g
    .append('g')
    .selectAll('g.node')
    .data(nodes)
    .join('g')
    .attr('class', 'node')
    .attr('transform', (d: any) => `translate(${d.x},${d.y})`)
    .style('cursor', 'default');

  // Outer glow/halo for health status
  node
    .append('circle')
    .attr('r', 24)
    .attr('fill', (d: any) => {
      const status = getNodeHealthStatus(d.id, d.ref);
      return getStatusColor(status, dark);
    })
    .attr('opacity', 0.4);

  // Main node circle with shadow effect
  node
    .append('circle')
    .attr('r', 18)
    .attr('fill', dark ? '#0f172a' : '#ffffff')
    .attr('stroke', (d: any) => {
      switch (d.role) {
        case 'gateway/router':
          return '#ef4444';
        case 'firewall':
          return '#f97316';
        case 'switch/ap':
          return '#3b82f6';
        case 'server':
          return '#22c55e';
        case 'service':
          return '#10b981';
        case 'nas':
          return '#a855f7';
        case 'client':
          return '#06b6d4';
        default:
          return '#9ca3af';
      }
    })
    .attr('stroke-width', 3)
    .style(
      'filter',
      dark ? 'drop-shadow(0 3px 10px rgba(0,0,0,0.6))' : 'drop-shadow(0 2px 6px rgba(0,0,0,0.12))'
    );

  // Icon
  node
    .append('text')
    .attr('dy', '0.35em')
    .attr('text-anchor', 'middle')
    .attr('font-size', 18)
    .text((d: any) => roleIcon(d.role));

  // Label underneath node
  node
    .append('text')
    .attr('dy', '2.8em')
    .attr('text-anchor', 'middle')
    .attr('class', 'node-label')
    .attr('fill', dark ? '#cbd5e1' : '#1e293b')
    .attr('font-weight', '600')
    .attr('font-size', '11px')
    .text((d: any) => d.name);

  // Draw connection speed labels (speeds don't contain sensitive info, always show)
  const linksWithSpeed = links.filter((l: any) => {
    const speed = (l.target.ref as any)?.connectionSpeed;
    return speed && speed.trim().length > 0;
  });

  if (linksWithSpeed.length > 0) {
    const speedLabelGroup = g.append('g').attr('class', 'speed-labels');

    speedLabelGroup
      .selectAll('text.speed-label')
      .data(linksWithSpeed)
      .join('text')
      .attr('class', 'speed-label')
      .attr('x', (d: any) => (d.source.x + d.target.x) / 2)
      .attr('y', (d: any) => (d.source.y + d.target.y) / 2)
      .attr('text-anchor', 'middle')
      .attr('dy', '-0.5em')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('font-style', 'italic')
      .attr('fill', dark ? '#7dd3fc' : '#0369a1')
      .attr('opacity', dark ? 0.7 : 0.6)
      .attr('transform', (d: any) => {
        const angle = getBezierAngle(d.source, d.target);
        const centerX = (d.source.x + d.target.x) / 2;
        const centerY = (d.source.y + d.target.y) / 2;
        return `rotate(${angle}, ${centerX}, ${centerY})`;
      })
      .text((d: any) => (d.target.ref as any).connectionSpeed);
  }

  cleanup = () => {
    svg.selectAll('*').remove();
  };
}

// Exposed methods for zoom control
function zoomIn() {
  if (!svgRef.value || !currentZoom) return;
  const svg = d3.select(svgRef.value);
  svg.transition().duration(300).call(currentZoom.scaleBy, 1.3);
}

function zoomOut() {
  if (!svgRef.value || !currentZoom) return;
  const svg = d3.select(svgRef.value);
  svg.transition().duration(300).call(currentZoom.scaleBy, 0.7);
}

function resetView() {
  if (!svgRef.value || !currentZoom) return;
  const svg = d3.select(svgRef.value);

  // Use the calculated initial centered transform
  const resetTransform = initialTransform || d3.zoomIdentity;
  svg.transition().duration(500).call(currentZoom.transform, resetTransform);
}

defineExpose({
  zoomIn,
  zoomOut,
  resetView,
});

onMounted(() => {
  render();

  // Watch for resize
  const resizeObserver = new ResizeObserver(() => {
    render();
  });

  if (svgRef.value) {
    resizeObserver.observe(svgRef.value);
  }

  const originalCleanup = cleanup;
  cleanup = () => {
    resizeObserver.disconnect();
    if (originalCleanup) originalCleanup();
  };
});

onBeforeUnmount(() => {
  if (cleanup) cleanup();
});

watch(
  () => [props.data, props.sensitiveMode, props.isDark, props.healthMetrics],
  (newVal, oldVal) => {
    // Reset initial transform when data changes to recenter the view
    if (newVal[0] !== oldVal?.[0]) {
      initialTransform = null;
    }
    render();
  },
  { deep: true }
);
</script>

<style>
/* Animation for network links */
@keyframes link-flow {
  from {
    stroke-dashoffset: 12;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.animated-link {
  animation: link-flow 1s linear infinite;
}
</style>
