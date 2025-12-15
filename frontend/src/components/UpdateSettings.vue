<template>
	<Teleport to="body">
		<Transition
			enter-active-class="transition ease-out duration-200"
			enter-from-class="opacity-0"
			enter-to-class="opacity-100"
			leave-active-class="transition ease-in duration-150"
			leave-from-class="opacity-100"
			leave-to-class="opacity-0"
		>
			<div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
				<Transition
					enter-active-class="transition ease-out duration-200"
					enter-from-class="opacity-0 scale-95"
					enter-to-class="opacity-100 scale-100"
					leave-active-class="transition ease-in duration-150"
					leave-from-class="opacity-100 scale-100"
					leave-to-class="opacity-0 scale-95"
				>
					<div v-if="isOpen" class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200/80 dark:border-slate-800/80">
						<!-- Header -->
						<div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl">
							<div class="flex items-center gap-2">
								<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-cyan-500 dark:text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
								</svg>
								<div>
									<h2 class="font-semibold text-slate-800 dark:text-slate-100">Application Updates</h2>
									<p class="text-xs text-slate-500 dark:text-slate-400">Check for updates and configure notifications</p>
								</div>
							</div>
							<button
								@click="$emit('close')"
								class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
							>
								<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
								</svg>
							</button>
						</div>

						<!-- Content -->
						<div class="p-4 space-y-4">
							<!-- Current Version & Check Button -->
							<div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/40 rounded-lg border border-slate-200/80 dark:border-slate-700/50">
								<div>
									<p class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">Current Version</p>
									<p class="text-xl font-bold text-slate-800 dark:text-slate-100">
										v{{ versionInfo.current }}
									</p>
								</div>
								<button
									@click="checkForUpdatesManual"
									:disabled="isCheckingVersion"
									class="px-3 py-2 text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg shadow-sm shadow-cyan-500/20 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
								>
									<svg 
										xmlns="http://www.w3.org/2000/svg" 
										class="h-4 w-4"
										:class="{ 'animate-spin': isCheckingVersion }"
										fill="none" 
										viewBox="0 0 24 24" 
										stroke="currentColor" 
										stroke-width="2"
									>
										<path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
									</svg>
									{{ isCheckingVersion ? 'Checking...' : 'Check for Updates' }}
								</button>
							</div>

							<!-- Update Check Result -->
							<Transition
								enter-active-class="transition ease-out duration-300"
								enter-from-class="opacity-0 -translate-y-2"
								enter-to-class="opacity-100 translate-y-0"
								leave-active-class="transition ease-in duration-200"
								leave-from-class="opacity-100 translate-y-0"
								leave-to-class="opacity-0 -translate-y-2"
							>
								<div 
									v-if="updateCheckResult" 
									class="p-3 rounded-lg"
									:class="updateCheckResult.has_update 
										? 'bg-cyan-50 dark:bg-cyan-900/15 border border-cyan-200/80 dark:border-cyan-800/30' 
										: 'bg-emerald-50 dark:bg-emerald-900/15 border border-emerald-200/80 dark:border-emerald-800/30'"
								>
									<div class="flex items-start gap-3">
										<!-- Icon -->
										<div 
											class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
											:class="updateCheckResult.has_update 
												? 'bg-cyan-100 dark:bg-cyan-900/40' 
												: 'bg-emerald-100 dark:bg-emerald-900/40'"
										>
											<svg 
												v-if="updateCheckResult.has_update"
												xmlns="http://www.w3.org/2000/svg" 
												class="h-5 w-5 text-cyan-600 dark:text-cyan-400" 
												fill="none" 
												viewBox="0 0 24 24" 
												stroke="currentColor" 
												stroke-width="2"
											>
												<path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
											</svg>
											<svg 
												v-else
												xmlns="http://www.w3.org/2000/svg" 
												class="h-5 w-5 text-emerald-600 dark:text-emerald-400" 
												fill="none" 
												viewBox="0 0 24 24" 
												stroke="currentColor" 
												stroke-width="2"
											>
												<path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
											</svg>
										</div>

										<!-- Content -->
										<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 flex-wrap">
											<p 
												class="text-sm font-semibold"
												:class="updateCheckResult.has_update 
													? 'text-cyan-700 dark:text-cyan-400' 
													: 'text-emerald-700 dark:text-emerald-400'"
											>
												<template v-if="updateCheckResult.has_update">
													Update Available!
												</template>
												<template v-else>
													You're up to date!
												</template>
											</p>
											<!-- Changelog button inline with title -->
											<a
												v-if="updateCheckResult.has_update"
												:href="CHANGELOG_URL"
												target="_blank"
												rel="noopener noreferrer"
												class="inline-flex items-center gap-1 px-2 py-0.5 bg-cyan-600 hover:bg-cyan-500 text-white text-[10px] font-medium rounded transition-colors"
											>
												<svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
													<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
												</svg>
												Changelog
												<svg xmlns="http://www.w3.org/2000/svg" class="h-2.5 w-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
													<path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
												</svg>
											</a>
											<!-- Notifying spinner -->
											<span v-if="isSendingNotification && updateCheckResult.has_update" class="text-[10px] text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
												<svg class="animate-spin h-2.5 w-2.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
													<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
													<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
												</svg>
												Notifying...
											</span>
										</div>
										<p 
											class="text-xs mt-0.5" 
											:class="updateCheckResult.has_update 
												? 'text-cyan-600 dark:text-cyan-500' 
												: 'text-emerald-600 dark:text-emerald-500'"
										>
											<template v-if="updateCheckResult.has_update">
												<span class="font-medium">v{{ updateCheckResult.latest_version }}</span> is available
												<span class="mx-1">·</span>
												{{ getUpdateTypeLabel(updateCheckResult.update_type) }}
											</template>
											<template v-else>
												Running the latest version (v{{ updateCheckResult.current_version }})
											</template>
										</p>
										</div>
									</div>
								</div>
							</Transition>

							<!-- Update Notification Preferences -->
							<div class="space-y-3">
								<div>
									<h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
										<svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
											<path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
										</svg>
										Update Notifications
									</h3>
									<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
										Choose which types of updates show a notification banner
									</p>
								</div>

								<div class="space-y-2">
									<label 
										v-for="option in updateNotifyOptions" 
										:key="option.value"
										class="flex items-start gap-2.5 p-3 rounded-lg cursor-pointer transition-all duration-200"
										:class="[
											updateNotifyLevel === option.value
												? `bg-slate-50 dark:bg-slate-800/60 border border-slate-300/80 dark:border-slate-600/60 shadow-sm`
												: 'bg-slate-50/50 dark:bg-slate-800/30 border border-slate-200/60 dark:border-slate-700/40 hover:bg-slate-100 dark:hover:bg-slate-800/50'
										]"
									>
										<input
											type="radio"
											:value="option.value"
											v-model="updateNotifyLevel"
											@change="saveUpdateNotifyPreference"
											class="mt-0.5 h-3.5 w-3.5 border-slate-300 dark:border-slate-600 text-cyan-500 focus:ring-cyan-500 focus:ring-offset-0 dark:bg-slate-700"
										/>
										<div class="flex-1 min-w-0">
											<div class="flex items-center gap-2 flex-wrap">
												<span class="text-sm font-medium text-slate-800 dark:text-slate-200">
													{{ option.label }}
												</span>
												<span :class="['text-[10px] px-1.5 py-0.5 rounded font-bold', option.badgeClass]">
													{{ option.badge }}
												</span>
											</div>
											<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
												{{ option.description }}
											</p>
										</div>
									</label>
								</div>
							</div>
						</div>

						<!-- Footer -->
						<div class="px-4 py-3 border-t border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 flex justify-end">
							<button
								@click="$emit('close')"
								class="px-3 py-1.5 text-sm border border-slate-300 dark:border-slate-700 rounded-lg text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
							>
								Done
							</button>
						</div>
					</div>
				</Transition>
			</div>
		</Transition>
	</Teleport>
