<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      @click.self="$emit('close')"
    >
      <div
        class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col border border-slate-200/80 dark:border-slate-800/80"
      >
        <!-- Header -->
        <div
          class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50 rounded-t-xl"
        >
          <div class="flex items-center gap-2">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5 text-violet-500 dark:text-violet-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <div>
              <h2 class="font-semibold text-slate-800 dark:text-slate-100">
                Notification Settings
              </h2>
              <p class="text-xs text-slate-500 dark:text-slate-400">
                Configure how you receive alerts
              </p>
            </div>
          </div>
          <button
            @click="$emit('close')"
            class="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              class="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Tab Navigation -->
        <div
          class="flex border-b border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/50"
          v-if="networkId !== null"
        >
          <button
            @click="activeTab = 'network'"
            :class="[
              'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'network'
                ? 'border-violet-500 text-violet-600 dark:text-violet-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            <span class="flex items-center gap-2">
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
                  d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
                />
              </svg>
              Network
            </span>
          </button>
          <button
            v-if="!isCloudAuth"
            @click="activeTab = 'global'"
            :class="[
              'px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
              activeTab === 'global'
                ? 'border-blue-500 text-blue-600 dark:text-blue-400 bg-white dark:bg-slate-900'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
            ]"
          >
            <span class="flex items-center gap-2">
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
                  d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              Global
            </span>
          </button>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-4 space-y-4">
          <!-- Loading State (only on initial load) -->
          <div v-if="initialLoading" class="flex items-center justify-center py-12">
            <svg
              class="animate-spin h-8 w-8 text-violet-500"
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
                stroke-width="4"
              ></circle>
              <path
                class="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>

          <template v-if="!initialLoading">
            <!-- Network Tab -->
            <template v-if="activeTab === 'network' && networkId !== null">
              <NetworkSettings
                :network-id="networkId"
                :preferences="networkPrefs"
                :service-status="serviceStatus"
                :discord-link="networkDiscordLink"
                :anomaly-stats="anomalyStats"
                @update="handleNetworkUpdate"
                @test-email="handleTestEmail"
                @test-discord="handleTestDiscord"
                @link-discord="handleLinkNetworkDiscord"
                @unlink-discord="handleUnlinkNetworkDiscord"
              />
            </template>

            <!-- Global Tab -->
            <template v-if="activeTab === 'global' && !isCloudAuth">
              <GlobalSettings
                :preferences="globalPrefs"
                :service-status="serviceStatus"
                :discord-link="globalDiscordLink"
                @update="handleGlobalUpdate"
                @test-email="handleTestGlobalEmail"
                @test-discord="handleTestGlobalDiscord"
                @link-discord="handleLinkGlobalDiscord"
                @unlink-discord="handleUnlinkGlobalDiscord"
              />
            </template>
          </template>
        </div>
      </div>
    </div>

    <!-- Toast Notification -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="toast"
        class="fixed bottom-4 right-4 p-4 rounded-lg shadow-lg z-[60]"
        :class="toast.success ? 'bg-emerald-500 text-white' : 'bg-red-500 text-white'"
      >
        <p class="font-medium">{{ toast.success ? '✓' : '✗' }} {{ toast.message }}</p>
        <p v-if="toast.error" class="text-sm opacity-90 mt-1">{{ toast.error }}</p>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useUserNotifications } from '../composables/useUserNotifications';
import { useAuth } from '../composables/useAuth';
import NetworkSettings from './NotificationSettingsNetwork.vue';
import GlobalSettings from './NotificationSettingsGlobal.vue';

const props = defineProps<{
  networkId: string | null;
}>();

const emit = defineEmits<{
  close: [];
}>();

const { isCloudAuth } = useAuth();

