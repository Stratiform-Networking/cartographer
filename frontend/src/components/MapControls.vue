<template>
	<div class="flex items-center justify-between gap-4 p-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
		<!-- Left side: Branding -->
		<div class="flex items-center gap-2">
			<h1 class="text-lg font-semibold text-slate-800 dark:text-slate-100">🗺️ Cartographer</h1>
		</div>

		<!-- Right side: Buttons and message -->
		<div class="flex items-center gap-2">
			<div class="text-xs text-slate-500 dark:text-slate-400 min-w-28">
				<span v-if="message">{{ message }}</span>
			</div>
			<button @click="runMapper" class="px-3 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-500 disabled:opacity-50" :disabled="loading">
				<span v-if="!loading">Run Mapper</span>
				<span v-else>Running…</span>
			</button>
			<button @click="saveLayout" class="px-3 py-2 rounded bg-emerald-600 text-white text-sm hover:bg-emerald-500 disabled:opacity-50 flex items-center gap-2" :disabled="!props.root.children?.length || !props.hasUnsavedChanges || saving">
				<svg v-if="saving" class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
				</svg>
				<span v-if="!saving">Save Map</span>
				<span v-else>Saving…</span>
			</button>
			<button @click="exportJSON" class="px-3 py-2 rounded bg-purple-600 text-white text-sm hover:bg-purple-500" :disabled="!props.root.children?.length">
				Export JSON
			</button>
			<label class="px-3 py-2 rounded bg-slate-700 text-white text-sm hover:bg-slate-600 cursor-pointer">
				Import JSON
				<input type="file" accept="application/json" class="hidden" @change="onLoadFile" />
			</label>
			<button @click="cleanUpLayout" class="px-3 py-2 rounded bg-amber-600 text-white text-sm hover:bg-amber-500">
				Clean Up
			</button>
			<div class="border-l border-slate-300 dark:border-slate-600 h-8 mx-1"></div>
			<!-- Health Monitoring Settings -->
			<div class="relative">
				<button 
					@click="showHealthSettings = !showHealthSettings" 
					class="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 flex items-center gap-1"
					:class="{ 'bg-slate-100 dark:bg-slate-700': showHealthSettings }"
					title="Health monitoring settings"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
					</svg>
				</button>
				<!-- Dropdown -->
				<div 
					v-if="showHealthSettings" 
					class="absolute right-0 top-full mt-1 w-72 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-50 p-4"
				>
					<h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-3">Health Monitoring</h3>
					
					<!-- Enable/Disable -->
					<div class="flex items-center justify-between mb-3">
						<span class="text-xs text-slate-600 dark:text-slate-400">Passive Monitoring</span>
						<button 
							@click="toggleMonitoring"
							class="relative w-11 h-6 rounded-full transition-colors"
							:class="healthConfig.enabled ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'"
						>
							<span 
								class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
								:class="healthConfig.enabled ? 'translate-x-5' : 'translate-x-0'"
							></span>
						</button>
					</div>
					
					<!-- Check Interval -->
					<div class="mb-3">
						<label class="text-xs text-slate-600 dark:text-slate-400 block mb-1">Check Interval</label>
						<select 
							v-model="healthConfig.check_interval_seconds"
							@change="updateHealthConfig"
							class="w-full text-sm border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-2 py-1"
						>
							<option :value="10">10 seconds</option>
							<option :value="30">30 seconds</option>
							<option :value="60">1 minute</option>
							<option :value="120">2 minutes</option>
							<option :value="300">5 minutes</option>
							<option :value="600">10 minutes</option>
						</select>
					</div>
					
					<!-- Include DNS -->
					<div class="flex items-center justify-between mb-3">
						<span class="text-xs text-slate-600 dark:text-slate-400">Include DNS Lookups</span>
						<button 
							@click="toggleDns"
							class="relative w-11 h-6 rounded-full transition-colors"
							:class="healthConfig.include_dns ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'"
						>
							<span 
								class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
								:class="healthConfig.include_dns ? 'translate-x-5' : 'translate-x-0'"
							></span>
						</button>
					</div>
					
					<!-- Status Info -->
					<div class="text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-700">
						<p v-if="healthStatus?.monitored_devices?.length">
							Monitoring {{ healthStatus.monitored_devices.length }} devices
						</p>
						<p v-if="healthStatus?.last_check" class="mt-1">
							Last check: {{ formatTimestamp(healthStatus.last_check) }}
						</p>
					</div>
				</div>
			</div>
			<button @click="toggleDarkMode" class="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300" title="Toggle dark mode">
				<svg v-if="!isDark" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
				</svg>
				<svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
				</svg>
			</button>
		</div>
	</div>
