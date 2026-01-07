<template>
  <div class="h-screen flex flex-col overflow-hidden" :class="isDark ? 'bg-slate-950' : 'bg-white'">
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
      <template v-else-if="mapData">
        <NetworkMapEmbed
          ref="networkMapRef"
          :data="mapData"
          :sensitiveMode="sensitiveMode"
          :isDark="isDark"
          :healthMetrics="cachedMetrics"
        />

        <!-- Branding Label (top-left overlay) -->
        <div
          class="absolute top-3 left-3 px-2 py-1 rounded text-xs font-medium backdrop-blur-sm"
          :class="
            isDark
              ? 'bg-slate-900/70 text-slate-300 border border-slate-700/50'
              : 'bg-white/70 text-slate-600 border border-slate-200/50'
          "
        >
          <span>Cartographer</span>
          <template v-if="showOwner && ownerDisplayName">
            <span class="mx-1.5 opacity-40">|</span>
            <span>{{ ownerDisplayName }}</span>
          </template>
        </div>

        <!-- Zoom Controls (right-side vertical overlay) -->
        <div
          class="absolute top-3 right-3 flex flex-col gap-1 p-1 rounded-lg backdrop-blur-sm"
          :class="
            isDark
              ? 'bg-slate-900/70 border border-slate-700/50'
              : 'bg-white/70 border border-slate-200/50'
          "
        >
          <button
            @click="zoomIn"
            class="p-1.5 rounded transition-colors"
            :class="
              isDark
                ? 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/50'
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
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v12m6-6H6" />
            </svg>
          </button>
          <button
            @click="zoomOut"
            class="p-1.5 rounded transition-colors"
            :class="
              isDark
                ? 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/50'
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
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 12H6" />
            </svg>
          </button>
          <div
            class="w-full h-px my-0.5"
            :class="isDark ? 'bg-slate-700/50' : 'bg-slate-200/50'"
          ></div>
          <button
            @click="resetZoom"
            class="p-1.5 rounded transition-colors"
            :class="
              isDark
                ? 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200/50'
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
        </div>
      </template>

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
      sensitiveMode.value = embedData.sensitiveMode || false;
      showOwner.value = embedData.showOwner || false;
      ownerDisplayName.value = embedData.ownerDisplayName || null;

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