</template>

<script lang="ts" setup>
import { ref, onMounted } from "vue";
import { useVersionCheck, type VersionType } from "../composables/useVersionCheck";

defineProps<{
	isOpen: boolean;
}>();

defineEmits<{
	(e: "close"): void;
}>();

const {
	versionInfo,
	checkForUpdates,
	setEnabledTypes,
	preferences: versionPreferences,
	isChecking: isCheckingVersion,
	forceShowBanner,
	triggerBackendNotification,
	CHANGELOG_URL,
} = useVersionCheck();

// Track if we're sending backend notification
const isSendingNotification = ref(false);

// Update check result state
const updateCheckResult = ref<{
	success: boolean;
	current_version: string;
	latest_version: string;
	has_update: boolean;
	update_type: string | null;
} | null>(null);

// Update notification level: 'major', 'minor', or 'patch'
const updateNotifyLevel = ref<'major' | 'minor' | 'patch'>('minor');

// Update notification options with styling
const updateNotifyOptions = [
	{
		value: 'major' as const,
		label: 'Major updates only',
		badge: 'x.0.0',
		badgeClass: 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400',
		selectedBg: 'bg-rose-50 dark:bg-rose-900/20',
		selectedBorder: 'border-rose-300 dark:border-rose-700',
		description: 'Significant new features, redesigns, or breaking changes',
	},
	{
		value: 'minor' as const,
		label: 'Minor updates and above',
		badge: '0.x.0',
		badgeClass: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400',
		selectedBg: 'bg-amber-50 dark:bg-amber-900/20',
		selectedBorder: 'border-amber-300 dark:border-amber-700',
		description: 'New features, improvements, and major releases',
	},
	{
		value: 'patch' as const,
		label: 'All updates',
		badge: '0.0.x',
		badgeClass: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400',
		selectedBg: 'bg-emerald-50 dark:bg-emerald-900/20',
		selectedBorder: 'border-emerald-300 dark:border-emerald-700',
		description: 'Every update including bug fixes and patches',
	},
];

