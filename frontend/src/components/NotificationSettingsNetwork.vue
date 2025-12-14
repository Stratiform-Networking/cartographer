<template>
	<div class="space-y-6">
		<!-- Delivery Channels -->
		<div class="space-y-4">
			<h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
				</svg>
				Delivery Channels
			</h3>
			
			<!-- Email -->
			<div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
				<div class="flex items-center justify-between mb-3">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Email</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							{{ serviceStatus?.email_configured ? 'Using your account email' : 'Email service not configured' }}
						</p>
					</div>
					<button
						@click="toggleEmail"
						:disabled="!serviceStatus?.email_configured"
						class="relative w-12 h-7 rounded-full transition-colors disabled:opacity-50"
						:class="preferences?.email_enabled && serviceStatus?.email_configured ? 'bg-blue-500' : 'bg-slate-300 dark:bg-slate-600'"
					>
						<span
							class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
							:class="preferences?.email_enabled && serviceStatus?.email_configured ? 'translate-x-5' : ''"
						></span>
					</button>
				</div>
				<button
					v-if="preferences?.email_enabled"
					@click="$emit('test-email')"
					class="px-4 py-2 text-sm bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors"
				>
					Send Test Email
				</button>
			</div>
			
			<!-- Discord -->
			<div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
				<div class="flex items-center justify-between mb-3">
					<div>
						<p class="font-medium text-slate-900 dark:text-white">Discord</p>
						<p class="text-sm text-slate-500 dark:text-slate-400">
							{{ discordLink?.linked ? `Linked: @${discordLink.discord_username}` : 'Link your Discord account' }}
						</p>
					</div>
					<button
						@click="toggleDiscord"
						:disabled="!discordLink?.linked"
						class="relative w-12 h-7 rounded-full transition-colors disabled:opacity-50"
						:class="preferences?.discord_enabled && discordLink?.linked ? 'bg-indigo-500' : 'bg-slate-300 dark:bg-slate-600'"
					>
						<span
							class="absolute top-0.5 left-0.5 w-6 h-6 bg-white rounded-full shadow transition-transform"
							:class="preferences?.discord_enabled && discordLink?.linked ? 'translate-x-5' : ''"
						></span>
					</button>
				</div>
				<div class="flex gap-2">
					<button
						v-if="!discordLink?.linked"
						@click="$emit('link-discord')"
						class="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
					>
						Link Discord Account
					</button>
					<button
						v-else
						@click="$emit('unlink-discord')"
						class="px-4 py-2 text-sm bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
					>
						Unlink
					</button>
					<button
						v-if="preferences?.discord_enabled && discordLink?.linked"
						@click="$emit('test-discord')"
						class="px-4 py-2 text-sm bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded-lg hover:bg-indigo-200 dark:hover:bg-indigo-900/50 transition-colors"
					>
						Send Test
					</button>
				</div>
			</div>
		</div>
		
		<!-- Notification Types -->
		<div class="space-y-4">
			<div>
				<h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
					</svg>
					Notification Types
				</h3>
				<p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Enable/disable notification types and customize their priority. Click the priority badge to change it.</p>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<div
					v-for="type in networkNotificationTypes"
					:key="type.value"
					@click="toggleType(type.value)"
					class="relative p-4 rounded-lg border cursor-pointer transition-all duration-200"
					:class="isTypeEnabled(type.value) 
						? 'bg-violet-500/10 border-violet-500/50 hover:border-violet-400/70' 
						: 'bg-slate-800 border-slate-600 hover:border-slate-500'"
				>
					<!-- Priority Badge -->
					<button
						@click.stop="cycleTypePriority(type.value)"
						class="absolute top-3 right-3 px-2.5 py-1 text-xs font-medium rounded-md transition-colors"
						:class="getPriorityBadgeClass(getTypePriority(type.value))"
					>
						{{ capitalizeFirst(getTypePriority(type.value)) }}
					</button>
					
					<!-- Content -->
					<div class="flex items-start gap-3 pr-16">
						<span class="text-xl flex-shrink-0">{{ type.icon }}</span>
						<div class="min-w-0">
							<p class="font-medium text-white truncate">{{ type.label }}</p>
							<p class="text-xs text-slate-400 mt-0.5 line-clamp-2">{{ type.description }}</p>
						</div>
					</div>
				</div>
			</div>
		</div>
		
		<!-- Filters -->
		<div class="space-y-4">
			<h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
				<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
				</svg>
				Filters & Limits
			</h3>
			<div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 space-y-4">
				<!-- Minimum Priority -->
				<div>
					<label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
						Minimum Priority
					</label>
					<div class="grid grid-cols-4 gap-2">
						<button
							v-for="priority in priorityOptions"
							:key="priority.value"
							@click="updateMinimumPriority(priority.value)"
							class="px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 border"
							:class="(preferences?.minimum_priority || 'low') === priority.value
								? getPriorityButtonActiveClass(priority.value)
								: 'bg-slate-700/50 border-slate-600 text-slate-400 hover:bg-slate-700 hover:text-slate-300'"
						>
							{{ priority.label }}
						</button>
					</div>
				</div>
				
				<!-- Quiet Hours -->
				<div class="space-y-3">
					<div class="flex items-center justify-between">
						<label class="text-sm font-medium text-slate-700 dark:text-slate-300">
							Quiet Hours
						</label>
						<button
							@click="toggleQuietHours"
							class="relative w-11 h-6 rounded-full transition-colors"
							:class="preferences?.quiet_hours_enabled ? 'bg-violet-500' : 'bg-slate-300 dark:bg-slate-600'"
						>
							<span
								class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
								:class="preferences?.quiet_hours_enabled ? 'translate-x-5' : ''"
							></span>
						</button>
					</div>
					
					<template v-if="preferences?.quiet_hours_enabled">
						<div class="grid grid-cols-2 gap-3">
							<div>
								<label class="block text-xs text-slate-500 dark:text-slate-400 mb-1">Start</label>
								<input
									type="time"
									:value="preferences?.quiet_hours_start || '22:00'"
									@change="updateQuietHoursStart(($event.target as HTMLInputElement).value)"
									class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
								/>
							</div>
							<div>
								<label class="block text-xs text-slate-500 dark:text-slate-400 mb-1">End</label>
								<input
									type="time"
									:value="preferences?.quiet_hours_end || '08:00'"
									@change="updateQuietHoursEnd(($event.target as HTMLInputElement).value)"
									class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
								/>
							</div>
						</div>
						<div>
							<label class="block text-xs text-slate-500 dark:text-slate-400 mb-1">Timezone</label>
							<select
								:value="preferences?.quiet_hours_timezone || 'UTC'"
								@change="updateQuietHoursTimezone(($event.target as HTMLSelectElement).value)"
								class="w-full px-3 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white"
							>
								<option value="UTC">UTC</option>
								<option value="America/New_York">Eastern Time</option>
								<option value="America/Chicago">Central Time</option>
								<option value="America/Denver">Mountain Time</option>
								<option value="America/Los_Angeles">Pacific Time</option>
								<option value="Europe/London">London</option>
								<option value="Europe/Paris">Paris</option>
								<option value="Asia/Tokyo">Tokyo</option>
							</select>
						</div>
						<div>
							<label class="block text-xs text-slate-500 dark:text-slate-400 mb-2">Pass-through Alerts</label>
							<div class="grid grid-cols-5 gap-2">
								<button
									v-for="bypass in bypassOptions"
									:key="bypass.value"
									@click="updateQuietHoursBypass(bypass.value)"
									class="px-2 py-2 text-xs font-medium rounded-lg transition-all duration-200 border"
									:class="(preferences?.quiet_hours_bypass_priority || '') === bypass.value
										? getBypassButtonActiveClass(bypass.value)
										: 'bg-slate-700/50 border-slate-600 text-slate-400 hover:bg-slate-700 hover:text-slate-300'"
								>
									{{ bypass.label }}
								</button>
							</div>
						</div>
					</template>
				</div>
			</div>
		</div>
		
		<!-- Anomaly Detection Stats -->
		<div class="space-y-4" v-if="anomalyStats">
			<h3 class="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
				Anomaly Detection
			</h3>
			<div class="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
				<div class="grid grid-cols-3 gap-4">
					<div>
						<p class="text-xs text-slate-500 dark:text-slate-400">Devices Tracked</p>
						<p class="text-lg font-semibold text-slate-900 dark:text-white">{{ anomalyStats.devices_tracked || 0 }}</p>
					</div>
					<div>
						<p class="text-xs text-slate-500 dark:text-slate-400">Anomalies (24h)</p>
						<p class="text-lg font-semibold text-slate-900 dark:text-white">{{ anomalyStats.anomalies_detected_24h || 0 }}</p>
					</div>
					<div>
						<p class="text-xs text-slate-500 dark:text-slate-400">Model Status</p>
						<p class="text-lg font-semibold text-slate-900 dark:text-white">{{ anomalyStats.is_trained ? 'Trained' : 'Training' }}</p>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