const activeTab = ref<'network' | 'global'>(props.networkId !== null ? 'network' : 'global');
const {
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
// Separate Discord links for network and global contexts
const networkDiscordLink = ref<any>(null);
const globalDiscordLink = ref<any>(null);
const anomalyStats = ref<any>(null);
// Use our own loading state for initial load only
const initialLoading = ref(true);
// Toast notification state
const toast = ref<{ success: boolean; message: string; error?: string } | null>(null);

function showToast(success: boolean, message: string, error?: string) {
  toast.value = { success, message, error };
  setTimeout(() => {
    toast.value = null;
  }, 5000);
}

async function loadData(showLoading = false) {
  if (showLoading) {
    initialLoading.value = true;
  }
  try {
    // Load global data in parallel
    const [status, globalLink, globalP] = await Promise.all([
      getServiceStatus(),
      getDiscordLink('global'),
      getGlobalPreferences(),
    ]);

    serviceStatus.value = status;
    globalDiscordLink.value = globalLink;
    globalPrefs.value = globalP;

    // Load network-specific data if in network context
    if (props.networkId !== null) {
      const [networkP, networkLink] = await Promise.all([
        getNetworkPreferences(props.networkId),
        getDiscordLink('network', props.networkId),
      ]);
      networkPrefs.value = networkP;
      networkDiscordLink.value = networkLink;

      try {
        anomalyStats.value = await getAnomalyStats(props.networkId);
      } catch (e) {
        // Anomaly stats might not be available
        console.warn('Could not load anomaly stats:', e);
      }
    }
  } catch (e) {
    console.error('Failed to load notification settings:', e);
  } finally {
    initialLoading.value = false;
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
    showToast(
      result.success,
      result.success ? 'Test email sent!' : 'Failed to send test email',
      result.error
    );
  } catch (e: any) {
    showToast(false, 'Failed to send test email', e.message || 'Unknown error');
  }
}

async function handleTestDiscord() {
  if (props.networkId === null) return;
  try {
    const result = await testNetworkNotification(props.networkId, 'discord');
    showToast(
      result.success,
      result.success ? 'Test Discord notification sent!' : 'Failed to send test',
      result.error
    );
  } catch (e: any) {
    showToast(false, 'Failed to send test Discord notification', e.message || 'Unknown error');
  }
}

async function handleTestGlobalEmail() {
  try {
    const result = await testGlobalNotification('email');
    showToast(
      result.success,
      result.success ? 'Test email sent!' : 'Failed to send test email',
      result.error
    );
  } catch (e: any) {
    showToast(false, 'Failed to send test email', e.message || 'Unknown error');
  }
}

async function handleTestGlobalDiscord() {
  try {
    const result = await testGlobalNotification('discord');
    showToast(
      result.success,
      result.success ? 'Test Discord notification sent!' : 'Failed to send test',
      result.error
    );
  } catch (e: any) {
    showToast(false, 'Failed to send test Discord notification', e.message || 'Unknown error');
  }
}

// Network-specific Discord link handlers
async function handleLinkNetworkDiscord() {
  if (props.networkId === null) return;
  await handleLinkDiscordWithContext('network', props.networkId);
}

async function handleUnlinkNetworkDiscord() {
  if (props.networkId === null) return;
  await handleUnlinkDiscordWithContext('network', props.networkId);
}

// Global Discord link handlers
async function handleLinkGlobalDiscord() {
  await handleLinkDiscordWithContext('global');
}

async function handleUnlinkGlobalDiscord() {
  await handleUnlinkDiscordWithContext('global');
}

// Generic context-aware Discord link handler
async function handleLinkDiscordWithContext(contextType: 'network' | 'global', networkId?: string) {
  try {
    const { authorization_url } = await initiateDiscordOAuth(contextType, networkId);
    const popup = window.open(authorization_url, 'discord_oauth', 'width=600,height=700');

    if (!popup) {
      showToast(false, 'Popup blocked', 'Please allow popups for this site and try again.');
      return;
    }

    let linkCompleted = false;

    // Handler for OAuth completion (triggered by App.vue via postMessage or localStorage)
    const oauthCompleteHandler = async (event: CustomEvent) => {
      const data = event.detail;
      if (!data || linkCompleted) return;

      // Check if this callback matches our context (or accept any if no context specified)
      const callbackContextType = data.context_type || 'global';
      const callbackNetworkId = data.network_id;

      // Only handle if it matches our initiated context
      if (contextType === 'network' && networkId !== undefined) {
        if (callbackContextType !== 'network' || callbackNetworkId !== networkId) {
          // This callback is for a different context, ignore
          return;
        }
      } else if (contextType === 'global') {
        if (callbackContextType !== 'global') {
          return;
        }
      }

      linkCompleted = true;
      window.removeEventListener('discord-oauth-complete', oauthCompleteHandler as EventListener);

      if (data.status === 'success') {
        // Reload data for the specific context (both link and preferences since backend enables discord)
        if (contextType === 'network' && networkId !== undefined) {
          const [link, prefs] = await Promise.all([
            getDiscordLink('network', networkId),
            getNetworkPreferences(networkId),
          ]);
          networkDiscordLink.value = link;
          networkPrefs.value = prefs;
        } else {
          const [link, prefs] = await Promise.all([
            getDiscordLink('global'),
            getGlobalPreferences(),
          ]);
          globalDiscordLink.value = link;
          globalPrefs.value = prefs;
        }
        const contextLabel = contextType === 'network' ? 'network' : 'global';
        showToast(true, `Discord account linked successfully for ${contextLabel}!`);
      } else {
        showToast(false, 'Discord linking failed', data.message || 'Unknown error');
      }
    };

    // Listen for the custom event dispatched by App.vue (works for both postMessage and localStorage)
    window.addEventListener('discord-oauth-complete', oauthCompleteHandler as EventListener);

    // Fallback: Check when popup closes (in case the event wasn't received)
    const checkPopupClosed = setInterval(async () => {
      if (popup.closed) {
        clearInterval(checkPopupClosed);

        // Give a small delay for storage event to propagate
        setTimeout(async () => {
          window.removeEventListener(
            'discord-oauth-complete',
            oauthCompleteHandler as EventListener
          );

          // Only reload if we haven't already handled via event
          if (!linkCompleted) {
            // Check localStorage directly as final fallback
            const storedData = localStorage.getItem('discord_oauth_callback');
            if (storedData) {
              try {
                const data = JSON.parse(storedData);
                localStorage.removeItem('discord_oauth_callback');
                if (data.status === 'success') {
                  // Reload both link and preferences since backend enables discord
                  if (contextType === 'network' && networkId !== undefined) {
                    const [link, prefs] = await Promise.all([
                      getDiscordLink('network', networkId),
                      getNetworkPreferences(networkId),
                    ]);
                    networkDiscordLink.value = link;
                    networkPrefs.value = prefs;
                  } else {
                    const [link, prefs] = await Promise.all([
                      getDiscordLink('global'),
                      getGlobalPreferences(),
                    ]);
                    globalDiscordLink.value = link;
                    globalPrefs.value = prefs;
                  }
                  showToast(true, 'Discord account linked successfully!');
                } else {
                  showToast(false, 'Discord linking failed', data.message || 'Unknown error');
                }
                return;
              } catch (e) {
                // Invalid JSON
              }
            }

            // No stored data, just reload link and preferences in case linking succeeded
            if (contextType === 'network' && networkId !== undefined) {
              const [link, prefs] = await Promise.all([
                getDiscordLink('network', networkId),
                getNetworkPreferences(networkId),
              ]);
              networkDiscordLink.value = link;
              networkPrefs.value = prefs;
            } else {
              const [link, prefs] = await Promise.all([
                getDiscordLink('global'),
                getGlobalPreferences(),
              ]);
              globalDiscordLink.value = link;
              globalPrefs.value = prefs;
            }
          }
        }, 500);
      }
    }, 500);

    // Stop checking after 5 minutes
    setTimeout(() => {
      clearInterval(checkPopupClosed);
      window.removeEventListener('discord-oauth-complete', oauthCompleteHandler as EventListener);
    }, 300000);
  } catch (e: any) {
    showToast(false, 'Failed to initiate Discord OAuth', e.message || 'Unknown error');
  }
}

// Generic context-aware Discord unlink handler
async function handleUnlinkDiscordWithContext(
  contextType: 'network' | 'global',
  networkId?: string
) {
  const contextLabel = contextType === 'network' ? 'this network' : 'global settings';
  if (!confirm(`Are you sure you want to unlink your Discord account from ${contextLabel}?`)) {
    return;
  }

  try {
    await unlinkDiscord(contextType, networkId);
    // Update the specific discord link status
    if (contextType === 'network' && networkId !== undefined) {
      networkDiscordLink.value = { linked: false };
    } else {
      globalDiscordLink.value = { linked: false };
    }
    showToast(true, `Discord account unlinked from ${contextLabel} successfully`);
  } catch (e: any) {
    showToast(false, 'Failed to unlink Discord', e.message || 'Unknown error');
  }
}

// Note: OAuth callback handling is now done via postMessage in App.vue
// This watch is kept for backwards compatibility but shouldn't be needed

onMounted(() => {
  loadData(true); // Show loading spinner on initial load
});
</script>
