<template>
	<aside 
		class="w-96 border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col overflow-hidden"
	>
		<!-- Header -->
		<div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
			<div class="flex items-center gap-2 min-w-0">
				<span class="text-lg">{{ roleIcon(node?.role) }}</span>
				<div class="min-w-0">
					<h2 class="font-semibold text-slate-800 dark:text-slate-100 truncate">{{ node?.hostname || node?.name }}</h2>
					<p class="text-xs text-slate-500 dark:text-slate-400 font-mono">{{ node?.ip || node?.id }}</p>
				</div>
			</div>
			<button 
				@click="$emit('close')"
				class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 flex-shrink-0"
				title="Close panel"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-auto">
			<!-- Health Status Banner -->
			<div 
				class="px-4 py-3 border-b border-slate-200 dark:border-slate-700"
				:class="statusBannerClass"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 rounded-full animate-pulse" :class="statusDotClass"></div>
						<span class="font-medium text-sm">{{ statusLabel }}</span>
					</div>
					<button 
						@click="refreshHealth"
						:disabled="loading"
						class="p-1.5 rounded hover:bg-white/20 dark:hover:bg-black/20 transition-colors disabled:opacity-50"
						title="Refresh health data"
					>
						<svg 
							xmlns="http://www.w3.org/2000/svg" 
							class="h-4 w-4" 
							:class="{ 'animate-spin': loading }"
							fill="none" 
							viewBox="0 0 24 24" 
							stroke="currentColor" 
							stroke-width="2"
						>
							<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
					</button>
				</div>
				<p v-if="metrics?.last_check" class="text-xs opacity-75 mt-1">
					Last checked: {{ formatTimestamp(metrics.last_check) }}
				</p>
			</div>

			<!-- Loading State -->
			<div v-if="loading && !metrics" class="p-8 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400">
				<svg class="animate-spin h-8 w-8 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-sm">Checking device health...</p>
			</div>

			<!-- Metrics Content (also shown when offline) -->
			<div v-if="metrics || isOffline" class="p-4 space-y-4">
				<!-- Offline Notice -->
				<div v-if="isOffline" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
					<div class="flex items-start gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
						</svg>
						<div>
							<p class="text-sm font-medium text-red-800 dark:text-red-200">Unable to reach device</p>
							<p class="text-xs text-red-600 dark:text-red-400 mt-1">{{ error }}</p>
						</div>
					</div>
				</div>

				<!-- Ping Metrics -->
				<section v-if="metrics?.ping">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Connectivity</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div class="grid grid-cols-2 gap-3">
							<MetricCard 
								label="Latency" 
								:value="formatLatency(metrics.ping.avg_latency_ms)"
								:sublabel="metrics.ping.min_latency_ms && metrics.ping.max_latency_ms 
									? `${metrics.ping.min_latency_ms.toFixed(1)} - ${metrics.ping.max_latency_ms.toFixed(1)} ms`
									: undefined"
								:status="getLatencyStatus(metrics.ping.avg_latency_ms)"
							/>
							<MetricCard 
								label="Packet Loss" 
								:value="`${metrics.ping.packet_loss_percent.toFixed(1)}%`"
								:status="getPacketLossStatus(metrics.ping.packet_loss_percent)"
							/>
						</div>
						<div v-if="metrics.ping.jitter_ms != null" class="pt-2 border-t border-slate-200 dark:border-slate-700">
							<div class="flex items-center justify-between">
								<span class="text-xs text-slate-500 dark:text-slate-400">Jitter</span>
								<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.ping.jitter_ms.toFixed(2) }} ms</span>
							</div>
						</div>
					</div>
				</section>

				<!-- 24h Statistics -->
				<section v-if="metrics?.uptime_percent_24h != null || metrics?.avg_latency_24h_ms != null">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">24h Statistics</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-3">
						<div v-if="metrics.uptime_percent_24h != null" class="space-y-1">
							<div class="flex items-center justify-between">
								<span class="text-xs text-slate-500 dark:text-slate-400">Uptime</span>
								<span class="text-sm font-medium" :class="getUptimeColor(metrics.uptime_percent_24h)">
									{{ metrics.uptime_percent_24h.toFixed(1) }}%
								</span>
							</div>
							<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
								<div 
									class="h-full rounded-full transition-all duration-500"
									:class="getUptimeBarColor(metrics.uptime_percent_24h)"
									:style="{ width: `${metrics.uptime_percent_24h}%` }"
								></div>
							</div>
						</div>
						<div v-if="metrics.avg_latency_24h_ms != null" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Avg Latency (24h)</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.avg_latency_24h_ms.toFixed(1) }} ms</span>
						</div>
						<div class="flex items-center justify-between text-xs">
							<span class="text-slate-500 dark:text-slate-400">Checks</span>
							<span class="space-x-2">
								<span class="text-emerald-600 dark:text-emerald-400">{{ metrics.checks_passed_24h }} passed</span>
								<span class="text-slate-400">/</span>
								<span class="text-red-600 dark:text-red-400">{{ metrics.checks_failed_24h }} failed</span>
							</span>
						</div>
					</div>
				</section>

				<!-- DNS Information -->
				<section v-if="metrics?.dns">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">DNS</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div v-if="metrics.dns.reverse_dns" class="flex items-start justify-between gap-2">
							<span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">Reverse DNS</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 text-right break-all">{{ metrics.dns.reverse_dns }}</span>
						</div>
						<div v-if="metrics.dns.resolved_hostname" class="flex items-start justify-between gap-2">
							<span class="text-xs text-slate-500 dark:text-slate-400 flex-shrink-0">Hostname</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 text-right break-all">{{ metrics.dns.resolved_hostname }}</span>
						</div>
						<div v-if="metrics.dns.resolution_time_ms" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Resolution Time</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ metrics.dns.resolution_time_ms.toFixed(1) }} ms</span>
						</div>
						<div v-if="!metrics.dns.success && !metrics.dns.reverse_dns && !metrics.dns.resolved_hostname" class="text-xs text-slate-500 dark:text-slate-400 italic">
							No DNS records found
						</div>
					</div>
				</section>

				<!-- Open Ports -->
				<section v-if="metrics?.open_ports && metrics.open_ports.length > 0">
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Open Ports</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg overflow-hidden">
						<div 
							v-for="port in metrics.open_ports" 
							:key="port.port"
							class="flex items-center justify-between px-3 py-2 border-b border-slate-200 dark:border-slate-700 last:border-b-0"
						>
							<div class="flex items-center gap-2">
								<span class="w-2 h-2 rounded-full bg-emerald-400"></span>
								<span class="text-sm font-mono text-slate-700 dark:text-slate-300">{{ port.port }}</span>
								<span v-if="port.service" class="text-xs text-slate-500 dark:text-slate-400">{{ port.service }}</span>
							</div>
							<span v-if="port.response_time_ms" class="text-xs text-slate-500 dark:text-slate-400">
								{{ port.response_time_ms.toFixed(0) }}ms
							</span>
						</div>
					</div>
				</section>

				<!-- Device Info -->
				<section>
					<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Device Info</h3>
					<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Role</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300 capitalize">{{ node?.role?.replace('/', ' / ') || 'Unknown' }}</span>
						</div>
						<div v-if="node?.connectionSpeed" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Connection Speed</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ node.connectionSpeed }}</span>
						</div>
						<div v-if="metrics?.last_seen_online" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Last Seen Online</span>
							<span class="text-sm font-medium text-slate-700 dark:text-slate-300">{{ formatTimestamp(metrics.last_seen_online) }}</span>
						</div>
						<div v-if="metrics?.consecutive_failures && metrics.consecutive_failures > 0" class="flex items-center justify-between">
							<span class="text-xs text-slate-500 dark:text-slate-400">Consecutive Failures</span>
							<span class="text-sm font-medium text-red-600 dark:text-red-400">{{ metrics.consecutive_failures }}</span>
						</div>
					</div>
				</section>
			</div>

			<!-- No IP Warning -->
			<div v-else-if="!node?.ip" class="p-8 flex flex-col items-center justify-center text-slate-500 dark:text-slate-400">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
				</svg>
				<p class="text-sm text-center">No IP address assigned</p>
				<p class="text-xs mt-1 text-center">Add an IP address to enable health monitoring</p>
			</div>
		</div>

		<!-- Scan Ports Button -->
		<div v-if="node?.ip && metrics && !metrics.open_ports?.length" class="p-3 border-t border-slate-200 dark:border-slate-700">
			<button
				@click="scanPorts"
				:disabled="scanningPorts"
				class="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
			>
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" :class="{ 'animate-spin': scanningPorts }" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				{{ scanningPorts ? 'Scanning...' : 'Scan Ports' }}
			</button>
		</div>
	</aside>
