<template>
	<div class="h-screen w-screen overflow-hidden bg-slate-900">
		<!-- Loading State -->
		<div v-if="loading" class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg class="animate-spin h-12 w-12 text-cyan-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<p class="text-slate-400">Loading Network Map...</p>
			</div>
		</div>

		<!-- Error State -->
		<div v-else-if="error" class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-red-400 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
				<p class="text-slate-300 text-lg font-medium mb-2">Unable to Load Map</p>
				<p class="text-slate-500 text-sm">{{ error }}</p>
			</div>
		</div>

		<!-- Network Map -->
		<div v-else-if="mapData" class="h-full w-full relative">
			<!-- Branding watermark -->
			<div class="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-slate-800/80 backdrop-blur-sm rounded-lg px-3 py-2 border border-slate-700">
				<span class="text-sm font-medium text-slate-300">🗺️ Cartographer</span>
				<span v-if="sensitiveMode" class="text-xs text-amber-400 flex items-center gap-1">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
					</svg>
					Sensitive Mode
				</span>
			</div>
			
			<!-- Zoom controls -->
			<div class="absolute bottom-3 right-3 z-10 flex flex-col gap-1">
				<button 
					@click="zoomIn"
					class="p-2 bg-slate-800/80 backdrop-blur-sm rounded border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
					title="Zoom in"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
				</button>
				<button 
					@click="zoomOut"
					class="p-2 bg-slate-800/80 backdrop-blur-sm rounded border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
					title="Zoom out"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 12H4" />
					</svg>
				</button>
				<button 
					@click="resetView"
					class="p-2 bg-slate-800/80 backdrop-blur-sm rounded border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
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
			/>
		</div>

		<!-- Empty State -->
		<div v-else class="h-full flex items-center justify-center">
			<div class="text-center">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 text-slate-600 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
				</svg>
				<p class="text-slate-400">No network map available</p>
			</div>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import type { TreeNode } from '../types/network';
import NetworkMapEmbed from './NetworkMapEmbed.vue';

const props = defineProps<{
	sensitiveMode?: boolean;
}>();

const loading = ref(true);
const error = ref<string | null>(null);
const mapData = ref<TreeNode | null>(null);
const networkMapRef = ref<InstanceType<typeof NetworkMapEmbed> | null>(null);

async function loadMapData() {
	loading.value = true;
	error.value = null;
	
	try {
		const response = await axios.get('/api/embed-data');
		if (response.data.exists && response.data.root) {
			mapData.value = response.data.root;
		} else {
			error.value = 'No network map has been configured yet.';
		}
	} catch (err: any) {
		console.error('Failed to load embed data:', err);
		error.value = err?.response?.data?.detail || 'Failed to load network map data.';
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

onMounted(() => {
	// Force dark mode for embed view
	document.documentElement.classList.add('dark');
	loadMapData();
});
</script>

<style scoped>
/* Embed view specific styles */
</style>
