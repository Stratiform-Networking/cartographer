<template>
	<!-- Loading State -->
	<div v-if="authLoading" class="h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
		<div class="text-center">
			<svg class="animate-spin h-12 w-12 text-cyan-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
			<p class="text-slate-400">Loading Cartographer...</p>
		</div>
	</div>

	<!-- Setup Wizard (First Run) -->
	<SetupWizard v-else-if="needsSetup" @complete="onSetupComplete" />

	<!-- Login Screen -->
	<LoginScreen v-else-if="!isAuthenticated" @success="onLoginSuccess" />

	<!-- Main Application -->
	<div v-else class="h-screen flex flex-col bg-slate-50 dark:bg-slate-900">
		<MapControls
			:root="parsed?.root || emptyRoot"
			:hasUnsavedChanges="hasUnsavedChanges"
			:canEdit="canWrite"
			@updateMap="onUpdateMap"
			@applyLayout="onApplyLayout"
			@log="onLog"
			@running="onRunning"
			@clearLogs="onClearLogs"
			@cleanUpLayout="onCleanUpLayout"
			@saved="onMapSaved"
		>
			<!-- User Menu Slot -->
			<template #user-menu>
				<UserMenu @logout="onLogout" @manageUsers="showUserManagement = true" />
			</template>
		</MapControls>
		<div class="flex flex-1 min-h-0">
			<aside class="w-80 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800">
				<DeviceList
					v-if="parsed"
					:root="parsed.root"
					:selectedId="selectedId"
					@select="onNodeSelected"
				/>
				<div v-else class="p-4 text-sm text-slate-600 dark:text-slate-400">
					Run the mapper to generate a network map, or load a saved layout.
				</div>
			</aside>
			<main class="flex-1 p-3 relative bg-slate-50 dark:bg-slate-900">
				<!-- Add Node button (top-left, edit mode only) -->
				<div v-if="mode === 'edit'" class="absolute top-2 left-3 z-10">
					<button
						@click="onAddNode"
						class="px-3 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 shadow-sm text-slate-700 dark:text-slate-300 hover:bg-emerald-50 dark:hover:bg-emerald-900/30 hover:border-emerald-400 dark:hover:border-emerald-600 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors flex items-center gap-1.5"
						title="Add a new node to the network map"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
						</svg>
						Add Node
					</button>
				</div>
				<!-- Interaction mode toggle (top-right) -->
				<div class="absolute top-2 right-3 z-10 flex items-center gap-2">
					<div class="rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 shadow-sm overflow-hidden flex items-center">
						<button
							class="px-3 py-1 text-xs"
							:class="mode === 'pan' ? 'bg-blue-600 text-white' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700'"
							@click="mode = 'pan'"
							title="Pan mode (default)"
						>
							Pan
						</button>
						<button
							class="px-3 py-1 text-xs border-l border-slate-300 dark:border-slate-600"
							:class="[
								mode === 'edit' ? 'bg-blue-600 text-white' : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700',
								!canWrite ? 'opacity-50 cursor-not-allowed' : ''
							]"
							@click="canWrite && (mode = 'edit')"
							:disabled="!canWrite"
							:title="canWrite ? 'Edit nodes (drag + type) + Pan' : 'Edit mode requires write permissions'"
						>
							Edit
						</button>
					</div>
					<button
						@click="toggleHistoryPanel"
						class="px-3 py-1 text-xs rounded border border-slate-300 dark:border-slate-600 shadow-sm flex items-center gap-1.5 transition-colors"
						:class="showHistoryPanel 
							? 'bg-amber-500 text-white border-amber-500 hover:bg-amber-600' 
							: 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-amber-50 dark:hover:bg-amber-900/30 hover:border-amber-400 dark:hover:border-amber-600 hover:text-amber-700 dark:hover:text-amber-400'"
						title="View node change history"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						History
					</button>
				</div>
				<!-- Node configuration panel (bottom-right) -->
				<div class="absolute bottom-2 right-3 z-10">
					<div v-if="mode === 'edit' && selectedNode" class="flex items-center gap-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded px-2 py-1 shadow-sm">
						<span class="text-xs text-slate-600 dark:text-slate-400">Type:</span>
						<select class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5"
							v-model="editRole"
							@change="onChangeRole"
						>
							<option value="gateway/router">Gateway / Router</option>
							<option value="firewall">Firewall</option>
							<option value="switch/ap">Switch / AP</option>
							<option value="server">Server</option>
							<option value="service">Service</option>
							<option value="nas">NAS</option>
							<option value="client">Client</option>
							<option value="unknown">Unknown</option>
						</select>
						<span class="text-xs text-slate-600 dark:text-slate-400 ml-3">IP:</span>
						<input class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5 w-36"
							v-model="editIp"
							@change="onChangeIp"
							placeholder="192.168.1.10"
						/>
						<span class="text-xs text-slate-600 dark:text-slate-400">Name:</span>
						<input class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5 w-44"
							v-model="editHostname"
							@change="onChangeHostname"
							placeholder="device.local"
						/>
						<span class="text-xs text-slate-600 dark:text-slate-400 ml-3">Connect to:</span>
						<select class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5"
							v-model="connectParent"
							@change="onChangeParent"
						>
							<option v-for="opt in connectOptions" :key="opt.id" :value="opt.id">
								{{ opt.name }}
							</option>
						</select>
						<span class="text-xs text-slate-600 dark:text-slate-400 ml-3">Speed:</span>
						<select 
							v-if="!showCustomSpeed"
							class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5"
							v-model="editConnectionSpeed"
							@change="onSpeedSelectChange"
						>
							<option value="">None</option>
							<option value="10Mbps">10Mbps</option>
							<option value="100Mbps">100Mbps</option>
							<option value="1GbE">1GbE</option>
							<option value="2.5GbE">2.5GbE</option>
							<option value="5GbE">5GbE</option>
							<option value="10GbE">10GbE</option>
							<option value="25GbE">25GbE</option>
							<option value="40GbE">40GbE</option>
							<option value="100GbE">100GbE</option>
							<option value="__custom__">Custom...</option>
						</select>
						<input 
							v-else
							class="text-xs border border-slate-300 dark:border-slate-600 dark:bg-slate-700 dark:text-slate-200 rounded px-1 py-0.5 w-24"
							v-model="editConnectionSpeed"
							@blur="onCustomSpeedBlur"
							@keyup.enter="onCustomSpeedBlur"
							placeholder="e.g. 1GbE"
							autofocus
						/>
						<button 
							v-if="selectedNode.id !== parsed?.root.id"
							@click="onRemoveNode" 
							class="ml-3 px-2 py-0.5 text-xs bg-red-600 text-white rounded hover:bg-red-700"
							title="Remove this node"
						>
							Remove
						</button>
					</div>
				</div>
				<div class="w-full h-full">
					<NetworkMap
						ref="networkMapRef"
						v-if="parsed"
						:data="parsed.root"
						:mode="mode"
						:selectedId="selectedId"
						@nodeSelected="onNodeSelected"
						@nodePositionChanged="onNodePositionChanged"
					/>
					<div v-else class="h-full rounded border border-dashed border-slate-300 dark:border-slate-600 flex items-center justify-center text-slate-500 dark:text-slate-400">
						No map loaded yet.
					</div>
				</div>
			</main>
			<!-- History Panel (Right Side) -->
			<aside 
				v-if="showHistoryPanel"
				class="w-96 border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 flex flex-col overflow-hidden"
			>
				<div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900">
					<div class="flex items-center gap-2">
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
						</svg>
						<h2 class="font-semibold text-slate-800 dark:text-slate-100">Change History</h2>
					</div>
					<button 
						@click="showHistoryPanel = false"
						class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
						title="Close history panel"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				
				<!-- Filter tabs -->
				<div class="flex border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
					<button
						@click="historyFilter = 'selected'"
						class="flex-1 px-3 py-2 text-xs font-medium transition-colors"
						:class="historyFilter === 'selected' 
							? 'text-amber-600 dark:text-amber-400 border-b-2 border-amber-500 bg-white dark:bg-slate-800' 
							: 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
					>
						Selected Node
					</button>
					<button
						@click="historyFilter = 'all'"
						class="flex-1 px-3 py-2 text-xs font-medium transition-colors"
						:class="historyFilter === 'all' 
							? 'text-amber-600 dark:text-amber-400 border-b-2 border-amber-500 bg-white dark:bg-slate-800' 
							: 'text-slate-600 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'"
					>
						All Nodes
					</button>
				</div>
				
				<!-- History content -->
				<div class="flex-1 overflow-auto p-3">
					<!-- Selected node history -->
					<div v-if="historyFilter === 'selected'">
						<div v-if="selectedNode && selectedNode.history?.length" class="space-y-3">
							<div class="mb-3 p-2 rounded bg-slate-100 dark:bg-slate-700/50">
								<div class="text-xs font-medium text-slate-700 dark:text-slate-300">{{ selectedNode.name }}</div>
								<div class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
									Version {{ selectedNode.version || 1 }} • {{ selectedNode.history?.length || 0 }} changes
								</div>
							</div>
							<div 
								v-for="(entry, idx) in [...(selectedNode.history || [])].reverse()" 
								:key="idx"
								class="relative pl-4 pb-3 border-l-2 border-slate-200 dark:border-slate-600 last:pb-0"
							>
								<div class="absolute -left-1.5 top-0 w-3 h-3 rounded-full bg-amber-400 dark:bg-amber-500 border-2 border-white dark:border-slate-800"></div>
								<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">
									v{{ entry.version }} • {{ formatTimestamp(entry.timestamp) }}
								</div>
								<div 
									v-for="(change, cIdx) in entry.changes" 
									:key="cIdx"
									class="text-sm text-slate-700 dark:text-slate-300"
								>
									{{ change }}
								</div>
							</div>
						</div>
						<div v-else-if="selectedNode && !selectedNode.history?.length" class="text-center py-8 text-slate-500 dark:text-slate-400">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-sm">No history for this node</p>
						</div>
						<div v-else class="text-center py-8 text-slate-500 dark:text-slate-400">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
							</svg>
							<p class="text-sm">Select a node to view its history</p>
						</div>
					</div>
					
					<!-- All nodes history -->
					<div v-else>
						<div v-if="allNodesHistory.length" class="space-y-3">
							<div 
								v-for="(item, idx) in allNodesHistory" 
								:key="idx"
								class="relative pl-4 pb-3 border-l-2 border-slate-200 dark:border-slate-600 last:pb-0 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/30 -ml-1 pl-5 py-1 rounded-r"
								@click="selectNodeFromHistory(item.nodeId)"
							>
								<div class="absolute left-0 top-1.5 w-3 h-3 rounded-full border-2 border-white dark:border-slate-800"
									:class="getNodeRoleColor(item.role)"
								></div>
								<div class="flex items-center gap-2 mb-0.5">
									<span class="text-xs font-medium text-slate-700 dark:text-slate-300 truncate max-w-48">{{ item.nodeName }}</span>
									<span class="text-xs text-slate-400 dark:text-slate-500">v{{ item.version }}</span>
								</div>
								<div class="text-xs text-slate-500 dark:text-slate-400 mb-1">
									{{ formatTimestamp(item.timestamp) }}
								</div>
								<div 
									v-for="(change, cIdx) in item.changes" 
									:key="cIdx"
									class="text-xs text-slate-600 dark:text-slate-400"
								>
									{{ change }}
								</div>
							</div>
						</div>
						<div v-else class="text-center py-8 text-slate-500 dark:text-slate-400">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							<p class="text-sm">No changes recorded yet</p>
							<p class="text-xs mt-1">Changes will appear here as you edit nodes</p>
						</div>
					</div>
				</div>
			</aside>
			<!-- Node Info Panel (Right Side) -->
			<NodeInfoPanel
				v-if="showNodeInfoPanel && selectedNode"
				:node="selectedNode"
				:canEdit="canWrite"
				@close="closeNodeInfoPanel"
				@toggleMonitoring="onToggleNodeMonitoring"
				@updateNotes="onUpdateNodeNotes"
			/>
		</div>
		<!-- Terminal / Logs Panel -->
		<div 
			v-if="logs.length" 
			class="flex flex-col border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 transition-all ease-linear duration-75"
			:style="{ height: logsHeight + 'px' }"
		>
			<!-- Resize Handle -->
			<div 
				class="h-1 bg-slate-200 dark:bg-slate-700 cursor-row-resize hover:bg-blue-400 active:bg-blue-600 flex justify-center"
				@mousedown.prevent="startResize"
			>
				<div class="w-12 h-0.5 bg-slate-400 dark:bg-slate-500 rounded my-auto"></div>
			</div>

			<!-- Logs Content -->
			<div 
				ref="logContainer" 
				class="flex-1 overflow-auto font-mono text-xs px-3 py-2 text-slate-700 dark:text-slate-300"
			>
				<div v-for="(line, idx) in logs" :key="idx" class="whitespace-pre-wrap text-slate-700 dark:text-slate-300">
					<template v-if="downloadHref(line)">
						<a :href="downloadHref(line)!" class="text-blue-600 underline" target="_blank" rel="noopener">
							Download network_map.txt
						</a>
					</template>
					<template v-else>
						{{ line }}
					</template>
				</div>
			</div>
		</div>

		<!-- User Management Modal -->
		<UserManagement v-if="showUserManagement" @close="showUserManagement = false" />
	</div>
