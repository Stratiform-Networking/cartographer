<template>
  <header
    class="flex items-center h-14 px-4 border-b border-slate-200 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-lg"
  >
    <!-- Left: Branding + Network Name -->
    <div class="flex items-center gap-3 mr-6">
      <!-- Back button (when viewing a specific network) -->
      <router-link
        v-if="networkId"
        to="/"
        class="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800/60 hover:bg-slate-200 dark:hover:bg-slate-700/60 transition-colors"
        title="Back to Networks"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4 text-slate-600 dark:text-slate-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </router-link>
      <div
        class="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-[#0fb685] to-[#0994ae] shadow-sm"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-5 w-5 text-white"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
          />
        </svg>
      </div>
      <div class="flex flex-col">
        <span class="text-sm font-semibold text-slate-900 dark:text-white tracking-tight">
          {{ networkName || 'Cartographer' }}
        </span>
        <span class="text-[10px] text-slate-400 dark:text-slate-500 -mt-0.5">
          {{ networkId ? 'Network Map' : 'Network Mapper' }}
        </span>
      </div>
    </div>

    <!-- Center: Status Message -->
    <div class="flex-1 flex items-center justify-center">
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div
          v-if="message"
          class="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/50"
        >
          <div v-if="loading" class="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></div>
          <div v-else class="w-2 h-2 rounded-full bg-emerald-500"></div>
          <span class="text-xs text-slate-600 dark:text-slate-300">{{ message }}</span>
        </div>
      </Transition>
    </div>

    <!-- Right: Actions -->
    <div class="flex items-center gap-1">
      <!-- Primary Actions Group -->
      <div class="flex items-center gap-1 p-1 rounded-lg bg-slate-100/80 dark:bg-slate-800/50">
        <!-- Scan Button (hidden in cloud deployment and when loading) -->
        <button
          v-if="!isCloudDeployment && !loading"
          @click="runMapper"
          class="group flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-sm shadow-cyan-500/20 disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="!props.canEdit"
          :title="props.canEdit ? 'Scan network and generate map' : 'Write permission required'"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <span>Scan</span>
        </button>

        <!-- Scanning in progress (shown when loading, hidden in cloud deployment) -->
        <div v-else-if="!isCloudDeployment && loading" class="flex items-center gap-1">
          <div
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-amber-500 text-white shadow-sm shadow-amber-500/20"
          >
            <svg
              class="animate-spin h-4 w-4"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                class="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                stroke-width="3"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
            <span>Scanning...</span>
          </div>
          <button
            @click="cancelScan"
            class="flex items-center gap-1 px-2 py-1.5 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-500 transition-colors shadow-sm shadow-red-500/20"
            title="Cancel network scan"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span class="hidden sm:inline">Cancel</span>
          </button>
        </div>

        <button
          @click="saveLayout"
          class="group flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          :class="
            props.hasUnsavedChanges && !saving
              ? 'bg-emerald-600 text-white hover:bg-emerald-500 shadow-sm shadow-emerald-500/20'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700/60'
          "
          :disabled="
            !props.root.children?.length || !props.hasUnsavedChanges || saving || !props.canEdit
          "
          :title="
            props.canEdit
              ? props.hasUnsavedChanges
                ? 'Save changes'
                : 'No unsaved changes'
              : 'Write permission required'
          "
        >
          <svg
            v-if="saving"
            class="animate-spin h-4 w-4"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="3"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"
            />
          </svg>
          <span>{{ saving ? 'Saving' : 'Save' }}</span>
        </button>
      </div>

      <!-- Divider -->
      <div class="w-px h-6 bg-slate-200 dark:bg-slate-700/50 mx-1"></div>

      <!-- File Operations Group -->
      <div class="flex items-center gap-0.5">
        <button
          @click="exportJSON"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="!props.root.children?.length"
          title="Export as JSON file"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          <span class="hidden lg:inline">Export</span>
        </button>

        <label
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs transition-colors"
          :class="
            props.canEdit
              ? 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 cursor-pointer'
              : 'text-slate-400 dark:text-slate-600 cursor-not-allowed'
          "
          :title="props.canEdit ? 'Import JSON file' : 'Write permission required'"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L9 8m4-4v12"
            />
          </svg>
          <span class="hidden lg:inline">Import</span>
          <input
            type="file"
            accept="application/json"
            class="hidden"
            @change="onLoadFile"
            :disabled="!props.canEdit"
          />
        </label>

        <button
          @click="showEmbedGenerator = true"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="!props.root.children?.length"
          title="Generate embeddable map link"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            class="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            stroke-width="2"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
          <span class="hidden lg:inline">Embed</span>
        </button>
      </div>

      <!-- Divider -->
      <div class="w-px h-6 bg-slate-200 dark:bg-slate-700/50 mx-1"></div>

      <!-- Layout Action -->
      <button
        @click="cleanUpLayout"
        class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        :disabled="!props.canEdit || !props.root.children?.length"
        :title="props.canEdit ? 'Auto-arrange nodes in clean layout' : 'Write permission required'"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="2"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
          />
        </svg>
        <span class="hidden lg:inline">Tidy</span>
      </button>

      <!-- Divider -->
      <div class="w-px h-6 bg-slate-200 dark:bg-slate-700/50 mx-1"></div>

      <!-- Settings Group -->
      <div class="flex items-center gap-0.5">
        <!-- Health Monitoring Button -->
        <div class="relative">
          <button
            @click="showHealthSettings = !showHealthSettings"
            class="flex items-center justify-center w-8 h-8 rounded-md transition-colors"
            :class="
              showHealthSettings
                ? 'bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400'
                : 'text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60'
            "
            title="Health monitoring settings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-[18px] w-[18px]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
              />
            </svg>
          </button>

          <!-- Health Settings Dropdown -->
          <Transition
            enter-active-class="transition ease-out duration-100"
            enter-from-class="transform opacity-0 scale-95"
            enter-to-class="transform opacity-100 scale-100"
            leave-active-class="transition ease-in duration-75"
            leave-from-class="transform opacity-100 scale-100"
            leave-to-class="transform opacity-0 scale-95"
          >
            <div
              v-if="showHealthSettings"
              class="absolute right-0 top-full mt-2 w-72 bg-white/95 dark:bg-slate-900/95 backdrop-blur-lg border border-slate-200/80 dark:border-slate-700/50 rounded-xl shadow-xl z-50 overflow-hidden"
            >
              <div
                class="px-4 py-3 bg-slate-50 dark:bg-slate-950/50 border-b border-slate-200/80 dark:border-slate-700/50"
              >
                <h3
                  class="text-sm font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    class="h-4 w-4 text-rose-500"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                    />
                  </svg>
                  Health Monitoring
                </h3>
              </div>

              <div class="p-4 space-y-4">
                <!-- Readonly notice -->
                <div
                  v-if="!props.canEdit"
                  class="p-2 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-700/50 text-xs text-amber-600 dark:text-amber-400 text-center"
                >
                  View only mode — editing disabled
                </div>

                <!-- Enable/Disable -->
                <div class="flex items-center justify-between">
                  <div>
                    <span class="text-sm text-slate-700 dark:text-slate-200"
                      >Passive Monitoring</span
                    >
                    <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                      Ping devices periodically
                    </p>
                  </div>
                  <button
                    @click="toggleMonitoring"
                    class="relative w-11 h-6 rounded-full transition-colors"
                    :class="[
                      healthConfig.enabled ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700',
                      !props.canEdit ? 'opacity-50 cursor-not-allowed' : '',
                    ]"
                    :disabled="!props.canEdit"
                  >
                    <span
                      class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
                      :class="healthConfig.enabled ? 'translate-x-5' : 'translate-x-0'"
                    ></span>
                  </button>
                </div>

                <!-- Check Interval -->
                <div>
                  <label class="text-sm text-slate-700 dark:text-slate-200 block mb-1.5"
                    >Check Interval</label
                  >
                  <select
                    v-model="healthConfig.check_interval_seconds"
                    @change="updateHealthConfig"
                    :disabled="!props.canEdit"
                    class="w-full text-sm border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 dark:text-slate-200 rounded-lg px-3 py-2 focus:ring-2 focus:ring-cyan-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
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
                <div class="flex items-center justify-between">
                  <div>
                    <span class="text-sm text-slate-700 dark:text-slate-200">DNS Lookups</span>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
                      Resolve hostnames for IPs
                    </p>
                  </div>
                  <button
                    @click="toggleDns"
                    class="relative w-11 h-6 rounded-full transition-colors"
                    :class="[
                      healthConfig.include_dns
                        ? 'bg-emerald-500'
                        : 'bg-slate-300 dark:bg-slate-700',
                      !props.canEdit ? 'opacity-50 cursor-not-allowed' : '',
                    ]"
                    :disabled="!props.canEdit"
                  >
                    <span
                      class="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-200"
                      :class="healthConfig.include_dns ? 'translate-x-5' : 'translate-x-0'"
                    ></span>
                  </button>
                </div>
              </div>

              <!-- Status Footer -->
              <div
                class="px-4 py-3 bg-slate-50 dark:bg-slate-950/50 border-t border-slate-200/80 dark:border-slate-700/50 text-xs text-slate-500 dark:text-slate-400"
              >
                <div class="flex items-center justify-between">
                  <span v-if="healthStatus?.monitored_devices?.length">
                    {{ healthStatus.monitored_devices.length }} devices
                  </span>
                  <span v-else>No devices monitored</span>
                  <span v-if="healthStatus?.last_check">
                    Updated {{ formatTimestamp(healthStatus.last_check) }}
                  </span>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Dark Mode Toggle -->
        <button
          @click="toggleDarkMode"
          class="flex items-center justify-center w-8 h-8 rounded-md text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
          title="Toggle dark mode"
        >
          <svg
            v-if="!isDark"
            xmlns="http://www.w3.org/2000/svg"
            class="h-[18px] w-[18px]"
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
          <svg
            v-else
            xmlns="http://www.w3.org/2000/svg"
            class="h-[18px] w-[18px]"
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
        </button>
      </div>

      <!-- Divider -->
      <div class="w-px h-6 bg-slate-200 dark:bg-slate-700/50 mx-1"></div>

      <!-- User Menu -->
      <slot name="user-menu"></slot>
    </div>

    <!-- Embed Generator Modal -->
    <EmbedGenerator
      v-if="showEmbedGenerator"
      :networkId="networkId"
      @close="showEmbedGenerator = false"
    />
  </header>
