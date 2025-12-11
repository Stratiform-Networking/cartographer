<template>
	<!-- Loading State (checking auth) -->
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

	<!-- Main Dashboard -->
	<div v-else class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
		<!-- Navigation Header -->
		<header class="sticky top-0 z-50 flex items-center h-14 px-4 border-b border-slate-700/50 bg-slate-900/95 backdrop-blur-lg">
			<!-- Left: Branding -->
			<div class="flex items-center gap-3 mr-6">
				<div class="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 shadow-sm">
					<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
					</svg>
				</div>
				<div class="flex flex-col">
					<span class="text-sm font-semibold text-white tracking-tight">Cartographer</span>
					<span class="text-[10px] text-slate-500 -mt-0.5">Networks</span>
				</div>
			</div>

			<!-- Center: Spacer -->
			<div class="flex-1"></div>

			<!-- Right: User Menu -->
			<UserMenu @logout="onLogout" @manageUsers="showUserManagement = true" />
		</header>

		<!-- Main Content -->
		<main class="relative z-10 pt-8 pb-12 px-6">
			<div class="max-w-6xl mx-auto">
				<!-- Header -->
				<div class="mb-10">
					<h1 class="text-3xl font-bold text-white mb-2">
						Your Networks
					</h1>
					<p class="text-slate-400">Select a network to view and manage, or create a new one.</p>
				</div>

				<!-- Loading Networks -->
				<div v-if="networksLoading" class="flex items-center justify-center py-20">
					<svg class="w-8 h-8 text-cyan-400 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
					</svg>
				</div>

				<!-- No Networks State -->
				<div v-else-if="networks.length === 0" class="text-center py-20">
					<div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-slate-800/60 border border-slate-700/50 flex items-center justify-center">
						<svg class="w-10 h-10 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
						</svg>
					</div>
					<h2 class="text-xl font-bold text-white mb-3">No networks yet</h2>
					<p class="text-slate-400 mb-8 max-w-md mx-auto">
						Create your first network to start mapping and monitoring your devices.
					</p>
					<button
						@click="showCreateModal = true"
						class="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98]"
					>
						Create Network
					</button>
				</div>

				<!-- Networks Grid -->
				<div v-else>
					<div class="flex items-center justify-between mb-6">
						<h2 class="text-xl font-semibold text-white">{{ networks.length }} Network{{ networks.length !== 1 ? 's' : '' }}</h2>
						<button
							@click="showCreateModal = true"
							class="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-sm font-medium rounded-lg shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/30 hover:scale-[1.02] active:scale-[0.98]"
						>
							+ New Network
						</button>
					</div>

					<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
						<router-link
							v-for="network in networks"
							:key="network.id"
							:to="`/network/${network.id}`"
							class="block bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-6 hover:bg-slate-800/70 hover:border-slate-600/50 transition-all group"
						>
							<div class="flex items-start justify-between mb-4">
								<div class="w-12 h-12 rounded-xl bg-cyan-500/10 flex items-center justify-center group-hover:bg-cyan-500/20 transition-colors">
									<svg class="w-6 h-6 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
									</svg>
								</div>
								<div class="flex items-center gap-2">
									<span
										v-if="network.is_owner"
										class="px-2 py-0.5 text-xs rounded-full bg-amber-500/20 text-amber-400"
									>
										Owner
									</span>
									<span
										v-else-if="network.permission"
										class="px-2 py-0.5 text-xs rounded-full bg-slate-700 text-slate-400"
									>
										{{ network.permission }}
									</span>
								</div>
							</div>

							<h3 class="text-lg font-semibold text-white mb-1 group-hover:text-cyan-400 transition-colors">{{ network.name }}</h3>
							<p class="text-sm text-slate-400 mb-4 line-clamp-2">{{ network.description || 'No description' }}</p>

							<div class="flex items-center justify-between text-xs text-slate-500">
								<span>Updated {{ formatDate(network.updated_at) }}</span>
								<svg class="w-4 h-4 text-slate-600 group-hover:text-cyan-400 group-hover:translate-x-0.5 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
								</svg>
							</div>
						</router-link>
					</div>
				</div>
			</div>
		</main>

		<!-- Create Network Modal -->
		<Transition
			enter-active-class="transition duration-200"
			enter-from-class="opacity-0"
			enter-to-class="opacity-100"
			leave-active-class="transition duration-150"
			leave-from-class="opacity-100"
			leave-to-class="opacity-0"
		>
			<div v-if="showCreateModal" class="fixed inset-0 z-50 flex items-center justify-center p-6">
				<div class="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" @click="closeCreateModal" />

				<Transition
					enter-active-class="transition duration-200 delay-75"
					enter-from-class="opacity-0 scale-95"
					enter-to-class="opacity-100 scale-100"
					leave-active-class="transition duration-150"
					leave-from-class="opacity-100 scale-100"
					leave-to-class="opacity-0 scale-95"
				>
					<div v-if="showCreateModal" class="relative bg-slate-800/90 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 w-full max-w-md shadow-2xl">
						<h2 class="text-xl font-bold text-white mb-6">Create Network</h2>

						<form @submit.prevent="createNetwork" class="space-y-4">
							<div>
								<label for="networkName" class="block text-sm font-medium text-slate-300 mb-1.5">
									Network Name
								</label>
								<input
									id="networkName"
									v-model="newNetwork.name"
									type="text"
									required
									class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition"
									placeholder="Home Network"
								/>
							</div>

							<div>
								<label for="networkDescription" class="block text-sm font-medium text-slate-300 mb-1.5">
									Description (optional)
								</label>
								<textarea
									id="networkDescription"
									v-model="newNetwork.description"
									rows="3"
									class="w-full px-4 py-2.5 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition resize-none"
									placeholder="Describe this network..."
								></textarea>
							</div>

							<Transition
								enter-active-class="transition duration-200"
								enter-from-class="opacity-0"
								enter-to-class="opacity-100"
							>
								<div v-if="createError" class="p-4 bg-red-900/30 border border-red-500/50 rounded-xl">
									<p class="text-sm text-red-400">{{ createError }}</p>
								</div>
							</Transition>

							<div class="flex gap-3 pt-4">
								<button
									type="button"
									@click="closeCreateModal"
									class="flex-1 py-3 text-slate-400 hover:text-white transition-colors"
								>
									Cancel
								</button>
								<button
									type="submit"
									:disabled="isCreating || !newNetwork.name.trim()"
									class="flex-1 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all hover:shadow-cyan-500/40 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
								>
									<span v-if="isCreating" class="flex items-center justify-center gap-2">
										<svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
										</svg>
										Creating...
									</span>
									<span v-else>Create Network</span>
								</button>
							</div>
						</form>
					</div>
				</Transition>
			</div>
		</Transition>

		<!-- User Management Modal -->
		<UserManagement v-if="showUserManagement" @close="showUserManagement = false" />
	</div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuth } from "../composables/useAuth";
