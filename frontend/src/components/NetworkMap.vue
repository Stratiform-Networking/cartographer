<template>
	<div class="w-full h-full relative">
		<!-- Gradient background using OKLCH color space for smoother interpolation -->
		<div class="absolute inset-0 rounded-lg overflow-hidden pointer-events-none network-map-bg">
			<!-- Light mode: Blur overlay -->
			<div class="absolute -inset-4 dark:hidden blur-xl"></div>
			<div 
				class="absolute inset-0 pointer-events-none hidden dark:block"
				style="background: linear-gradient(160deg, #05182f 0%, #020e20 50%, #03172d 100%); opacity: 0.5;"
			></div>
			<!-- Dark mode: Blur overlay -->
			<div class="absolute -inset-4 hidden dark:block blur-xl"></div>
			<!-- Blue noise dither overlay - prevents color banding -->
			<div class="absolute inset-0 blue-noise-dither"></div>
			<!-- Subtle radial accent glow -->
			<div class="absolute inset-0 opacity-40 dark:opacity-25" style="background: radial-gradient(ellipse 100% 80% at 50% 30%, rgba(56, 189, 248, 0.08) 0%, rgba(56, 189, 248, 0.02) 35%, transparent 55%)"></div>
			<!-- Bottom corner accent -->
			<div class="absolute inset-0 opacity-30 dark:opacity-15" style="background: radial-gradient(ellipse 60% 50% at 90% 90%, rgba(99, 102, 241, 0.06) 0%, rgba(99, 102, 241, 0.015) 35%, transparent 55%)"></div>
		</div>
		<!-- SVG with grid pattern that pans with content -->
		<svg ref="svgRef" class="relative w-full h-full rounded-lg border border-slate-200/60 dark:border-slate-800/60"></svg>
	</div>
</template>

<script lang="ts" setup>
import * as d3 from "d3";
import { onMounted, onBeforeUnmount, ref, watch, computed } from "vue";
import type { TreeNode, DeviceMetrics, HealthStatus } from "../types/network";
import { useMapLayout } from "../composables/useMapLayout";

const props = defineProps<{
	data: TreeNode;
	selectedId?: string;
	mode?: 'pan' | 'edit';
	healthMetrics?: Record<string, DeviceMetrics>;
}>();