</template>

<script lang="ts" setup>
import { onBeforeUnmount, ref, onMounted, reactive } from 'vue';
import * as networksApi from '../api/networks';
import type { ParsedNetworkMap, TreeNode } from '../types/network';
import { useNetworkData } from '../composables/useNetworkData';
import { useMapLayout } from '../composables/useMapLayout';
import {
  useHealthMonitoring,
  type MonitoringConfig,
  type MonitoringStatus,
} from '../composables/useHealthMonitoring';
import { useDarkMode } from '../composables/useDarkMode';
import { apiUrl } from '../config';
import EmbedGenerator from './EmbedGenerator.vue';

const props = defineProps<{
  root: TreeNode;
  hasUnsavedChanges?: boolean;
  canEdit?: boolean;
  networkId?: string;
  networkName?: string;
}>();

const emit = defineEmits<{
  (e: 'updateMap', parsed: ParsedNetworkMap): void;
  (e: 'applyLayout', layout: any): void;
  (e: 'log', line: string): void;
  (e: 'running', isRunning: boolean): void;
  (e: 'clearLogs'): void;
  (e: 'cleanUpLayout'): void;
  (e: 'autoLoadFromServer'): void;
  (e: 'saved'): void;
}>();

const loading = ref(false);
const saving = ref(false);
const message = ref('');
const { parseNetworkMap } = useNetworkData();
const { exportLayout, importLayout } = useMapLayout();
const { fetchConfig, updateConfig, fetchStatus } = useHealthMonitoring();
const { isDark, toggleDarkMode } = useDarkMode();
let es: EventSource | null = null;
// Prefer relative URLs to avoid mixed-content; use APPLICATION_URL only if safe (https or same protocol)
const baseUrl = ref<string>('');
const isCloudDeployment = (import.meta.env.BASE_URL || '/').startsWith('/app');

