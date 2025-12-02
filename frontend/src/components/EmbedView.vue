<template>
	<div class="h-screen w-screen overflow-hidden bg-slate-100 dark:bg-slate-900 transition-colors">
		<!-- Loading State -->
		<div v-if="loading" class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg class="animate-spin h-12 w-12 text-cyan-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-slate-600 dark:text-slate-400">Loading Network Map...</p>
			</div>
		</div>

		<!-- Error State -->
		<div v-else-if="error" class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
				<p class="text-slate-700 dark:text-slate-300 text-lg font-medium mb-2">Unable to Load Map</p>
				<p class="text-slate-500 text-sm">{{ error }}</p>
			</div>
		</div>

		<!-- Network Map -->
		<div v-else-if="mapData" class="h-full w-full relative">
			<!-- Branding watermark -->
			<div class="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-200 dark:border-slate-700">
				<span class="text-sm font-medium text-slate-700 dark:text-slate-300">🗺️ Cartographer</span>
				<template v-if="showOwner && ownerDisplayName">
					<span class="text-slate-400 dark:text-slate-500">•</span>
					<span class="text-sm text-slate-500 dark:text-slate-400">{{ ownerDisplayName }}</span>
				</template>
			</div>
			
			<!-- Controls -->
			<div class="absolute bottom-3 right-3 z-10 flex flex-col gap-1">
				<!-- Theme toggle -->
				<button 
					@click="toggleTheme"
					class="p-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-white transition-colors"
					:title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
				>
					<!-- Sun icon (shown in dark mode) -->
					<svg v-if="isDark" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
					</svg>
					<!-- Moon icon (shown in light mode) -->
					<svg v-else xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
					</svg>
				</button>
				<div class="h-1"></div>
				<!-- Zoom controls -->
				<button 
					@click="zoomIn"
					class="p-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-white transition-colors"
					title="Zoom in"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
				</button>
				<button 
					@click="zoomOut"
					class="p-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-white transition-colors"
					title="Zoom out"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
					</svg>
				</button>
				<button 
					@click="resetView"
					class="p-2 bg-white/80 dark:bg-slate-800/80 backdrop-blur-sm rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-800 dark:hover:text-white transition-colors"
					title="Reset view"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
					</svg>
				</button>
			</div>

			<!-- Network Map Component -->
			<NetworkMapEmbed
				ref="networkMapRef"
				:data="mapData"
				:sensitiveMode="sensitiveMode"
				:isDark="isDark"
				:healthMetrics="cachedMetrics"
			/>
		</div>

		<!-- Empty State -->
		<div v-else class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-slate-400 dark:text-slate-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
				</svg>
				<p class="text-slate-500 dark:text-slate-400">No network map available</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';
import type { TreeNode } from '../types/network';
import NetworkMapEmbed from './NetworkMapEmbed.vue';
import { useHealthMonitoring } from '../composables/useHealthMonitoring';

const props = defineProps<{
	embedId: string;
}>();

const loading = ref(true);
const error = ref<string | null>(null);
const mapData = ref<TreeNode | null>(null);
const sensitiveMode = ref(false);
const showOwner = ref(false);
const ownerDisplayName = ref<string | null>(null);
const networkMapRef = ref<InstanceType<typeof NetworkMapEmbed> | null>(null);
const isDark = ref(true);

// Health monitoring
const { registerDevices, startPolling, stopPolling, cachedMetrics } = useHealthMonitoring();

// Helper to extract IPs from the tree
function extractIPs(node: TreeNode): string[] {
	const ips: string[] = [];
	const walk = (n: TreeNode) => {
		if (n.ip && n.role !== 'group' && n.monitoringEnabled !== false) {
			ips.push(n.ip);
		}
		for (const child of (n.children || [])) {
			walk(child);
		}
	};
	walk(node);
	return ips;
}

async function loadMapData() {
	loading.value = true;
	error.value = null;
	
	if (!props.embedId) {
		error.value = 'Invalid embed URL.';
		loading.value = false;
		return;
	}
	
	try {
		const response = await axios.get(`/api/embed-data/${props.embedId}`);
		if (response.data.exists && response.data.root) {
			mapData.value = response.data.root;
			sensitiveMode.value = response.data.sensitiveMode || false;
			showOwner.value = response.data.showOwner || false;
			ownerDisplayName.value = response.data.ownerDisplayName || null;
			
			// Register devices for health monitoring
			const ips = extractIPs(response.data.root);
			if (ips.length > 0) {
				await registerDevices(ips);
				// Start polling for health metrics updates
				startPolling(10000);
			}
		} else {
			error.value = 'No network map has been configured yet.';
		}
	} catch (err: any) {
		console.error('Failed to load embed data:', err);
		if (err?.response?.status === 404) {
			error.value = 'Embed not found.';
		} else {
			error.value = err?.response?.data?.detail || 'Failed to load network map data.';
		}
	} finally {
		loading.value = false;
	}
}

function zoomIn() {
	networkMapRef.value?.zoomIn();
}

function zoomOut() {
	networkMapRef.value?.zoomOut();
}

function resetView() {
	networkMapRef.value?.resetView();
}

function toggleTheme() {
	isDark.value = !isDark.value;
	if (isDark.value) {
		document.documentElement.classList.add('dark');
	} else {
		document.documentElement.classList.remove('dark');
	}
}

onMounted(() => {
	// Check for saved preference or system preference
	const savedTheme = localStorage.getItem('embed_theme');
	if (savedTheme) {
		isDark.value = savedTheme === 'dark';
	} else {
		// Default to system preference
		isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
	}
	
	// Apply theme
	if (isDark.value) {
		document.documentElement.classList.add('dark');
	} else {
		document.documentElement.classList.remove('dark');
	}
	
	loadMapData();
});

// Stop health polling when component unmounts
onBeforeUnmount(() => {
	stopPolling();
});
</script>

<style scoped>
/* Embed view specific styles */
</style>
