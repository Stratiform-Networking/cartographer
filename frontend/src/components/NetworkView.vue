<template>
	<!-- Loading State -->
	<div v-if="loading" class="h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
		<div class="text-center">
			<svg class="animate-spin h-12 w-12 text-cyan-500 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
			</svg>
			<p class="text-slate-400">Loading network...</p>
		</div>
	</div>

	<!-- Error State -->
	<div v-else-if="error" class="h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
		<div class="text-center max-w-md">
			<div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-500/10 flex items-center justify-center">
				<svg class="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
			</div>
			<h2 class="text-xl font-bold text-white mb-2">Failed to load network</h2>
			<p class="text-slate-400 mb-6">{{ error }}</p>
			<router-link
				to="/"
				class="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
				</svg>
				Back to Networks
			</router-link>
		</div>
	</div>

	<!-- Network Loaded - Render MainApp -->
	<MainApp
		v-else-if="network"
		:networkId="network.id"
		:networkName="network.name"
		:canWriteNetwork="canWrite"
	/>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useNetworks, type Network } from "../composables/useNetworks";
import MainApp from "./MainApp.vue";

const route = useRoute();
const router = useRouter();
const { getNetwork, canWriteNetwork } = useNetworks();

const network = ref<Network | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const canWrite = computed(() => {
	if (!network.value) return false;
	return canWriteNetwork(network.value);
});

async function loadNetwork() {
	const id = Number(route.params.id);
	if (isNaN(id)) {
		error.value = "Invalid network ID";
		loading.value = false;
		return;
	}

	loading.value = true;
	error.value = null;

	try {
		network.value = await getNetwork(id);
	} catch (e: any) {
		error.value = e.message || "Network not found";
		network.value = null;
	} finally {
		loading.value = false;
	}
}

// Watch for route changes (if navigating between networks)
watch(() => route.params.id, () => {
	if (route.params.id) {
		loadNetwork();
	}
});

onMounted(() => {
	loadNetwork();
});
</script>