// Health monitoring settings
const showHealthSettings = ref(false);
const showEmbedGenerator = ref(false);
const healthConfig = reactive<MonitoringConfig>({
  enabled: true,
  check_interval_seconds: 30,
  include_dns: true,
});
const healthStatus = ref<MonitoringStatus | null>(null);

onMounted(async () => {
  // Dark mode is now initialized by useDarkMode composable (uses localStorage immediately)
  try {
    const res = await fetch(apiUrl('/api/config'));
    if (res.ok) {
      const cfg = await res.json();
      const url = String(cfg?.applicationUrl || '').trim();
      if (url) {
        try {
          const u = new URL(url);
          // Use only if protocol matches page or it's https (to avoid mixed-content when page is https)
          if (u.protocol === window.location.protocol || u.protocol === 'https:') {
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
    if (props.networkId) {
      // Load from network-specific endpoint
      const layoutResponse = await networksApi.getNetworkLayout(props.networkId);
      if (layoutResponse.layout_data) {
        emit('applyLayout', layoutResponse.layout_data);
        emit('saved'); // Mark as saved since we just loaded the saved state
        message.value = 'Loaded saved map';
        setTimeout(() => {
          message.value = '';
        }, 3000);
      }
    }
    // Legacy endpoint removed - networks now require networkId
  } catch (error) {
    console.error('Failed to load saved layout:', error);
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
    console.error('Failed to load health config:', error);
  }
}

async function updateHealthConfig() {
  try {
    await updateConfig(healthConfig);
    healthStatus.value = await fetchStatus();
  } catch (error) {
    console.error('Failed to update health config:', error);
  }
}

async function toggleMonitoring() {
  if (!props.canEdit) return;
  healthConfig.enabled = !healthConfig.enabled;
  await updateHealthConfig();
}

async function toggleDns() {
  if (!props.canEdit) return;
  healthConfig.include_dns = !healthConfig.include_dns;
  await updateHealthConfig();
}

// formatTimestamp - use formatShortTime from utils/formatters
import { formatShortTime } from '../utils/formatters';
const formatTimestamp = (isoString: string) => formatShortTime(isoString);

// Close health settings dropdown when clicking outside
function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement;
  if (showHealthSettings.value && !target.closest('.relative')) {
    showHealthSettings.value = false;
  }
}

async function runMapper() {
  message.value = '';
  emit('clearLogs');
  startSSE();
}

function cancelScan() {
  emit('log', '--- Scan cancelled by user ---');
  message.value = 'Scan cancelled';
  loading.value = false;
  emit('running', false);
  endSSE();
  setTimeout(() => {
    message.value = '';
  }, 3000);
}

async function saveLayout() {
  if (saving.value) return; // Prevent multiple simultaneous saves

  saving.value = true;
  try {
    const layout = exportLayout(props.root);

    if (props.networkId) {
      // Save to network-specific endpoint
      await networksApi.saveNetworkLayout(props.networkId, layout);
      message.value = 'Map saved';
      emit('saved');
      setTimeout(() => {
        message.value = '';
      }, 3000);
    }
    // Legacy endpoint removed - networks now require networkId
  } catch (error: unknown) {
    message.value = 'Failed to save';
    console.error('Save error:', error);
    setTimeout(() => {
      message.value = '';
    }, 5000);
  } finally {
    saving.value = false;
  }
}

function exportJSON() {
  const layout = exportLayout(props.root);
  const blob = new Blob([JSON.stringify(layout, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'network_layout.json';
  document.body.appendChild(a);
  a.click();
  URL.revokeObjectURL(url);
  document.body.removeChild(a);
  message.value = 'JSON exported';
  setTimeout(() => {
    message.value = '';
  }, 2000);
}

function onLoadFile(e: Event) {
  if (!props.canEdit) {
    message.value = 'Write permission required';
    return;
  }
  const input = e.target as HTMLInputElement;
  if (!input.files || !input.files.length) return;
  const file = input.files[0];
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const text = String(reader.result || '');
      const layout = importLayout(text);
      emit('applyLayout', layout);
      message.value = 'Layout imported';
    } catch (err: any) {
      message.value = err?.message || 'Import failed';
    }
  };
  reader.readAsText(file);
}

function cleanUpLayout() {
  emit('cleanUpLayout');
  message.value = 'Layout tidied';
  setTimeout(() => {
    message.value = '';
  }, 2000);
}

function startSSE() {
  endSSE();
  loading.value = true;
  message.value = 'Scanning network...';
  emit('running', true);
  try {
    // Build SSE URL for same-origin cookie-authenticated requests
    let sseUrl = `${baseUrl.value}/api/run-mapper/stream`.replace(/^\/\//, '/');
    if (!baseUrl.value) {
      sseUrl = apiUrl('/api/run-mapper/stream');
    }
    es = new EventSource(sseUrl);
    es.addEventListener('log', (e: MessageEvent) => {
      emit('log', String(e.data || ''));
    });
    es.addEventListener('result', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(String(e.data || '{}'));
        const content = String(payload?.content || '');
        if (content) {
          const parsed = parseNetworkMap(content);
          emit('updateMap', parsed);
        }
      } catch {
        /* ignore parse errors */
      }
    });
    es.addEventListener('done', (e: MessageEvent) => {
      message.value = 'Scan complete';
      loading.value = false;
      emit('running', false);
      // Emit a download hint line
      const dl = baseUrl.value ? `${baseUrl.value}/api/download-map` : apiUrl('/api/download-map');
      emit('log', `DOWNLOAD: ${dl}`);
      endSSE();
      setTimeout(() => {
        message.value = '';
      }, 3000);
    });
    es.onerror = () => {
      if (loading.value) {
        message.value = 'Connection error';
        loading.value = false;
      }
      emit('running', false);
      endSSE();
    };
  } catch (err: any) {
    message.value = err?.message || 'Failed to start scan';
    loading.value = false;
    emit('running', false);
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