</template>

<script lang="ts" setup>
import { ref, watch, computed, onMounted } from 'vue';
import axios from 'axios';
import type { TreeNode, DeviceMetrics, HealthStatus } from '../types/network';
import MetricCard from './MetricCard.vue';

const props = defineProps<{
	node?: TreeNode;
}>();

const emit = defineEmits<{
	(e: 'close'): void;
}>();

const metrics = ref<DeviceMetrics | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const scanningPorts = ref(false);

// True when we couldn't reach the node (connection error)
const isOffline = computed(() => !!error.value && !!props.node?.ip);

const statusLabel = computed(() => {
	if (isOffline.value) return 'Offline (Unreachable)';
	if (!metrics.value) return 'Unknown';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'Online';
		case 'degraded': return 'Degraded';
		case 'unhealthy': return 'Offline';
		default: return 'Unknown';
	}
});

const statusBannerClass = computed(() => {
	if (isOffline.value) return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
	if (!metrics.value) return 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200';
		case 'degraded': return 'bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200';
		case 'unhealthy': return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
		default: return 'bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400';
	}
});

const statusDotClass = computed(() => {
	if (isOffline.value) return 'bg-red-500';
	if (!metrics.value) return 'bg-slate-400';
	const status = metrics.value.status;
	switch (status) {
		case 'healthy': return 'bg-emerald-500';
		case 'degraded': return 'bg-amber-500';
		case 'unhealthy': return 'bg-red-500';
		default: return 'bg-slate-400';
	}
});

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