// Initialize update notify level from stored preferences
function initUpdateNotifyLevel() {
	const types = versionPreferences.value.enabledTypes;
	if (types.includes('patch')) {
		updateNotifyLevel.value = 'patch';
	} else if (types.includes('minor')) {
		updateNotifyLevel.value = 'minor';
	} else {
		updateNotifyLevel.value = 'major';
	}
}

// Save update notification preference
function saveUpdateNotifyPreference() {
	const level = updateNotifyLevel.value;
	let enabledTypes: VersionType[] = [];
	
	if (level === 'patch') {
		enabledTypes = ['major', 'minor', 'patch'];
	} else if (level === 'minor') {
		enabledTypes = ['major', 'minor'];
	} else {
		enabledTypes = ['major'];
	}
	
	setEnabledTypes(enabledTypes);
}

// Check for updates manually
async function checkForUpdatesManual() {
	updateCheckResult.value = null;
	await checkForUpdates();
	
	const hasUpdate = versionInfo.value.updateAvailable;
	
	// Build result from versionInfo
	updateCheckResult.value = {
		success: true,
		current_version: versionInfo.value.current,
		latest_version: versionInfo.value.latest,
		has_update: hasUpdate,
		update_type: versionInfo.value.updateType,
	};
	
	// If an update is found, show the banner and trigger backend notification
	if (hasUpdate) {
		// Force show the banner (undismiss if previously dismissed)
		forceShowBanner();
		
		// Trigger backend notification to notify all subscribed users
		isSendingNotification.value = true;
		try {
			const result = await triggerBackendNotification();
			if (result.success) {
				console.log(`[UpdateSettings] Notified ${result.users_notified} users about update`);
			}
		} catch (e) {
			console.error("[UpdateSettings] Failed to send backend notification:", e);
		} finally {
			isSendingNotification.value = false;
		}
	}
}

// Get update type label
function getUpdateTypeLabel(updateType: string | null): string {
	switch (updateType) {
		case 'major':
			return 'Major Release';
		case 'minor':
			return 'New Features';
		case 'patch':
			return 'Bug Fixes';
		default:
			return 'Update';
	}
}

onMounted(() => {
	initUpdateNotifyLevel();
});
</script>