</template>

<script lang="ts" setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, computed } from "vue";
import axios from "axios";
import MapControls from "./MapControls.vue";
import DeviceList from "./DeviceList.vue";
import NetworkMap from "./NetworkMap.vue";
import NodeInfoPanel from "./NodeInfoPanel.vue";
import SetupWizard from "./SetupWizard.vue";
import LoginScreen from "./LoginScreen.vue";
import UserMenu from "./UserMenu.vue";
import UserManagement from "./UserManagement.vue";
import type { ParsedNetworkMap, TreeNode, NodeVersion } from "../types/network";
import { useMapLayout } from "../composables/useMapLayout";
import { useNetworkData } from "../composables/useNetworkData";
import { useHealthMonitoring } from "../composables/useHealthMonitoring";
import { useAuth } from "../composables/useAuth";

// Auth state
const { isAuthenticated, canWrite, checkSetupStatus, verifySession } = useAuth();
const authLoading = ref(true);
const needsSetup = ref(false);
const showUserManagement = ref(false);

// Check auth status on mount
async function initAuth() {
	authLoading.value = true;
	try {
		// Check if setup is complete
		const status = await checkSetupStatus();
		needsSetup.value = !status.is_setup_complete;
		
		// If setup is complete and we have a stored token, verify it
		if (status.is_setup_complete) {
			await verifySession();
		}
	} catch (e) {
		console.error("[Auth] Failed to check setup status:", e);
		// If we can't reach the auth service, assume setup is needed
		needsSetup.value = false;
	} finally {
		authLoading.value = false;
	}
}

