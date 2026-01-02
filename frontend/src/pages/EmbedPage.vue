<template>
  <div class="h-screen flex flex-col overflow-hidden" :class="isDark ? 'bg-slate-950' : 'bg-white'">
    <!-- Header -->
    <header
      class="flex items-center justify-between h-12 px-4 border-b shrink-0"
      :class="isDark ? 'border-slate-800/80 bg-slate-950' : 'border-slate-200 bg-white'"
    >
      <!-- Title -->
      <div class="flex items-center gap-2 min-w-0 overflow-hidden">
        <svg
          class="w-5 h-5 shrink-0"
          :class="isDark ? 'text-cyan-400' : 'text-cyan-600'"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
        <span
          class="text-sm font-medium truncate"
          :class="isDark ? 'text-white' : 'text-slate-900'"
        >
          Cartographer
        </span>
      </div>

      <!-- Controls -->
      <div class="flex items-center gap-1.5">
        <!-- Zoom controls -->
        <button
          @click="zoomIn"
          class="p-1.5 rounded-md transition-colors"
          :class="
            isDark
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
          "
          title="Zoom in"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
            />
          </svg>
        </button>
        <button
          @click="zoomOut"
          class="p-1.5 rounded-md transition-colors"
          :class="
            isDark
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
          "
          title="Zoom out"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM7 10h6"
            />
          </svg>
        </button>
        <button
          @click="resetZoom"
          class="p-1.5 rounded-md transition-colors"
          :class="
            isDark
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
          "
          title="Reset view"
        >
          <svg
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          </svg>
        </button>

        <div class="w-px h-5 mx-1" :class="isDark ? 'bg-slate-800' : 'bg-slate-200'"></div>

        <!-- Theme toggle -->
        <button
          @click="isDark = !isDark"
          class="p-1.5 rounded-md transition-colors"
          :class="
            isDark
              ? 'text-slate-400 hover:text-white hover:bg-slate-800'
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
          "
          :title="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        >
          <svg
            v-if="isDark"
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
          <svg
            v-else
            class="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            />
          </svg>
        </button>
      </div>
    </header>

    <!-- Map Content -->
    <div class="flex-1 relative overflow-hidden">
      <!-- Loading -->
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center">
        <div class="text-center">
          <div class="flex gap-1 justify-center mb-3">
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
          <p class="text-sm" :class="isDark ? 'text-slate-400' : 'text-slate-500'">
            Loading network map...
          </p>
        </div>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="absolute inset-0 flex items-center justify-center p-4">
        <div class="text-center max-w-md">
          <div
            class="w-12 h-12 mx-auto mb-3 rounded-full flex items-center justify-center"
            :class="isDark ? 'bg-red-500/20' : 'bg-red-100'"
          >
            <svg class="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <p class="text-sm" :class="isDark ? 'text-slate-300' : 'text-slate-700'">{{ error }}</p>
        </div>
      </div>

      <!-- Network Map -->
      <NetworkMapEmbed
        v-else-if="mapData"
        ref="networkMapRef"
        :root="mapData"
        :sensitiveMode="sensitiveMode"
        :isDark="isDark"
        :cachedMetrics="cachedMetrics"
      />

      <!-- Empty State -->
      <div v-else class="absolute inset-0 flex items-center justify-center">
        <p class="text-slate-500 dark:text-slate-400">No network map available</p>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import * as embedsApi from '../api/embeds';
import type { TreeNode, DeviceMetrics } from '../types/network';
import NetworkMapEmbed from '../components/NetworkMapEmbed.vue';

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

// Embed-specific health monitoring (uses anonymized IDs in sensitive mode)
const embedHealthMetrics = ref<Record<string, DeviceMetrics>>({});
let healthPollInterval: ReturnType<typeof setInterval> | null = null;

// Helper to extract device IDs from the tree (these are anonymized in sensitive mode)
function extractDeviceIds(node: TreeNode): string[] {
  const ids: string[] = [];
  const walk = (n: TreeNode) => {
    // Use the ip field which contains anonymized IDs in sensitive mode
    if (n.ip && n.role !== 'group' && n.monitoringEnabled !== false) {
      ids.push(n.ip);
    }
    for (const child of n.children || []) {
      walk(child);
    }
  };
  walk(node);
  return ids;
}

// Register devices using embed-specific endpoint (server handles IP translation)
async function registerEmbedDevices(deviceIds: string[]): Promise<void> {
  try {
    await embedsApi.registerEmbedDevices(props.embedId, deviceIds);
    await embedsApi.triggerEmbedHealthCheck(props.embedId);
    await fetchEmbedHealthMetrics();
  } catch (err) {
    console.error('[Embed Health] Failed to register devices:', err);
  }
}

// Fetch health metrics using embed-specific endpoint (returns anonymized keys in sensitive mode)
async function fetchEmbedHealthMetrics(): Promise<void> {
  try {
    const metrics = await embedsApi.getEmbedHealthMetrics(props.embedId);
    embedHealthMetrics.value = metrics as Record<string, DeviceMetrics>;
  } catch (err) {
    console.error('[Embed Health] Failed to fetch metrics:', err);
  }
}

function startEmbedHealthPolling(intervalMs: number = 10000): void {
  if (healthPollInterval) return;
  healthPollInterval = setInterval(fetchEmbedHealthMetrics, intervalMs);
}

function stopEmbedHealthPolling(): void {
  if (healthPollInterval) {
    clearInterval(healthPollInterval);
    healthPollInterval = null;
  }
}

// Computed to pass to NetworkMapEmbed
const cachedMetrics = computed(() => embedHealthMetrics.value);

async function loadMapData() {
  loading.value = true;
  error.value = null;

  if (!props.embedId) {
    error.value = 'Invalid embed URL.';
    loading.value = false;
    return;
  }

  try {
    const embedData = await embedsApi.getEmbedData(props.embedId);
    if (embedData.exists && embedData.root) {
      mapData.value = embedData.root;
      sensitiveMode.value = embedData.sensitive_mode || false;
      showOwner.value = false;
      ownerDisplayName.value = null;

      // Register devices for health monitoring using embed-specific endpoint
      // This works with anonymized IDs - the server handles IP translation
      const deviceIds = extractDeviceIds(embedData.root);
      if (deviceIds.length > 0) {
        await registerEmbedDevices(deviceIds);
        // Start polling for health metrics updates
        startEmbedHealthPolling(10000);
      }
    } else {
      error.value = 'No network map has been configured yet.';
    }
  } catch (err: unknown) {
    console.error('Failed to load embed data:', err);
    const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
    if (axiosError.response?.status === 404) {
      error.value = 'Embed not found.';
    } else {
      error.value = axiosError.response?.data?.detail || 'Failed to load network map data.';
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

function resetZoom() {
  networkMapRef.value?.resetZoom();
}

onMounted(() => {
  loadMapData();
});

onBeforeUnmount(() => {
  stopEmbedHealthPolling();
});
</script>
