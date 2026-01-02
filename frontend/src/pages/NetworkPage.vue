<template>
  <!-- Loading State -->
  <div
    v-if="loading"
    class="h-screen flex items-center justify-center bg-white dark:bg-slate-950 relative overflow-hidden transition-colors"
  >
    <!-- Animated background elements -->
    <div class="absolute inset-0 overflow-hidden pointer-events-none">
      <div
        class="absolute top-1/4 -left-20 w-72 h-72 bg-cyan-400/10 dark:bg-cyan-500/10 rounded-full blur-3xl animate-pulse"
      />
      <div
        class="absolute bottom-1/4 -right-20 w-80 h-80 bg-blue-400/10 dark:bg-blue-500/10 rounded-full blur-3xl animate-pulse"
        style="animation-delay: 1s"
      />
    </div>

    <div class="relative text-center">
      <!-- App Logo -->
      <div
        class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-[#0fb685] to-[#0994ae] rounded-2xl shadow-lg shadow-[#0fb685]/30 mb-6"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-8 w-8 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
      </div>

      <!-- App Name -->
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white tracking-tight mb-2">
        Cartographer
      </h1>

      <!-- Loading Indicator -->
      <div class="flex items-center justify-center gap-2 mt-4">
        <div class="flex gap-1">
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 0ms"
          ></span>
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 150ms"
          ></span>
          <span
            class="w-2 h-2 rounded-full bg-cyan-500 animate-bounce"
            style="animation-delay: 300ms"
          ></span>
        </div>
      </div>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-3">Loading network...</p>
    </div>
  </div>

  <!-- Error State -->
  <div
    v-else-if="error"
    class="h-screen flex items-center justify-center bg-white dark:bg-slate-950 transition-colors"
  >
    <div class="text-center max-w-md px-6">
      <div
        class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-red-100 dark:bg-red-500/10 flex items-center justify-center"
      >
        <svg
          class="w-8 h-8 text-red-500 dark:text-red-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      </div>
      <h2 class="text-xl font-bold text-slate-900 dark:text-white mb-2">Failed to load network</h2>
      <p class="text-slate-500 dark:text-slate-400 mb-6">{{ error }}</p>
      <router-link
        to="/"
        class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-white rounded-lg transition-colors border border-slate-200 dark:border-transparent"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10 19l-7-7m0 0l7-7m-7 7h18"
          />
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
    :networkOwnerId="network.owner_id"
    :canWriteNetwork="canWrite"
    :isNetworkOwner="network.is_owner"
  />
</template>

<script lang="ts" setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useNetworks, type Network } from '../composables/useNetworks';
import { useAuth } from '../composables/useAuth';
import MainApp from '../components/MainApp.vue';

const route = useRoute();
const router = useRouter();
const { getNetwork, canWriteNetwork } = useNetworks();
const { isAuthenticated, verifySession } = useAuth();

const network = ref<Network | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

const canWrite = computed(() => {
  if (!network.value) return false;
  return canWriteNetwork(network.value);
});

async function ensureAuthenticated(): Promise<boolean> {
  // If we have a token stored, verify it's still valid on the server
  // This handles the case where the backend restarted and sessions were lost
  if (isAuthenticated.value) {
    const isValid = await verifySession();
    if (!isValid) {
      // Session is no longer valid on server, redirect to home for re-login
      console.log('[NetworkPage] Session invalid, redirecting to home');
      router.replace('/');
      return false;
    }
    return true;
  }

  // No auth token at all, redirect to home for login
  console.log('[NetworkPage] Not authenticated, redirecting to home');
  router.replace('/');
  return false;
}

async function loadNetwork() {
  const id = route.params.id as string;
  // Validate UUID format
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  if (!id || !uuidRegex.test(id)) {
    error.value = 'Invalid network ID';
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = null;

  // First ensure we're authenticated
  const authenticated = await ensureAuthenticated();
  if (!authenticated) {
    loading.value = false;
    return;
  }

  try {
    network.value = await getNetwork(id);
  } catch (e: unknown) {
    // Check if this is an auth error - redirect to home instead of showing error
    const err = e as { status?: number; response?: { status?: number }; message?: string };
    const status = err.status || err.response?.status;
    const isAuthError =
      status === 401 ||
      status === 403 ||
      err.message?.toLowerCase().includes('not authenticated') ||
      err.message?.toLowerCase().includes('unauthorized') ||
      err.message?.toLowerCase().includes('authentication');

    if (isAuthError) {
      console.log('[NetworkPage] Auth error loading network, redirecting to home');
      router.replace('/');
      return;
    }
    error.value = err.message || 'Network not found';
    network.value = null;
  } finally {
    loading.value = false;
  }
}

// Watch for route changes (if navigating between networks)
watch(
  () => route.params.id,
  () => {
    if (route.params.id) {
      loadNetwork();
    }
  }
);

onMounted(() => {
  loadNetwork();
});
</script>