function onSetupComplete() {
	needsSetup.value = false;
}

function onLoginSuccess() {
	// Auth state is already updated by the composable
	console.log("[App] Login successful");
}

function onLogout() {
	// Reload the page to reset all state
	window.location.reload();
}

// Version management helpers
function initializeNodeVersion(node: TreeNode, source: 'manual' | 'mapper' = 'manual'): void {
	const now = new Date().toISOString();
	if (!node.createdAt) {
		node.createdAt = now;
		node.version = 1;
		node.history = [{
			version: 1,
			timestamp: now,
			changes: [`Node created (${source})`]
		}];
	}
	node.updatedAt = now;
}

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
		changes
	});
	if (node.history.length > 20) {
		node.history = node.history.slice(-20);
	}
}

function ensureAllNodesVersioned(root: TreeNode, source: 'manual' | 'mapper' = 'mapper'): void {
	const walk = (n: TreeNode) => {
		if (n.role !== 'group') {
			initializeNodeVersion(n, source);
		}
		for (const c of (n.children || [])) walk(c);
	};
	walk(root);
}

const parsed = ref<ParsedNetworkMap | null>(null);
const selectedId = ref<string | undefined>(undefined);
const emptyRoot: TreeNode = { id: "root", name: "Network", role: "group", children: [] };
const logs = ref<string[]>([]);
const running = ref(false);
const mode = ref<'pan' | 'edit'>('pan'); // interaction mode

