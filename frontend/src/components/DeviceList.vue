<template>
	<div class="h-full flex flex-col">
		<!-- Header -->
		<div class="flex items-center gap-2 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
			</svg>
			<h2 class="font-semibold text-slate-800 dark:text-slate-100">Devices</h2>
			<span class="ml-auto text-xs text-slate-500 dark:text-slate-400 tabular-nums">{{ filtered.length }}</span>
		</div>
		
		<!-- Search -->
		<div class="p-3 border-b border-slate-200 dark:border-slate-700">
			<div class="relative">
				<svg xmlns="http://www.w3.org/2000/svg" class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<input
					v-model="query"
					type="text"
					placeholder="Search devices..."
					class="w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 pl-9 pr-3 py-2 text-sm focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-shadow"
				/>
			</div>
		</div>
		
		<!-- Device List -->
		<div class="flex-1 overflow-auto">
			<ul class="divide-y divide-slate-100 dark:divide-slate-700/50">
				<li
					v-for="d in filtered"
					:key="d.id"
					@click="$emit('select', d.id)"
					class="px-4 py-2.5 hover:bg-slate-100 dark:hover:bg-slate-700/50 cursor-pointer flex items-center gap-3 transition-colors"
					:class="[
						d.id === selectedId 
							? 'bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500' 
							: getStatusBackground(d)
					]"
				>
					<span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :class="roleDot(d.role)"></span>
					<div class="min-w-0 flex-1">
						<div class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{{ d.name }}</div>
						<div class="text-xs text-slate-500 dark:text-slate-400 capitalize">{{ d.role?.replace('/', ' / ') }}</div>
					</div>
				</li>
			</ul>
			
			<!-- Empty State -->
			<div v-if="filtered.length === 0 && query" class="p-6 text-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 mx-auto mb-2 text-slate-300 dark:text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				<p class="text-sm text-slate-500 dark:text-slate-400">No devices found</p>
				<p class="text-xs text-slate-400 dark:text-slate-500 mt-1">Try a different search term</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import type { TreeNode } from "../types/network";
import { useHealthMonitoring } from "../composables/useHealthMonitoring";

const props = defineProps<{
	root: TreeNode;
	selectedId?: string;
}>();

defineEmits<{
	(e: "select", id: string): void;
}>();

const { cachedMetrics, monitoringStatus } = useHealthMonitoring();

const query = ref("");

function flatten(root: TreeNode): TreeNode[] {
	const res: TreeNode[] = [];
	const walk = (n: TreeNode, isRoot = false) => {
		// Don't add the root itself to the list
		if (!isRoot) {
			res.push(n);
		}
		for (const c of n.children || []) walk(c, false);
	};
	walk(root, true);
	return res.filter(n => n.role !== "group");
}

// Sort nodes by depth, parent position, and IP address (matching map layout)
function sortByDepthAndIP(nodes: TreeNode[], root: TreeNode): TreeNode[] {
	// Build a map of all nodes
	const allNodesMap = new Map<string, TreeNode>();
	nodes.forEach(n => allNodesMap.set(n.id, n));
	
	// Calculate depth for each node based on parentId chain
	const getDepth = (nodeId: string, visited = new Set<string>()): number => {
		if (nodeId === root.id) return 0;
		if (visited.has(nodeId)) return 1; // Prevent infinite loops
		visited.add(nodeId);
		
		const node = allNodesMap.get(nodeId);
		if (!node) return 1;
		
		const parentId = (node as any).parentId;
		if (!parentId || parentId === root.id) {
			return 1; // Direct connection to root
		}
		
		// Recursively get parent's depth
		return getDepth(parentId, visited) + 1;
	};
	
	// Group nodes by depth
	const nodesByDepth = new Map<number, TreeNode[]>();
	nodes.forEach(node => {
		const depth = getDepth(node.id);
		if (!nodesByDepth.has(depth)) {
			nodesByDepth.set(depth, []);
		}
		nodesByDepth.get(depth)!.push(node);
	});
	
	// Parse IP address for sorting
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
	nodeSortOrder.set(root.id, 0);
	
	// Sort each depth level, considering parent positions
	const maxDepth = Math.max(...Array.from(nodesByDepth.keys()), 0);
	for (let depth = 0; depth <= maxDepth; depth++) {
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
			return compareIps(a, b);
		});
		
		// Record sort order for this depth (for next depth's sorting)
		nodesAtDepth.forEach((node, index) => {
			nodeSortOrder.set(node.id, index);
		});
	}
	
	// Flatten back to array in sorted order
	const sorted: TreeNode[] = [];
	for (let depth = 0; depth <= maxDepth; depth++) {
		const nodesAtDepth = nodesByDepth.get(depth) || [];
		sorted.push(...nodesAtDepth);
	}
	
	return sorted;
}

const all = computed(() => sortByDepthAndIP(flatten(props.root), props.root));
const filtered = computed(() => {
	const q = query.value.trim().toLowerCase();
	if (!q) return all.value;
	// Filter but maintain the sorted order
	return all.value.filter(n =>
		(n.name?.toLowerCase()?.includes(q)) ||
		(n.role || "").toLowerCase().includes(q) ||
		(n.ip || "").toLowerCase().includes(q) ||
		(n.hostname || "").toLowerCase().includes(q),
	);
});

function roleDot(role?: string) {
	switch (role) {
		case "gateway/router": return "bg-red-500";
		case "switch/ap": return "bg-blue-500";
		case "firewall": return "bg-orange-500";
		case "server": return "bg-green-500";
		case "service": return "bg-emerald-500";
		case "nas": return "bg-purple-500";
		case "client": return "bg-cyan-500";
		default: return "bg-gray-400";
	}
}

// Get status background class for monitored devices
function getStatusBackground(node: TreeNode): string {
	const ip = (node as any).ip;
	if (!ip) return '';
	
	// Check if device is in the actively monitored list
	const isMonitored = monitoringStatus.value?.monitored_devices?.includes(ip);
	if (!isMonitored) return ''; // Not monitored - leave default
	
	const metrics = cachedMetrics.value?.[ip];
	if (!metrics) return ''; // No metrics yet
	
	switch (metrics.status) {
		case 'healthy': return 'bg-emerald-50 dark:bg-emerald-900/20';
		case 'degraded': return 'bg-amber-50 dark:bg-amber-900/20';
		case 'unhealthy': return 'bg-red-50 dark:bg-red-900/20';
		default: return '';
	}
}
</script>