import { useNetworks, type Network } from "../composables/useNetworks";
import SetupWizard from "./SetupWizard.vue";
import LoginScreen from "./LoginScreen.vue";
import UserMenu from "./UserMenu.vue";
import UserManagement from "./UserManagement.vue";

const router = useRouter();
const { isAuthenticated, checkSetupStatus, verifySession } = useAuth();
const { networks, loading: networksLoading, fetchNetworks, createNetwork: createNetworkApi } = useNetworks();

// Auth state
const authLoading = ref(true);
const needsSetup = ref(false);
const showUserManagement = ref(false);

// Modal state
const showCreateModal = ref(false);
const isCreating = ref(false);
const createError = ref("");

const newNetwork = reactive({
	name: "",
	description: "",
});

// Check auth status on mount
async function initAuth() {
	authLoading.value = true;
	try {
		const status = await checkSetupStatus();
		needsSetup.value = !status.is_setup_complete;

		if (status.is_setup_complete) {
			await verifySession();
		}
	} catch (e) {
		console.error("[Auth] Failed to check setup status:", e);
		needsSetup.value = false;
	} finally {
		authLoading.value = false;
	}
}

function onSetupComplete() {
	needsSetup.value = false;
}

function onLoginSuccess() {
	console.log("[HomePage] Login successful");
	loadNetworks();
}

function onLogout() {
	window.location.reload();
}

async function loadNetworks() {
	if (isAuthenticated.value) {
		await fetchNetworks();
	}
}

function formatDate(dateStr: string): string {
	const date = new Date(dateStr);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffMins = Math.floor(diffMs / 60000);
	const diffHours = Math.floor(diffMs / 3600000);
	const diffDays = Math.floor(diffMs / 86400000);

	if (diffMins < 1) return "just now";
	if (diffMins < 60) return `${diffMins}m ago`;
	if (diffHours < 24) return `${diffHours}h ago`;
	if (diffDays < 7) return `${diffDays}d ago`;

	return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function closeCreateModal() {
	showCreateModal.value = false;
	createError.value = "";
	newNetwork.name = "";
	newNetwork.description = "";
}

async function createNetwork() {
	if (!newNetwork.name.trim()) return;

	isCreating.value = true;
	createError.value = "";

	try {
		await createNetworkApi({
			name: newNetwork.name.trim(),
			description: newNetwork.description.trim() || undefined,
		});

		closeCreateModal();
	} catch (e: any) {
		createError.value = e.message || "Failed to create network";
	} finally {
		isCreating.value = false;
	}
}

onMounted(async () => {
	await initAuth();
	if (isAuthenticated.value) {
		await loadNetworks();
	}
});
</script>

<style scoped>
.line-clamp-2 {
	display: -webkit-box;
	-webkit-line-clamp: 2;
	-webkit-box-orient: vertical;
	overflow: hidden;
}
</style>

