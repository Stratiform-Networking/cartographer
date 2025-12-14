<template>
	<Teleport to="body">
		<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm" @click.self="$emit('close')">
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col">
				<!-- Header -->
				<div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 rounded-t-xl">
					<div class="flex items-center gap-3">
						<div class="w-9 h-9 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-violet-600 dark:text-violet-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
							</svg>
						</div>
						<div>
							<h2 class="text-lg font-semibold text-slate-900 dark:text-white">Notification Settings</h2>
							<p class="text-xs text-slate-500 dark:text-slate-400">Configure how you receive alerts</p>
						</div>
					</div>
					<button
						@click="$emit('close')"
						class="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
					>
						<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>

				<!-- Tab Navigation -->
				<div class="flex border-b border-slate-200 dark:border-slate-700 px-6" v-if="networkId !== null">
					<button
						@click="activeTab = 'network'"
						:class="[
							'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
							activeTab === 'network'
								? 'border-violet-500 text-violet-600 dark:text-violet-400'
								: 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
						]"
					>
						<span class="flex items-center gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
							</svg>
							Network
						</span>
					</button>
					<button
						@click="activeTab = 'global'"
						:class="[
							'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
							activeTab === 'global'
								? 'border-blue-500 text-blue-600 dark:text-blue-400'
								: 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
						]"
					>
						<span class="flex items-center gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
							</svg>
							Global
						</span>
					</button>
				</div>

				<!-- Content -->
				<div class="flex-1 overflow-auto p-6 space-y-6">
					<!-- Loading State -->
					<div v-if="isLoading" class="flex items-center justify-center py-12">
						<svg class="animate-spin h-8 w-8 text-violet-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
					</div>

					<template v-else>
						<!-- Network Tab -->
						<template v-if="activeTab === 'network' && networkId !== null">
							<NetworkSettings
								:network-id="networkId"
								:preferences="networkPrefs"
								:service-status="serviceStatus"
								:discord-link="discordLink"
								:anomaly-stats="anomalyStats"
								@update="handleNetworkUpdate"
								@test-email="handleTestEmail"
								@test-discord="handleTestDiscord"
								@link-discord="handleLinkDiscord"
								@unlink-discord="handleUnlinkDiscord"
							/>
						</template>

						<!-- Global Tab -->
						<template v-if="activeTab === 'global'">
							<GlobalSettings
								:preferences="globalPrefs"
								:service-status="serviceStatus"
								:discord-link="discordLink"
								@update="handleGlobalUpdate"
								@test-email="handleTestGlobalEmail"
								@test-discord="handleTestGlobalDiscord"
								@link-discord="handleLinkDiscord"
								@unlink-discord="handleUnlinkDiscord"
							/>
						</template>
					</template>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useUserNotifications } from '../composables/useUserNotifications';
import NetworkSettings from './NotificationSettingsNetwork.vue';
import GlobalSettings from './NotificationSettingsGlobal.vue';

const props = defineProps<{
	networkId: number | null;
}>();

const emit = defineEmits<{
	close: [];
}>();

const activeTab = ref<'network' | 'global'>(props.networkId !== null ? 'network' : 'global');
const {
	isLoading,
	error,
	getNetworkPreferences,
	updateNetworkPreferences,
	getGlobalPreferences,
	updateGlobalPreferences,
	testNetworkNotification,
	testGlobalNotification,
	initiateDiscordOAuth,
	getDiscordLink,
	unlinkDiscord,
	getServiceStatus,
	getAnomalyStats,
} = useUserNotifications();

const networkPrefs = ref<any>(null);
const globalPrefs = ref<any>(null);
const serviceStatus = ref<any>(null);
const discordLink = ref<any>(null);
const anomalyStats = ref<any>(null);

async function loadData() {
	try {
		// Load service status
		serviceStatus.value = await getServiceStatus();
		
		// Load Discord link
		discordLink.value = await getDiscordLink();
		
		// Load network preferences if in network
		if (props.networkId !== null) {
			networkPrefs.value = await getNetworkPreferences(props.networkId);
			try {
				anomalyStats.value = await getAnomalyStats(props.networkId);
			} catch (e) {
				// Anomaly stats might not be available
				console.warn('Could not load anomaly stats:', e);
			}
		}
		
		// Always load global preferences
		globalPrefs.value = await getGlobalPreferences();
	} catch (e) {
		console.error('Failed to load notification settings:', e);
	}
}