// Watch canWrite and reset mode if user becomes readonly
watch(canWrite, (canEdit) => {
	if (!canEdit && mode.value === 'edit') {
		mode.value = 'pan';
	}
});
const showHistoryPanel = ref(false); // history panel visibility
const showNodeInfoPanel = ref(false); // node info panel visibility
const historyFilter = ref<'selected' | 'all'>('selected'); // history panel filter
const networkMapRef = ref<InstanceType<typeof NetworkMap> | null>(null);
const editRole = ref<string>('unknown');
const connectParent = ref<string>('');
const editIp = ref<string>('');
const editHostname = ref<string>('');
const editConnectionSpeed = ref<string>('');
const showCustomSpeed = ref<boolean>(false);

// Track saved state for unsaved changes detection
const savedStateHash = ref<string>('');

// Compute hash of current state
const currentStateHash = computed(() => {
	if (!parsed.value?.root) return '';
	try {
		return JSON.stringify(parsed.value.root);
	} catch {
		return '';
	}
});

// Check if there are unsaved changes
const hasUnsavedChanges = computed(() => {
	if (!savedStateHash.value) return true; // No saved state yet
	return currentStateHash.value !== savedStateHash.value;
});

// Terminal Resize Logic
const logsHeight = ref(192); // Default 12rem (48 * 4px)
const logContainer = ref<HTMLDivElement | null>(null);
let isResizing = false;

function startResize(e: MouseEvent) {
	isResizing = true;
	document.addEventListener('mousemove', handleResize);
	document.addEventListener('mouseup', stopResize);
	document.body.style.userSelect = 'none';
}

function handleResize(e: MouseEvent) {
	if (!isResizing) return;
	// Calculate new height based on window height - mouse Y
	// But capped between 100px and 80% of screen
	const newHeight = window.innerHeight - e.clientY;
	if (newHeight > 100 && newHeight < window.innerHeight * 0.8) {
		logsHeight.value = newHeight;
	}
}

function stopResize() {
	isResizing = false;
	document.removeEventListener('mousemove', handleResize);
	document.removeEventListener('mouseup', stopResize);
	document.body.style.userSelect = '';
}

const { applySavedPositions, clearPositions, exportLayout } = useMapLayout();
const { parseNetworkMap } = useNetworkData();
const { registerDevices, startPolling, stopPolling } = useHealthMonitoring();

// Track if we've done initial registration
let hasRegisteredDevices = false;

// Helper to get IPs of devices that have monitoring enabled
function getMonitoredDeviceIPs(root: TreeNode): string[] {
	const devices = flattenDevices(root);
	return devices
		.filter(d => d.ip && d.monitoringEnabled !== false) // Only include nodes with monitoring enabled (default: true)
		.map(d => d.ip!)
		.filter((ip): ip is string => !!ip);
}