function formatTimestamp(isoString: string): string {
	const date = new Date(isoString);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMs / 3600000);
	const diffDays = Math.floor(diffMs / 86400000);
	
	if (diffMins < 1) return 'Just now';
	if (diffMins < 60) return `${diffMins}m ago`;
	if (diffHours < 24) return `${diffHours}h ago`;
	if (diffDays < 7) return `${diffDays}d ago`;
	
	return date.toLocaleDateString(undefined, { 
		month: 'short', 
		day: 'numeric',
		hour: '2-digit',
		minute: '2-digit'
	});
}

function formatLatency(ms?: number): string {
	if (ms === undefined || ms === null) return '—';
	if (ms < 1) return '<1 ms';
	return `${ms.toFixed(1)} ms`;
}

function getLatencyStatus(ms?: number): 'good' | 'warning' | 'bad' {
	if (ms === undefined || ms === null) return 'bad';
	if (ms < 50) return 'good';
	if (ms < 150) return 'warning';
	return 'bad';
}

function getPacketLossStatus(percent: number): 'good' | 'warning' | 'bad' {
	if (percent === 0) return 'good';
	if (percent < 5) return 'warning';
	return 'bad';
}

function getUptimeColor(percent: number): string {
	if (percent >= 99) return 'text-emerald-600 dark:text-emerald-400';
	if (percent >= 95) return 'text-amber-600 dark:text-amber-400';
	return 'text-red-600 dark:text-red-400';
}

function getUptimeBarColor(percent: number): string {
	if (percent >= 99) return 'bg-emerald-500';
	if (percent >= 95) return 'bg-amber-500';
	return 'bg-red-500';
}

async function fetchHealth(includePorts = false) {
	const ip = props.node?.ip;
	if (!ip) return;
	
	loading.value = true;
	error.value = null;
	
	try {
		// Call the backend proxy which forwards to health service
		const response = await axios.get<DeviceMetrics>(
			`/api/health/check/${ip}`,
			{ 
				params: { 
					include_ports: includePorts,
					include_dns: true
				},
				timeout: 30000 
			}
		);
		metrics.value = response.data;
	} catch (err: any) {
		console.error('Health check failed:', err);
		error.value = err.response?.data?.detail || err.message || 'Failed to connect to health service';
	} finally {
		loading.value = false;
	}
}

async function refreshHealth() {
	await fetchHealth(false);
}

async function scanPorts() {
	scanningPorts.value = true;
	try {
		await fetchHealth(true);
	} finally {
		scanningPorts.value = false;
	}
}

// Fetch health when node changes
watch(() => props.node?.ip, (newIp, oldIp) => {
	if (newIp && newIp !== oldIp) {
		metrics.value = null;
		fetchHealth();
	}
}, { immediate: true });
</script>