const props = defineProps<{
	networkId: number;
	preferences: any;
	serviceStatus: any;
	discordLink: any;
	anomalyStats: any;
}>();

const emit = defineEmits<{
	update: [update: any];
	'test-email': [];
	'test-discord': [];
	'link-discord': [];
	'unlink-discord': [];
}>();

const priorityOptions = [
	{ value: 'low', label: 'Low' },
	{ value: 'medium', label: 'Medium' },
	{ value: 'high', label: 'High' },
	{ value: 'critical', label: 'Critical' },
];

const bypassOptions = [
	{ value: '', label: 'None' },
	{ value: 'low', label: 'Low+' },
	{ value: 'medium', label: 'Med+' },
	{ value: 'high', label: 'High+' },
	{ value: 'critical', label: 'Crit' },
];

const networkNotificationTypes = [
	{ value: 'device_offline', label: 'Device Offline', icon: '🔴', description: 'When a device stops responding', defaultPriority: 'high' },
	{ value: 'device_online', label: 'Device Online', icon: '🟢', description: 'When a device comes back online', defaultPriority: 'low' },
	{ value: 'device_degraded', label: 'Device Degraded', icon: '🟡', description: 'When a device has degraded performance', defaultPriority: 'medium' },
	{ value: 'anomaly_detected', label: 'Anomaly Detected', icon: '⚠️', description: 'ML-detected unusual behavior', defaultPriority: 'high' },
	{ value: 'high_latency', label: 'High Latency', icon: '🐌', description: 'Unusual latency spikes', defaultPriority: 'medium' },
	{ value: 'packet_loss', label: 'Packet Loss', icon: '📉', description: 'Significant packet loss', defaultPriority: 'medium' },
	{ value: 'isp_issue', label: 'ISP Issue', icon: '🌐', description: 'Internet connectivity problems', defaultPriority: 'high' },
	{ value: 'security_alert', label: 'Security Alert', icon: '🔒', description: 'Security-related notifications', defaultPriority: 'critical' },
	{ value: 'scheduled_maintenance', label: 'Maintenance', icon: '🔧', description: 'Planned maintenance notices', defaultPriority: 'low' },
	{ value: 'system_status', label: 'System Status', icon: 'ℹ️', description: 'General system updates', defaultPriority: 'low' },
];