// Get status color for health glow (using light fill colors like selection)
function getStatusColor(status?: HealthStatus, dark?: boolean): string {
	switch (status) {
		case 'healthy': return dark ? '#22c55e' : '#bbf7d0'; // green-500 / green-200
		case 'degraded': return dark ? '#f59e0b' : '#fde68a'; // amber-500 / amber-200
		case 'unhealthy': return dark ? '#ef4444' : '#fecaca'; // red-500 / red-200
		default: return 'none'; // unknown - no glow
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

const emit = defineEmits<{
	(e: "nodeSelected", id: string | undefined): void;
	(e: "nodePositionChanged", id: string, x: number, y: number): void;
}>();

const svgRef = ref<SVGSVGElement | null>(null);
const { updatePosition } = useMapLayout();

// Create a stable fingerprint of health statuses to avoid deep watch on healthMetrics
// This only changes when actual status values change, not on every poll response
const healthStatusFingerprint = computed(() => {
	if (!props.healthMetrics) return '';
	const entries = Object.entries(props.healthMetrics)
		.map(([ip, m]) => `${ip}:${m.status}`)
		.sort()
		.join('|');
	return entries;
});

let cleanup: (() => void) | null = null;
let currentTransform = d3.zoomIdentity.translate(24, 24);
let currentZoom: any = null;
let nodePositions = new Map<string, { x: number; y: number }>();

// Detect dark mode
const isDarkMode = () => document.documentElement.classList.contains('dark');

function roleClass(role?: string): string {
	if (!role) return "role-unknown";
	const map: Record<string, string> = {
		"gateway/router": "role-gateway",
		"switch/ap": "role-switch",
		"firewall": "role-firewall",
		"server": "role-server",
		"service": "role-service",
		"nas": "role-nas",
		"client": "role-client",
		"group": "role-unknown",
		"unknown": "role-unknown",
	};
	return map[role] || "role-unknown";
}

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

	function render() {
	const svg = d3.select(svgRef.value!);
	svg.selectAll("*").remove();

	const width = (svgRef.value?.clientWidth || 800);
	const height = (svgRef.value?.clientHeight || 600);
	const dark = isDarkMode();
	
	// Define grid pattern
	const defs = svg.append("defs");
	const gridSize = 24;
	const pattern = defs.append("pattern")
		.attr("id", "grid-pattern")
		.attr("width", gridSize)
		.attr("height", gridSize)
		.attr("patternUnits", "userSpaceOnUse");
	
	pattern.append("circle")
		.attr("cx", gridSize / 2)
		.attr("cy", gridSize / 2)
		.attr("r", 1)
		.attr("fill", dark ? "rgba(148, 163, 184, 0.15)" : "rgba(148, 163, 184, 0.35)");

	const g = svg.attr("viewBox", [0, 0, width, height].join(" ")).append("g").attr("class", "zoom-layer").attr("transform", "translate(24,24)");
	
	// Add grid background that pans with content (large enough for any pan/zoom)
	g.insert("rect", ":first-child")
		.attr("class", "grid-bg")
		.attr("x", -5000)
		.attr("y", -5000)
		.attr("width", 10000)
		.attr("height", 10000)
		.attr("fill", "url(#grid-pattern)");

	const zoom = d3.zoom<SVGSVGElement, unknown>()
		.scaleExtent([0.1, 4])
		.on("zoom", (event) => {
			g.attr("transform", event.transform);
			currentTransform = event.transform;
		});
	
	currentZoom = zoom;
	svg.call(zoom).call(zoom.transform, currentTransform);

	// Stop zoom propagation on nodes so dragging works
	svg.on("dblclick.zoom", null);

	// ─────────────────────────────────────────────────────────────────────────────
	// Depth-based layout (left → right)
	// Columns based on actual network depth from gateway (respecting parentId)
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
		if (visited.has(nodeId)) return 1; // Prevent infinite loops, treat as direct child
		visited.add(nodeId);
		
		const node = allNodesMap.get(nodeId);
		if (!node) return 1;
		
		const parentId = (node as any).parentId;
		if (!parentId || parentId === data.id) {
			return 1; // Direct connection to root
		}
		
		// Recursively get parent's depth
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

	// Sort nodes within each depth by parent position, then by IP address
	const parseIpForSorting = (ipStr: string): number[] => {
		const match = ipStr.match(/(\d+)\.(\d+)\.(\d+)\.(\d+)/);
		if (match) {
			return [
				parseInt(match[1]),
				parseInt(match[2]),
				parseInt(match[3]),
				parseInt(match[4])
			];
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
	
	// Sort each depth level, considering parent positions
	const maxDepthForSort = Math.max(...Array.from(nodesByDepth.keys()), 0);
	for (let depth = 1; depth <= maxDepthForSort; depth++) {
		const nodesAtDepth = nodesByDepth.get(depth) || [];
		if (nodesAtDepth.length === 0) continue;
		
		// Sort by: 1) parent's sort order, 2) IP address
		nodesAtDepth.sort((a, b) => {
			const parentIdA = (a as any).parentId || data.id;
			const parentIdB = (b as any).parentId || data.id;
			const parentOrderA = nodeSortOrder.get(parentIdA) ?? 999999;
			const parentOrderB = nodeSortOrder.get(parentIdB) ?? 999999;
			
			// First, compare by parent position
			if (parentOrderA !== parentOrderB) {
				return parentOrderA - parentOrderB;
			}
			
			// Within same parent group, sort by IP
			return compareIps(a, b);
		});
		
		// Record sort order for this depth (for next depth's sorting)
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
		name: data.name,
		role: data.role,
		x: typeof (data as any).fx === "number" ? (data as any).fx : marginX,
		y: typeof (data as any).fy === "number" ? (data as any).fy : (height / 2),
		ref: data,
		depth: 0,
	};
	if (typeof (data as any).fx !== "number" || typeof (data as any).fy !== "number") {
		(data as any).fx = router.x; (data as any).fy = router.y; updatePosition(router.id, router.x, router.y);
	}
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
				name: c.name,
				role: c.role,
				x: typeof (c as any).fx === "number" ? (c as any).fx : columnX,
				y: typeof (c as any).fy === "number" ? (c as any).fy : startY + idx * nodeGapY,
				ref: c,
				depth: depth,
			};
			if (typeof (c as any).fx !== "number" || typeof (c as any).fy !== "number") {
				(c as any).fx = dev.x; (c as any).fy = dev.y; updatePosition(c.id, dev.x, dev.y);
			}
			nodes.push(dev);
		});
	}

	// Build id → DrawNode map and store node positions
	const idToNode = new Map<string, DrawNode>();
	nodePositions.clear();
	nodes.forEach(n => {
		idToNode.set(n.id, n);
		nodePositions.set(n.id, { x: n.x, y: n.y });
	});

	// Build links based on parentId or default to router for depth-1 nodes
	for (const n of nodes) {
		if (n.id === router.id) continue;
		const ref = n.ref as any;
		const parentId = ref?.parentId as string | undefined;
		
		let parent: DrawNode | undefined;
		if (parentId) {
			parent = idToNode.get(parentId);
		}
		
		// If no explicit parent or parent not found, connect to router (for depth 1)
		if (!parent && n.depth === 1) {
			parent = router;
		}
		
		// For deeper nodes without parent, try to find a parent in the previous depth
		if (!parent && n.depth && n.depth > 1) {
			// Connect to router as fallback
			parent = router;
		}
		
		if (parent) {
			links.push({ source: parent, target: n });
		}
	}

	// Draw links (curved, horizontal routing - Unifi style)
	const linkPath = (s: DrawNode, t: DrawNode) => {
		const mx = (s.x + t.x) / 2;
		return `M${s.x},${s.y} C ${mx},${s.y} ${mx},${t.y} ${t.x},${t.y}`;
	};
	
	// Calculate the tangent angle at the midpoint of the bezier curve
	const getBezierAngle = (s: DrawNode, t: DrawNode) => {
		// Bezier control points: P0=(s.x,s.y), P1=(mx,s.y), P2=(mx,t.y), P3=(t.x,t.y)
		// Derivative at t=0.5: B'(0.5) = 0.75(P1-P0) + 1.5(P2-P1) + 0.75(P3-P2)
		// This simplifies to: dx = 0.75 * (t.x - s.x), dy = 1.5 * (t.y - s.y)
		const dx = 0.75 * (t.x - s.x);
		const dy = 1.5 * (t.y - s.y);
		
		let angle = Math.atan2(dy, dx) * (180 / Math.PI);
		
		// Keep text readable - flip if upside down
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
		.attr("stroke", dark ? "#38bdf8" : "#0ea5e9")
		.attr("stroke-width", 2)
		.attr("stroke-dasharray", "8,4")
		.attr("opacity", dark ? 0.6 : 0.5)
		.attr("d", (d: any) => linkPath(d.source, d.target));

	// Draw nodes
	const node = g.append("g")
		.selectAll("g.node")
		.data(nodes)
		.join("g")
		.attr("class", "node")
		.attr("transform", (d: any) => `translate(${d.x},${d.y})`)
		.style("cursor", "pointer")
		.on("click", (_, d: any) => emit("nodeSelected", d.id));

	// Outer glow/halo for status and selection
	node.append("circle")
		.attr("r", 24)
		.attr("fill", (d: any) => {
			// Selection takes priority
			if (d.id === props.selectedId) {
				return dark ? "#fbbf24" : "#fef3c7";
			}
			// Otherwise show health status
			const status = getNodeHealthStatus(d.id, d.ref);
			return getStatusColor(status, dark);
		})
		.attr("opacity", 0.4);

	// Main node circle with shadow effect
	node.append("circle")
		.attr("r", 18)
		.attr("fill", dark ? "#0f172a" : "white")
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
		.style("filter", dark ? "drop-shadow(0 3px 10px rgba(0,0,0,0.6))" : "drop-shadow(0 2px 6px rgba(0,0,0,0.12))");

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
		.attr("fill", dark ? "#cbd5e1" : "#1e293b")
		.attr("font-weight", "600")
		.attr("font-size", "11px")
		.text((d: any) => d.name);

	// Drag behavior (persist fx/fy) - only when in 'edit' mode
	if (props.mode === 'edit') {
		let dragStartX = 0;
		let dragStartY = 0;
		let hasDragged = false;
		const dragThreshold = 5; // pixels - movement below this is considered a click
		
		const drag = d3.drag<SVGGElement, any>()
			.on("start", function (event, d: any) {
				d3.select(this).raise();
				// Record starting position to detect if actual dragging occurred
				dragStartX = d.x;
				dragStartY = d.y;
				hasDragged = false;
			})
			.on("drag", function (event, d: any) {
				// Convert pointer to content coordinates accounting for zoom/pan
				const svgEl = svgRef.value as SVGSVGElement;
				const t = d3.zoomTransform(svgEl);
				const [sx, sy] = d3.pointer(event, svgEl);
				const [cx, cy] = t.invert([sx, sy]);
				
				// Check if movement exceeds threshold
				const dx = cx - dragStartX;
				const dy = cy - dragStartY;
				const distance = Math.sqrt(dx * dx + dy * dy);
				
				if (distance > dragThreshold) {
					hasDragged = true;
					d.x = cx; d.y = cy;
					d3.select(this).attr("transform", `translate(${d.x},${d.y})`);
					if (d.ref) { (d.ref as any).fx = d.x; (d.ref as any).fy = d.y; updatePosition(d.id, d.x, d.y); }
					// Update connected links
					g.selectAll("path.link").attr("d", (l: any) => linkPath(l.source, l.target));
					// Update speed label positions and angles
					g.selectAll("text.speed-label")
						.attr("x", (l: any) => (l.source.x + l.target.x) / 2)
						.attr("y", (l: any) => (l.source.y + l.target.y) / 2)
						.attr("transform", (l: any) => {
							const angle = getBezierAngle(l.source, l.target);
							const centerX = (l.source.x + l.target.x) / 2;
							const centerY = (l.source.y + l.target.y) / 2;
							return `rotate(${angle}, ${centerX}, ${centerY})`;
						});
				}
			})
			.on("end", function (_, d: any) {
				if (hasDragged) {
					// Notify parent that position changed for auto-save
					emit("nodePositionChanged", d.id, d.x, d.y);
				} else {
					// No significant drag movement - treat as a click to select
					emit("nodeSelected", d.id);
				}
			});
		node.call(drag as any);
	}

	// Draw connection speed labels (after nodes so they appear on top)
	const linksWithSpeed = links.filter((l: any) => {
		const speed = (l.target.ref as any)?.connectionSpeed;
		return speed && speed.trim().length > 0;
	});

	if (linksWithSpeed.length > 0) {
		// Add speed text labels (positioned above the line)
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
			.attr("fill", dark ? "#7dd3fc" : "#0369a1")
			.attr("opacity", dark ? 0.7 : 0.6)
			.attr("transform", (d: any) => {
				const angle = getBezierAngle(d.source, d.target);
				const centerX = (d.source.x + d.target.x) / 2;
				const centerY = (d.source.y + d.target.y) / 2;
				return `rotate(${angle}, ${centerX}, ${centerY})`;
			})
			.text((d: any) => (d.target.ref as any).connectionSpeed);
	}

	// Cleanup
	cleanup = () => {
		svg.selectAll("*").remove();
	};
}

// Function to zoom and pan to a specific node
function zoomToNode(nodeId: string) {
	if (!svgRef.value || !currentZoom) return;
	
	const pos = nodePositions.get(nodeId);
	if (!pos) return;
	
	const svg = d3.select(svgRef.value);
	const width = svgRef.value.clientWidth || 800;
	const height = svgRef.value.clientHeight || 600;
	
	// Calculate transform to center the node
	const scale = 1.5; // Zoom level
	const x = width / 2 - pos.x * scale;
	const y = height / 2 - pos.y * scale;
	
	// Animate the transition
	svg.transition()
		.duration(750)
		.call(currentZoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
}

// Navigation control functions
function zoomIn() {
	if (!svgRef.value || !currentZoom) return;
	const svg = d3.select(svgRef.value);
	svg.transition()
		.duration(300)
		.call(currentZoom.scaleBy, 1.4);
}

function zoomOut() {
	if (!svgRef.value || !currentZoom) return;
	const svg = d3.select(svgRef.value);
	svg.transition()
		.duration(300)
		.call(currentZoom.scaleBy, 0.7);
}

function resetView() {
	if (!svgRef.value || !currentZoom) return;
	const svg = d3.select(svgRef.value);
	svg.transition()
		.duration(500)
		.call(currentZoom.transform, d3.zoomIdentity.translate(24, 24));
}

function fitToView() {
	if (!svgRef.value || !currentZoom || nodePositions.size === 0) return;
	
	const svg = d3.select(svgRef.value);
	const width = svgRef.value.clientWidth || 800;
	const height = svgRef.value.clientHeight || 600;
	
	// Find bounds of all nodes
	let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
	nodePositions.forEach(pos => {
		minX = Math.min(minX, pos.x);
		minY = Math.min(minY, pos.y);
		maxX = Math.max(maxX, pos.x);
		maxY = Math.max(maxY, pos.y);
	});
	
	// Add padding
	const padding = 60;
	minX -= padding;
	minY -= padding;
	maxX += padding;
	maxY += padding;
	
	const contentWidth = maxX - minX;
	const contentHeight = maxY - minY;
	
	// Calculate scale to fit
	const scale = Math.min(
		width / contentWidth,
		height / contentHeight,
		2 // Max scale
	) * 0.9; // Leave some margin
	
	// Calculate translation to center
	const centerX = (minX + maxX) / 2;
	const centerY = (minY + maxY) / 2;
	const x = width / 2 - centerX * scale;
	const y = height / 2 - centerY * scale;
	
	svg.transition()
		.duration(500)
		.call(currentZoom.transform, d3.zoomIdentity.translate(x, y).scale(scale));
}

// Expose the zoom functions
defineExpose({
	zoomToNode,
	zoomIn,
	zoomOut,
	resetView,
	fitToView
});

onMounted(() => {
	render();
	
	// Watch for dark mode changes
	const observer = new MutationObserver(() => {
		render();
	});
	
	observer.observe(document.documentElement, {
		attributes: true,
		attributeFilter: ['class']
	});
	
	// Cleanup observer
	const originalCleanup = cleanup;
	cleanup = () => {
		observer.disconnect();
		if (originalCleanup) originalCleanup();
	};
});

onBeforeUnmount(() => {
	if (cleanup) cleanup();
});

// Watch for structural changes that require full re-render (data tree structure)
watch(() => props.data, () => {
	render();
}, { deep: true });

// Watch for selection and mode changes (shallow comparison is sufficient)
watch(() => [props.selectedId, props.mode], () => {
	render();
});

// Watch health status fingerprint - only re-renders when actual status values change
// This prevents expensive re-renders on every health poll when statuses haven't changed
watch(healthStatusFingerprint, () => {
	render();
});
</script>

<style>
/* Animation for network links - flow from parent to child */
@keyframes link-flow {
	from {
		stroke-dashoffset: 12;
	}
	to {
		stroke-dashoffset: 0;
	}
}

/* Apply animation to links (not scoped so D3 can use it) */
.animated-link {
	animation: link-flow 1s linear infinite;
}
</style>