</template>

<script lang="ts" setup>
import axios from "axios";
import { onBeforeUnmount, ref, onMounted, reactive } from "vue";
import type { ParsedNetworkMap, TreeNode } from "../types/network";
import { useNetworkData } from "../composables/useNetworkData";
import { useMapLayout } from "../composables/useMapLayout";
import { useHealthMonitoring, type MonitoringConfig, type MonitoringStatus } from "../composables/useHealthMonitoring";

const props = defineProps<{
	root: TreeNode;
	hasUnsavedChanges?: boolean;
}>();

const emit = defineEmits<{
	(e: "updateMap", parsed: ParsedNetworkMap): void;
	(e: "applyLayout", layout: any): void;
	(e: "log", line: string): void;
	(e: "running", isRunning: boolean): void;
	(e: "clearLogs"): void;
	(e: "cleanUpLayout"): void;
	(e: "autoLoadFromServer"): void;
	(e: "saved"): void;
}>();

const loading = ref(false);
const saving = ref(false);
const message = ref("");
const isDark = ref(false);
const { parseNetworkMap } = useNetworkData();
const { exportLayout, importLayout } = useMapLayout();
const { fetchConfig, updateConfig, fetchStatus } = useHealthMonitoring();
let es: EventSource | null = null;
// Prefer relative URLs to avoid mixed-content; use APPLICATION_URL only if safe (https or same protocol)
const baseUrl = ref<string>("");

// Health monitoring settings
const showHealthSettings = ref(false);
const healthConfig = reactive<MonitoringConfig>({
	enabled: true,
	check_interval_seconds: 30,
	include_dns: true
});
const healthStatus = ref<MonitoringStatus | null>(null);

onMounted(async () => {
	// Initialize dark mode from localStorage
	const savedDarkMode = localStorage.getItem('darkMode');
	if (savedDarkMode === 'true') {
		isDark.value = true;
		document.documentElement.classList.add('dark');
	} else if (savedDarkMode === 'false') {
		isDark.value = false;
		document.documentElement.classList.remove('dark');
	} else {
		// Check system preference if no saved preference
		isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches;
		if (isDark.value) {
			document.documentElement.classList.add('dark');
		}
	}

	try {
		const res = await fetch("/api/config");
		if (res.ok) {
			const cfg = await res.json();
			const url = String(cfg?.applicationUrl || "").trim();
			if (url) {
				try {
					const u = new URL(url);
					// Use only if protocol matches page or it's https (to avoid mixed-content when page is https)
					if (u.protocol === window.location.protocol || u.protocol === "https:") {
						baseUrl.value = u.origin;
					}
				} catch {
					/* ignore invalid url */
				}
			}
		}
	} catch {
		/* ignore */
	}

	// Try to load saved layout from server
	try {
		const response = await axios.get('/api/load-layout');
		if (response.data.exists && response.data.layout) {
			emit("applyLayout", response.data.layout);
			emit("saved"); // Mark as saved since we just loaded the saved state
			message.value = "Loaded saved map from server";
			setTimeout(() => { message.value = ""; }, 3000);
		}
	} catch (error) {
		console.error("Failed to load saved layout:", error);
	}

	// Load health monitoring config
	await loadHealthConfig();

	// Add click outside listener for dropdowns
	document.addEventListener('click', handleClickOutside);
});

// Health monitoring functions
async function loadHealthConfig() {
	try {
		const config = await fetchConfig();
		if (config) {
			healthConfig.enabled = config.enabled;
			healthConfig.check_interval_seconds = config.check_interval_seconds;
			healthConfig.include_dns = config.include_dns;
		}
		healthStatus.value = await fetchStatus();
	} catch (error) {
		console.error("Failed to load health config:", error);
	}
}

async function updateHealthConfig() {
	try {
		await updateConfig(healthConfig);
		healthStatus.value = await fetchStatus();
	} catch (error) {
		console.error("Failed to update health config:", error);
	}
}

async function toggleMonitoring() {
	healthConfig.enabled = !healthConfig.enabled;
	await updateHealthConfig();
}