function capitalizeFirst(str: string): string {
	return str.charAt(0).toUpperCase() + str.slice(1);
}

function getPriorityBadgeClass(priority: string): string {
	switch (priority) {
		case 'low':
			return 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30';
		case 'medium':
			return 'bg-yellow-500/20 text-yellow-400 hover:bg-yellow-500/30';
		case 'high':
			return 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30';
		case 'critical':
			return 'bg-red-500/20 text-red-400 hover:bg-red-500/30';
		default:
			return 'bg-slate-500/20 text-slate-400 hover:bg-slate-500/30';
	}
}

function getPriorityButtonActiveClass(priority: string): string {
	switch (priority) {
		case 'low':
			return 'bg-emerald-500/30 border-emerald-500 text-emerald-300';
		case 'medium':
			return 'bg-yellow-500/30 border-yellow-500 text-yellow-300';
		case 'high':
			return 'bg-orange-500/30 border-orange-500 text-orange-300';
		case 'critical':
			return 'bg-red-500/30 border-red-500 text-red-300';
		default:
			return 'bg-slate-500/30 border-slate-500 text-slate-300';
	}
}

function getBypassButtonActiveClass(priority: string): string {
	switch (priority) {
		case 'low':
			return 'bg-emerald-500/30 border-emerald-500 text-emerald-300';
		case 'medium':
			return 'bg-yellow-500/30 border-yellow-500 text-yellow-300';
		case 'high':
			return 'bg-orange-500/30 border-orange-500 text-orange-300';
		case 'critical':
			return 'bg-red-500/30 border-red-500 text-red-300';
		default:
			return 'bg-slate-500/30 border-slate-500 text-slate-300';
	}
}

function isTypeEnabled(type: string): boolean {
	return props.preferences?.enabled_types?.includes(type) ?? true;
}

function getTypePriority(type: string): string {
	const priorities = props.preferences?.type_priorities || {};
	return priorities[type] || networkNotificationTypes.find(t => t.value === type)?.defaultPriority || 'medium';
}

function cycleTypePriority(type: string) {
	const currentPriority = getTypePriority(type);
	const priorities = ['low', 'medium', 'high', 'critical'];
	const currentIndex = priorities.indexOf(currentPriority);
	const nextIndex = (currentIndex + 1) % priorities.length;
	updateTypePriority(type, priorities[nextIndex]);
}

function toggleEmail() {
	emit('update', { email_enabled: !props.preferences?.email_enabled });
}

function toggleDiscord() {
	if (!props.discordLink?.linked) return;
	emit('update', { discord_enabled: !props.preferences?.discord_enabled });
}

function toggleType(type: string) {
	const enabled = props.preferences?.enabled_types || [];
	const newEnabled = isTypeEnabled(type)
		? enabled.filter((t: string) => t !== type)
		: [...enabled, type];
	emit('update', { enabled_types: newEnabled });
}

function updateTypePriority(type: string, priority: string) {
	const priorities = { ...(props.preferences?.type_priorities || {}) };
	if (priority === networkNotificationTypes.find(t => t.value === type)?.defaultPriority) {
		delete priorities[type];
	} else {
		priorities[type] = priority;
	}
	emit('update', { type_priorities: priorities });
}

function updateMinimumPriority(priority: string) {
	emit('update', { minimum_priority: priority });
}

function toggleQuietHours() {
	emit('update', { quiet_hours_enabled: !props.preferences?.quiet_hours_enabled });
}

function updateQuietHoursStart(start: string) {
	emit('update', { quiet_hours_start: start });
}

function updateQuietHoursEnd(end: string) {
	emit('update', { quiet_hours_end: end });
}

function updateQuietHoursTimezone(timezone: string) {
	emit('update', { quiet_hours_timezone: timezone });
}

function updateQuietHoursBypass(priority: string) {
	emit('update', { quiet_hours_bypass_priority: priority || null });
}
</script>