// Register devices for health monitoring whenever parsed changes
watch(() => parsed.value?.root, async (root) => {
	if (root) {
		const ips = getMonitoredDeviceIPs(root);
		
		if (ips.length > 0) {
			await registerDevices(ips);
			hasRegisteredDevices = true;
			console.log(`[Health] Registered ${ips.length} device IPs for monitoring`);
		}
	}
});

// Start polling for health updates when app mounts
onMounted(async () => {
	// Initialize auth first
	await initAuth();
	
	// Start polling for cached health metrics every 10 seconds
	startPolling(10000);
	
	// If we already have parsed data (from MapControls loading saved layout),
	// register devices now
	if (parsed.value?.root && !hasRegisteredDevices) {
		const ips = getMonitoredDeviceIPs(parsed.value.root);
		if (ips.length > 0) {
			await registerDevices(ips);
			hasRegisteredDevices = true;
			console.log(`[Health] Registered ${ips.length} device IPs for monitoring (on mount)`);
		}
	}
});

// Stop polling when app unmounts
onBeforeUnmount(() => {
	stopPolling();
});

// Auto-save debounce timer
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
const autoSaveDelay = 2000; // 2 seconds after last change

function triggerAutoSave() {
	if (autoSaveTimer) {
		clearTimeout(autoSaveTimer);
	}
	autoSaveTimer = setTimeout(async () => {
		if (parsed.value && hasUnsavedChanges.value) {
			try {
				const layout = exportLayout(parsed.value.root);
				await axios.post('/api/save-layout', layout);
				savedStateHash.value = currentStateHash.value;
				console.log('[Auto-save] Network map saved');
			} catch (error) {
				console.error('[Auto-save] Failed to save:', error);
			}
		}
	}, autoSaveDelay);
}

function onUpdateMap(p: ParsedNetworkMap) {
	// Version all nodes from the mapper
	ensureAllNodesVersioned(p.root, 'mapper');
	parsed.value = p;
	selectedId.value = undefined;
	triggerAutoSave();
}

function findNodeById(n: TreeNode, id?: string): TreeNode | undefined {
	if (!id) return undefined;
	if (n.id === id) return n;
	for (const c of (n.children || [])) {
		const f = findNodeById(c, id);
		if (f) return f;
	}
	return undefined;
}