async function toggleDns() {
	healthConfig.include_dns = !healthConfig.include_dns;
	await updateHealthConfig();
}

function formatTimestamp(isoString: string): string {
	const date = new Date(isoString);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	
	if (diffMins < 1) return 'Just now';
	if (diffMins < 60) return `${diffMins}m ago`;
	
	return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
}

// Close health settings dropdown when clicking outside
function handleClickOutside(event: MouseEvent) {
	const target = event.target as HTMLElement;
	if (showHealthSettings.value && !target.closest('.relative')) {
		showHealthSettings.value = false;
	}
}

async function runMapper() {
	message.value = "";
	emit("clearLogs");
	startSSE();
}

async function saveLayout() {
	if (saving.value) return; // Prevent multiple simultaneous saves
	
	saving.value = true;
	try {
		const layout = exportLayout(props.root);
		const response = await axios.post('/api/save-layout', layout);
		if (response.data.success) {
			message.value = "Map saved to server";
			emit("saved");
			setTimeout(() => { message.value = ""; }, 3000);
		}
	} catch (error: any) {
		message.value = "Failed to save map";
		console.error("Save error:", error);
		setTimeout(() => { message.value = ""; }, 5000);
	} finally {
		saving.value = false;
	}
}

function exportJSON() {
	const layout = exportLayout(props.root);
	const blob = new Blob([JSON.stringify(layout, null, 2)], { type: "application/json" });
	const url = URL.createObjectURL(blob);
	const a = document.createElement("a");
	a.href = url;
	a.download = "network_layout.json";
	document.body.appendChild(a);
	a.click();
	URL.revokeObjectURL(url);
	document.body.removeChild(a);
	message.value = "JSON exported";
	setTimeout(() => { message.value = ""; }, 2000);
}

function onLoadFile(e: Event) {
	const input = e.target as HTMLInputElement;
	if (!input.files || !input.files.length) return;
	const file = input.files[0];
	const reader = new FileReader();
	reader.onload = () => {
		try {
			const text = String(reader.result || "");
			const layout = importLayout(text);
			emit("applyLayout", layout);
			message.value = "Layout loaded";
		} catch (err: any) {
			message.value = err?.message || "Failed to load layout";
		}
	};
	reader.readAsText(file);
}

function cleanUpLayout() {
	emit("cleanUpLayout");
	message.value = "Layout cleaned up";
}

function toggleDarkMode() {
	isDark.value = !isDark.value;
	if (isDark.value) {
		document.documentElement.classList.add('dark');
		localStorage.setItem('darkMode', 'true');
	} else {
		document.documentElement.classList.remove('dark');
		localStorage.setItem('darkMode', 'false');
	}
}

function startSSE() {
	endSSE();
	loading.value = true;
	message.value = "Running mapper…";
	emit("running", true);
	try {
		const sseUrl = `${baseUrl.value}/api/run-mapper/stream`.replace(/^\/\//, "/");
		es = new EventSource(baseUrl.value ? sseUrl : "/api/run-mapper/stream");
		es.addEventListener("log", (e: MessageEvent) => {
			emit("log", String(e.data || ""));
		});
		es.addEventListener("result", (e: MessageEvent) => {
			try {
				const payload = JSON.parse(String(e.data || "{}"));
				const content = String(payload?.content || "");
				if (content) {
					const parsed = parseNetworkMap(content);
					emit("updateMap", parsed);
				}
			} catch {
				/* ignore parse errors */
			}
		});
		es.addEventListener("done", (e: MessageEvent) => {
			message.value = "Mapper completed";
			loading.value = false;
			emit("running", false);
			// Emit a download hint line
			const dl = baseUrl.value ? `${baseUrl.value}/api/download-map` : `/api/download-map`;
			emit("log", `DOWNLOAD: ${dl}`);
			endSSE();
		});
		es.onerror = () => {
			if (loading.value) {
				message.value = "Stream error";
				loading.value = false;
			}
			emit("running", false);
			endSSE();
		};
	} catch (err: any) {
		message.value = err?.message || "Failed to start log stream";
		loading.value = false;
		emit("running", false);
	}
}

function endSSE() {
	if (es) {
		es.close();
		es = null;
	}
}

onBeforeUnmount(() => {
	endSSE();
	document.removeEventListener('click', handleClickOutside);
});
</script>