async function handleNetworkUpdate(update: any) {
	if (props.networkId === null) return;
	try {
		networkPrefs.value = await updateNetworkPreferences(props.networkId, update);
	} catch (e) {
		console.error('Failed to update network preferences:', e);
	}
}

async function handleGlobalUpdate(update: any) {
	try {
		globalPrefs.value = await updateGlobalPreferences(update);
	} catch (e) {
		console.error('Failed to update global preferences:', e);
	}
}

async function handleTestEmail() {
	if (props.networkId === null) return;
	try {
		const result = await testNetworkNotification(props.networkId, 'email');
		alert(result.success ? result.message : result.error || 'Test failed');
	} catch (e: any) {
		alert('Failed to send test email: ' + (e.message || 'Unknown error'));
	}
}

async function handleTestDiscord() {
	if (props.networkId === null) return;
	try {
		const result = await testNetworkNotification(props.networkId, 'discord');
		alert(result.success ? result.message : result.error || 'Test failed');
	} catch (e: any) {
		alert('Failed to send test Discord notification: ' + (e.message || 'Unknown error'));
	}
}

async function handleTestGlobalEmail() {
	try {
		const result = await testGlobalNotification('email');
		alert(result.success ? result.message : result.error || 'Test failed');
	} catch (e: any) {
		alert('Failed to send test email: ' + (e.message || 'Unknown error'));
	}
}

async function handleTestGlobalDiscord() {
	try {
		const result = await testGlobalNotification('discord');
		alert(result.success ? result.message : result.error || 'Test failed');
	} catch (e: any) {
		alert('Failed to send test Discord notification: ' + (e.message || 'Unknown error'));
	}
}

async function handleLinkDiscord() {
	try {
		const { authorization_url } = await initiateDiscordOAuth();
		const popup = window.open(authorization_url, 'discord_oauth', 'width=600,height=700');
		
		if (!popup) {
			alert('Popup blocked. Please allow popups for this site and try again.');
			return;
		}
		
		let linkCompleted = false;
		
		// Listen for message from popup
		const messageHandler = async (event: MessageEvent) => {
			if (event.origin !== window.location.origin) {
				return;
			}
			
			if (event.data && event.data.type === 'discord_oauth_callback') {
				window.removeEventListener('message', messageHandler);
				linkCompleted = true;
				
				if (event.data.status === 'success') {
					// Reload all data once
					await loadData();
				} else {
					alert('Discord linking failed: ' + (event.data.message || 'Unknown error'));
				}
			}
		};
		
		window.addEventListener('message', messageHandler);
		
		// Fallback: Check when popup closes (instead of aggressive polling)
		const checkPopupClosed = setInterval(async () => {
			if (popup.closed) {
				clearInterval(checkPopupClosed);
				window.removeEventListener('message', messageHandler);
				
				// Only reload if we haven't already handled via postMessage
				if (!linkCompleted) {
					await loadData();
				}
			}
		}, 500);
		
		// Stop checking after 5 minutes
		setTimeout(() => {
			clearInterval(checkPopupClosed);
			window.removeEventListener('message', messageHandler);
		}, 300000);
	} catch (e: any) {
		alert('Failed to initiate Discord OAuth: ' + (e.message || 'Unknown error'));
	}
}

async function handleUnlinkDiscord() {
	if (!confirm('Are you sure you want to unlink your Discord account?')) {
		return;
	}
	
	try {
		await unlinkDiscord();
		// Reload all data to get updated preferences and discord link status
		await loadData();
	} catch (e: any) {
		alert('Failed to unlink Discord: ' + (e.message || 'Unknown error'));
	}
}

// Note: OAuth callback handling is now done via postMessage in App.vue
// This watch is kept for backwards compatibility but shouldn't be needed

onMounted(() => {
	loadData();
});
</script>
