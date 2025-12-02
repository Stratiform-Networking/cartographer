<template>
	<div class="w-full h-full">
		<svg ref="svgRef" class="w-full h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"></svg>
	</div>
</template>

<script lang="ts" setup>
import * as d3 from "d3";
import { onMounted, onBeforeUnmount, ref, watch } from "vue";
import type { TreeNode } from "../types/network";

const props = defineProps<{
	data: TreeNode;
	sensitiveMode?: boolean;
}>();

const svgRef = ref<SVGSVGElement | null>(null);

let cleanup: (() => void) | null = null;
let currentTransform = d3.zoomIdentity.translate(24, 24);
let currentZoom: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;

function roleIcon(role?: string): string {
	const r = role || "unknown";
	switch (r) {
		case "gateway/router": return "📡";
		case "firewall": return "🧱";
		case "switch/ap": return "🔀";
		case "server": return "🖥️";
		case "service": return "⚙️";
		case "nas": return "🗄️";
		case "client": return "💻";
		default: return "❓";
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
	const roleName = role === 'gateway/router' ? 'Gateway' 
		: role === 'switch/ap' ? 'Switch/AP'
		: role === 'firewall' ? 'Firewall'
		: role === 'server' ? 'Server'
		: role === 'service' ? 'Service'
		: role === 'nas' ? 'NAS'
		: role === 'client' ? 'Client'
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
	svg.selectAll("*").remove();

	const width = (svgRef.value?.clientWidth || 800);
	const height = (svgRef.value?.clientHeight || 600);

	const g = svg.attr("viewBox", [0, 0, width, height].join(" ")).append("g").attr("class", "zoom-layer").attr("transform", "translate(24,24)");

	const zoom = d3.zoom<SVGSVGElement, unknown>()
		.scaleExtent([0.1, 4])
		.on("zoom", (event) => {
			g.attr("transform", event.transform);
			currentTransform = event.transform;
		});
	
	currentZoom = zoom;
	svg.call(zoom).call(zoom.transform, currentTransform);

	// Disable double-click zoom for cleaner experience
	svg.on("dblclick.zoom", null);

	// ─────────────────────────────────────────────────────────────────────────────
	// Depth-based layout (left → right)
	// ─────────────────────────────────────────────────────────────────────────────
	const data = props.data;
	const children = data.children || [];

	type DrawNode = { id: string; name: string; role?: string; x: number; y: number; ref?: TreeNode; depth?: number; };
	type DrawLink = { source: DrawNode; target: DrawNode; };

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
		for (const c of (g.children || [])) {
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
		for (const c of (g.children || [])) {
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
	const parseIpForSorting = (ipStr: string): number[] => {
		const match = ipStr.match(/(\d+)\.(\d+)\.(\d+)\.(\d+)/);
		if (match) {
			return [parseInt(match[1]), parseInt(match[2]), parseInt(match[3]), parseInt(match[4])];
		}
		return [0, 0, 0, 0];
	};
	
	const compareIps = (a: TreeNode, b: TreeNode): number => {
		const ipA = (a as any).ip || a.id;
		const ipB = (b as any).ip || b.id;
		const partsA = parseIpForSorting(ipA);
		const partsB = parseIpForSorting(ipB);
		
		for (let i = 0; i < 4; i++) {
			if (partsA[i] !== partsB[i]) {
				return partsA[i] - partsB[i];
			}
		}
		return 0;
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
		x: typeof (data as any).fx === "number" ? (data as any).fx : marginX,
		y: typeof (data as any).fy === "number" ? (data as any).fy : (height / 2),
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
				x: typeof (c as any).fx === "number" ? (c as any).fx : columnX,
				y: typeof (c as any).fy === "number" ? (c as any).fy : startY + idx * nodeGapY,
				ref: c,
				depth: depth,
			};
			nodes.push(dev);
		});
	}

	// Build id → DrawNode map
	const idToNode = new Map<string, DrawNode>();
	nodes.forEach(n => {
		idToNode.set(n.id, n);
	});

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

	g.append("g")
		.selectAll("path.link")
		.data(links)
		.join("path")
		.attr("class", "link animated-link")
		.attr("fill", "none")
		.attr("stroke", "#60a5fa")
		.attr("stroke-width", 2)
		.attr("stroke-dasharray", "8,4")
		.attr("opacity", 0.8)
		.attr("d", (d: any) => linkPath(d.source, d.target));

	// Draw nodes
	const node = g.append("g")
		.selectAll("g.node")
		.data(nodes)
		.join("g")
		.attr("class", "node")
		.attr("transform", (d: any) => `translate(${d.x},${d.y})`)
		.style("cursor", "default");

	// Main node circle with shadow effect
	node.append("circle")
		.attr("r", 18)
		.attr("fill", "#1e293b")
		.attr("stroke", (d: any) => {
			switch (d.role) {
				case "gateway/router": return "#ef4444";
				case "firewall": return "#f97316";
				case "switch/ap": return "#3b82f6";
				case "server": return "#22c55e";
				case "service": return "#10b981";
				case "nas": return "#a855f7";
				case "client": return "#06b6d4";
				default: return "#9ca3af";
			}
		})
		.attr("stroke-width", 3)
		.style("filter", "drop-shadow(0 2px 8px rgba(0,0,0,0.5))");

	// Icon
	node.append("text")
		.attr("dy", "0.35em")
		.attr("text-anchor", "middle")
		.attr("font-size", 18)
		.text((d: any) => roleIcon(d.role));

	// Label underneath node
	node.append("text")
		.attr("dy", "2.8em")
		.attr("text-anchor", "middle")
		.attr("class", "node-label")
		.attr("fill", "#e2e8f0")
		.attr("font-weight", "500")
		.attr("font-size", "11px")
		.text((d: any) => d.name);

	// Draw connection speed labels (only if not in sensitive mode)
	if (!props.sensitiveMode) {
		const linksWithSpeed = links.filter((l: any) => {
			const speed = (l.target.ref as any)?.connectionSpeed;
			return speed && speed.trim().length > 0;
		});

		if (linksWithSpeed.length > 0) {
			const speedLabelGroup = g.append("g").attr("class", "speed-labels");
			
			speedLabelGroup.selectAll("text.speed-label")
				.data(linksWithSpeed)
				.join("text")
				.attr("class", "speed-label")
				.attr("x", (d: any) => (d.source.x + d.target.x) / 2)
				.attr("y", (d: any) => (d.source.y + d.target.y) / 2)
				.attr("text-anchor", "middle")
				.attr("dy", "-0.5em")
				.attr("font-size", "10px")
				.attr("font-weight", "600")
				.attr("font-style", "italic")
				.attr("fill", "#93c5fd")
				.attr("opacity", 0.8)
				.attr("transform", (d: any) => {
					const angle = getBezierAngle(d.source, d.target);
					const centerX = (d.source.x + d.target.x) / 2;
					const centerY = (d.source.y + d.target.y) / 2;
					return `rotate(${angle}, ${centerX}, ${centerY})`;
				})
				.text((d: any) => (d.target.ref as any).connectionSpeed);
		}
	}

	cleanup = () => {
		svg.selectAll("*").remove();
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
	const width = svgRef.value.clientWidth || 800;
	const height = svgRef.value.clientHeight || 600;
	
	svg.transition()
		.duration(500)
		.call(currentZoom.transform, d3.zoomIdentity.translate(24, 24));
}

defineExpose({
	zoomIn,
	zoomOut,
	resetView
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

watch(() => [props.data, props.sensitiveMode], () => {
	render();
}, { deep: true });
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