function flattenDevices(root: TreeNode): TreeNode[] {
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

// Sort nodes by depth, parent position, and IP address (matching DeviceList)
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
	const maxDepthForSort = Math.max(...Array.from(nodesByDepth.keys()), 0);
	for (let depth = 0; depth <= maxDepthForSort; depth++) {
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
	for (let depth = 0; depth <= maxDepthForSort; depth++) {
		const nodesAtDepth = nodesByDepth.get(depth) || [];
		sorted.push(...nodesAtDepth);
	}
	
	return sorted;
}

function findGroupByPrefix(root: TreeNode, prefix: string): TreeNode | undefined {
	return (root.children || []).find(c => c.name.toLowerCase().startsWith(prefix));
}

function removeFromAllGroups(root: TreeNode, id: string): TreeNode | undefined {
	for (const g of (root.children || [])) {
		const idx = (g.children || []).findIndex(c => c.id === id);
		if (idx !== -1) {
			const [node] = g.children!.splice(idx, 1);
			return node;
		}
	}
	return undefined;
}

function walkAll(root: TreeNode, fn: (n: TreeNode, parent?: TreeNode) => void) {
	fn(root, undefined);
	for (const g of (root.children || [])) {
		for (const c of (g.children || [])) {
			fn(c, g);
		}
	}
}

function onChangeRole() {
	if (!parsed.value || !selectedId.value) return;
	const root = parsed.value.root;
	const node = findNodeById(root, selectedId.value);
	if (!node) return;
	const oldRole = node.role;
	node.role = editRole.value as any;
	
	// Track the version change
	updateNodeVersion(node, [`Role changed from "${oldRole}" to "${node.role}"`]);
	
	// Move across tiers if needed
	const role = node.role || 'unknown';
	let targetPrefix = '';
	if (role === 'firewall' || role === 'switch/ap') targetPrefix = 'infrastructure';
	else if (role === 'server' || role === 'service' || role === 'nas') targetPrefix = 'servers';
	else if (role === 'client' || role === 'unknown') targetPrefix = 'clients';
	// gateway/router remains at root (no move)
	if (targetPrefix) {
		const existingParent = removeFromAllGroups(root, node.id);
		const targetGroup = findGroupByPrefix(root, targetPrefix);
		if (existingParent && targetGroup) {
			targetGroup.children = targetGroup.children || [];
			targetGroup.children.push(existingParent);
		}
	}
	// Refresh view and trigger auto-save
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

const selectedNode = computed(() => {
	if (!parsed.value) return undefined;
	return findNodeById(parsed.value.root, selectedId.value);
});

// History panel helpers
interface HistoryEntry {
	nodeId: string;
	nodeName: string;
	role?: string;
	version: number;
	timestamp: string;
	changes: string[];
}

const allNodesHistory = computed((): HistoryEntry[] => {
	if (!parsed.value) return [];
	
	const entries: HistoryEntry[] = [];
	const collectHistory = (node: TreeNode) => {
		if (node.history && node.role !== 'group') {
			for (const h of node.history) {
				entries.push({
					nodeId: node.id,
					nodeName: node.name,
					role: node.role,
					version: h.version,
					timestamp: h.timestamp,
					changes: h.changes
				});
			}
		}
		for (const child of (node.children || [])) {
			collectHistory(child);
		}
	};
	collectHistory(parsed.value.root);
	
	// Sort by timestamp descending (most recent first)
	entries.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
	
	// Limit to most recent 100 entries
	return entries.slice(0, 100);
});

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

function selectNodeFromHistory(nodeId: string) {
	selectedId.value = nodeId;
	historyFilter.value = 'selected';
}

function toggleHistoryPanel() {
	showHistoryPanel.value = !showHistoryPanel.value;
	// Close node info panel when opening history
	if (showHistoryPanel.value) {
		showNodeInfoPanel.value = false;
	}
}

function onNodeSelected(id: string | undefined) {
	selectedId.value = id;
	if (id) {
		// Open node info panel when selecting a node
		showNodeInfoPanel.value = true;
		// Close history panel when opening node info
		showHistoryPanel.value = false;
	} else {
		// Close node info panel when deselecting
		showNodeInfoPanel.value = false;
	}
}

function closeNodeInfoPanel() {
	showNodeInfoPanel.value = false;
}

async function onToggleNodeMonitoring(nodeId: string, enabled: boolean) {
	if (!canWrite.value) return; // Permission check
	if (!parsed.value?.root) return;
	
	// Find the node and update its monitoringEnabled property
	const node = findNodeById(parsed.value.root, nodeId);
	if (node) {
		node.monitoringEnabled = enabled;
		
		// Update the version for change tracking
		const now = new Date().toISOString();
		node.updatedAt = now;
		node.version = (node.version || 0) + 1;
		
		// Re-register devices with updated list (excludes disabled nodes)
		const ips = getMonitoredDeviceIPs(parsed.value.root);
		console.log(`[Health] ${enabled ? 'Enabling' : 'Disabling'} monitoring for ${node.name || nodeId} (IP: ${node.ip})`);
		console.log(`[Health] Updating monitored devices list: ${ips.length} devices`, ips);
		
		// Send updated list to backend - this REPLACES the entire list
		await registerDevices(ips, false); // Don't trigger immediate check when disabling
		
		// Trigger auto-save
		triggerAutoSave();
	}
}

function onUpdateNodeNotes(nodeId: string, notes: string) {
	if (!canWrite.value) return; // Permission check
	if (!parsed.value?.root) return;
	
	const node = findNodeById(parsed.value.root, nodeId);
	if (node) {
		const oldNotes = node.notes;
		node.notes = notes || undefined; // Don't store empty string
		
		// Only track version change if notes actually changed
		if (oldNotes !== node.notes) {
			if (notes) {
				updateNodeVersion(node, ['Notes updated']);
			} else if (oldNotes) {
				updateNodeVersion(node, ['Notes cleared']);
			}
			
			// Trigger reactivity and auto-save
			parsed.value = { ...parsed.value };
			triggerAutoSave();
		}
	}
}

function getNodeRoleColor(role?: string): string {
	switch (role) {
		case 'gateway/router': return 'bg-red-500';
		case 'firewall': return 'bg-orange-500';
		case 'switch/ap': return 'bg-blue-500';
		case 'server': return 'bg-green-500';
		case 'service': return 'bg-emerald-500';
		case 'nas': return 'bg-purple-500';
		case 'client': return 'bg-cyan-500';
		default: return 'bg-gray-400';
	}
}

const connectOptions = computed(() => {
	if (!parsed.value) return [];
	const root = parsed.value.root;
	const all = flattenDevices(root);
	const sorted = sortByDepthAndIP(all, root);
	const current = selectedNode.value;
	if (!current) return [];
	
	// Add root at the beginning, then add sorted devices
	const allWithRoot = [root, ...sorted];
	
	// Deduplicate by IP address (keep first occurrence)
	const seen = new Set<string>();
	const deduplicated = allWithRoot.filter(d => {
		const key = (d as any).ip || d.id;
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
	
	// Allow connecting to ANY device (including router) except itself
	const allowed = deduplicated.filter(d => d.id !== current.id);
	return allowed.map(d => ({ id: d.id, name: d.name }));
});

watch(selectedNode, (n) => {
	// Keep the editor UI in sync with the selected node
	editRole.value = (n as any)?.role || 'unknown';
	connectParent.value = (n as any)?.parentId || (parsed.value?.root.id || '');
	editIp.value = (n as any)?.ip || (n as any)?.id || '';
	editHostname.value = (n as any)?.hostname || '';
	editConnectionSpeed.value = (n as any)?.connectionSpeed || '';
	showCustomSpeed.value = false; // Reset to dropdown when selecting a new node
});

// Zoom to node when selected from device list
watch(selectedId, (newId) => {
	if (newId && networkMapRef.value) {
		nextTick(() => {
			networkMapRef.value?.zoomToNode(newId);
		});
	}
});

function onChangeParent() {
	if (!parsed.value || !selectedId.value) return;
	const node = findNodeById(parsed.value.root, selectedId.value);
	if (!node) return;
	const oldParent = (node as any).parentId;
	(node as any).parentId = connectParent.value || undefined;
	
	// Track the version change
	updateNodeVersion(node, [`Parent connection changed from "${oldParent || 'root'}" to "${connectParent.value || 'root'}"`]);
	
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

function onSpeedSelectChange() {
	if (editConnectionSpeed.value === '__custom__') {
		showCustomSpeed.value = true;
		editConnectionSpeed.value = '';
		return;
	}
	onChangeConnectionSpeed();
}

function onCustomSpeedBlur() {
	if (!editConnectionSpeed.value.trim()) {
		// If empty, go back to dropdown
		showCustomSpeed.value = false;
	}
	onChangeConnectionSpeed();
}

function onChangeConnectionSpeed() {
	if (!parsed.value || !selectedId.value) return;
	const node = findNodeById(parsed.value.root, selectedId.value);
	if (!node) return;
	const oldSpeed = (node as any).connectionSpeed;
	const speed = editConnectionSpeed.value.trim();
	(node as any).connectionSpeed = speed || undefined;
	
	// Track the version change
	updateNodeVersion(node, [`Connection speed changed from "${oldSpeed || 'none'}" to "${speed || 'none'}"`]);
	
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

function refreshNodeLabel(n: TreeNode) {
	const ip = (n as any)?.ip || n.id;
	const hn = (n as any)?.hostname || 'Unknown';
	n.name = `${ip} (${hn})`;
}

function onChangeIp() {
	if (!parsed.value || !selectedId.value) return;
	const root = parsed.value.root;
	const node = findNodeById(root, selectedId.value);
	if (!node) return;
	const oldId = node.id;
	const oldIp = (node as any).ip;
	(node as any).ip = editIp.value.trim();
	if ((node as any).ip) node.id = (node as any).ip;
	// Update any child referencing this as parent
	walkAll(root, (n) => {
		if ((n as any).parentId === oldId) (n as any).parentId = node.id;
	});
	refreshNodeLabel(node);
	
	// Track the version change
	updateNodeVersion(node, [`IP address changed from "${oldIp || 'none'}" to "${(node as any).ip || 'none'}"`]);
	
	selectedId.value = node.id;
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

function onChangeHostname() {
	if (!parsed.value || !selectedId.value) return;
	const node = findNodeById(parsed.value.root, selectedId.value);
	if (!node) return;
	const oldHostname = (node as any).hostname;
	(node as any).hostname = editHostname.value.trim();
	refreshNodeLabel(node);
	
	// Track the version change
	updateNodeVersion(node, [`Hostname changed from "${oldHostname || 'none'}" to "${(node as any).hostname || 'none'}"`]);
	
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

function onApplyLayout(layout: any) {
	if (layout.root) {
		// Full project load - reconstruct devices array from tree
		const devices: Array<{ ip: string; hostname: string; role: any; depth: number }> = [];
		const extractDevices = (node: TreeNode, depth: number) => {
			if (node.ip && node.role !== 'group') {
				devices.push({
					ip: node.ip,
					hostname: node.hostname || 'unknown',
					role: node.role as any,
					depth: depth
				});
			}
			for (const child of (node.children || [])) {
				extractDevices(child, depth + 1);
			}
		};
		extractDevices(layout.root, 0);
		
		// Ensure all nodes have version info (for backwards compatibility with old saves)
		ensureAllNodesVersioned(layout.root, 'mapper');
		
		parsed.value = {
			raw: "", // Not available when loading from JSON, but we have the root
			devices: devices,
			root: layout.root
		};
	}
	
	if (!parsed.value) return;
	
	applySavedPositions(parsed.value.root, layout);
	
	// Trigger reactivity with shallow replacement (if we have raw source)
	if (parsed.value.raw) {
		parsed.value = parseNetworkMap(parsed.value.raw);
		ensureAllNodesVersioned(parsed.value.root, 'mapper');
		applySavedPositions(parsed.value.root, layout);
	} else {
		// Force refresh if we just loaded the tree
		parsed.value = { ...parsed.value };
	}
}

function onMapSaved() {
	// Update saved state hash to current state
	savedStateHash.value = currentStateHash.value;
}

function onNodePositionChanged(id: string, x: number, y: number) {
	if (!parsed.value) return;
	const node = findNodeById(parsed.value.root, id);
	if (node && node.role !== 'group') {
		// Track position change in version history
		updateNodeVersion(node, [`Position changed to (${Math.round(x)}, ${Math.round(y)})`]);
		// Trigger auto-save
		parsed.value = { ...parsed.value };
		triggerAutoSave();
	}
}

function onLog(line: string) {
	logs.value.push(line);
	if (logs.value.length > 2000) logs.value.splice(0, logs.value.length - 2000);
	
	// Auto-scroll to bottom
	nextTick(() => {
		if (logContainer.value) {
			logContainer.value.scrollTop = logContainer.value.scrollHeight;
		}
	});
}
function onRunning(isRunning: boolean) {
	running.value = isRunning;
}
function onClearLogs() {
	logs.value = [];
}

function downloadHref(line: string): string | null {
	const m = /^DOWNLOAD:\s+(https?:\/\/[^\s]+)$/i.exec(line.trim());
	return m ? m[1] : null;
}

function onRemoveNode() {
	if (!parsed.value || !selectedId.value) return;
	const root = parsed.value.root;
	
	// Don't allow removing the root gateway
	if (selectedId.value === root.id) return;
	
	const nodeToRemove = findNodeById(root, selectedId.value);
	if (!nodeToRemove) return;
	
	const nodeId = nodeToRemove.id;
	const nodeName = nodeToRemove.name;
	
	// Reassign any child nodes that have this node as their parent to the root
	walkAll(root, (n) => {
		if ((n as any).parentId === nodeId && n.id !== nodeId) {
			(n as any).parentId = root.id;
			// Track the parent change for affected nodes
			updateNodeVersion(n, [`Parent reassigned to root (previous parent "${nodeName}" was removed)`]);
		}
	});
	
	// Remove the node from its group
	const removed = removeFromAllGroups(root, nodeId);
	
	if (removed) {
		// Clear selection
		selectedId.value = undefined;
		// Trigger re-render and auto-save
		parsed.value = { ...parsed.value };
		triggerAutoSave();
	}
}

function onAddNode() {
	if (!parsed.value) return;
	const root = parsed.value.root;
	
	// Generate a unique ID for the new node
	const timestamp = Date.now();
	const randomSuffix = Math.random().toString(36).substring(2, 6);
	const newId = `new-node-${timestamp}-${randomSuffix}`;
	
	// Create a new node with default values
	const newNode: TreeNode = {
		id: newId,
		name: `New Device (${newId.slice(-8)})`,
		role: 'unknown',
		ip: '',
		hostname: 'New Device',
	};
	
	// Initialize version tracking for the new node
	initializeNodeVersion(newNode, 'manual');
	
	// Set parent to root by default
	(newNode as any).parentId = root.id;
	
	// Find or create the clients group (default for unknown devices)
	let clientsGroup = findGroupByPrefix(root, 'clients');
	if (!clientsGroup) {
		// Create clients group if it doesn't exist
		clientsGroup = {
			id: 'clients',
			name: 'Clients',
			role: 'group',
			children: []
		};
		root.children = root.children || [];
		root.children.push(clientsGroup);
	}
	
	// Add the new node to the clients group
	clientsGroup.children = clientsGroup.children || [];
	clientsGroup.children.push(newNode);
	
	// Select the new node so user can immediately configure it
	selectedId.value = newId;
	
	// Trigger re-render and auto-save
	parsed.value = { ...parsed.value };
	triggerAutoSave();
}

// Cleanup auto-save timer on unmount
onBeforeUnmount(() => {
	if (autoSaveTimer) {
		clearTimeout(autoSaveTimer);
		autoSaveTimer = null;
	}
});

function onCleanUpLayout() {
	if (!parsed.value) return;
	
	// Clear all saved positions
	clearPositions();
	
	// Remove fx/fy from all nodes in the tree and calculate depth-based layout
	const root = parsed.value.root;
	
	// Build a map of all nodes (including nested ones)
	const allNodes = new Map<string, TreeNode>();
	const collectNodes = (n: TreeNode) => {
		allNodes.set(n.id, n);
		for (const g of (n.children || [])) {
			for (const c of (g.children || [])) {
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
			return compareIps(a, b);
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
	const marginY = 40;
	const canvasHeight = 800; // Approximate canvas height
	
	// Clear all positions
	const clearNodePositions = (n: TreeNode) => {
		delete (n as any).fx;
		delete (n as any).fy;
		for (const c of (n.children || [])) {
			clearNodePositions(c);
		}
	};
	clearNodePositions(root);
	
	// Position root
	(root as any).fx = marginX;
	(root as any).fy = canvasHeight / 2;
	
	// Position nodes by depth
	const maxDepth = Math.max(...Array.from(nodesByDepth.keys()));
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
	
	// Trigger re-render by creating a new reference
	parsed.value = { ...parsed.value };
}
</script>

<style scoped>
</style>


