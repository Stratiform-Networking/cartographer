/**
 * Health monitoring composable
 *
 * Manages health monitoring state and orchestrates health API calls.
 */

import { ref, computed } from 'vue';
import * as healthApi from '../api/health';
import { toApiError } from '../api/client';
import type { DeviceMetrics } from '../types/network';

// Re-export types for backwards compatibility
export type { MonitoringConfig, MonitoringStatus } from '../api/health';

// Global state for health monitoring
const cachedMetrics = ref<Record<string, DeviceMetrics>>({});
const monitoringConfig = ref<healthApi.MonitoringConfig>({
  enabled: true,
  check_interval_seconds: 30,
  include_dns: true,
});
const monitoringStatus = ref<healthApi.MonitoringStatus | null>(null);
const isPolling = ref(false);
let pollInterval: ReturnType<typeof setInterval> | null = null;
let lastCachedMetricsUnavailableLogAt = 0;

const CACHED_METRICS_ERROR_LOG_COOLDOWN_MS = 60_000;

export function useHealthMonitoring() {
  /**
   * Register devices for passive monitoring and trigger immediate check
   */
  async function registerDevices(
    ips: string[],
    networkId: string,
    triggerCheck = true
  ): Promise<void> {
    try {
      console.log(
        `[Health] Sending ${ips.length} IPs to backend for monitoring (network ${networkId}):`,
        ips
      );
      const response = await healthApi.registerDevices(ips, networkId);
      console.log('[Health] Backend response:', response);

      // Trigger an immediate check so we have data right away
      if (triggerCheck && ips.length > 0) {
        if (response.active_monitoring) {
          console.log('[Health] Triggering immediate health check...');
          await triggerImmediateCheck();
        } else {
          // Cloud mode: active checks are disabled and metrics come from agent sync.
          console.log('[Health] Active checks disabled on backend; using cached metrics only');
          await fetchAllCachedMetrics();
        }
      }
    } catch (error) {
      console.error('[Health] Failed to register devices:', error);
    }
  }

  /**
   * Get monitoring configuration
   */
  async function fetchConfig(): Promise<healthApi.MonitoringConfig | null> {
    try {
      const config = await healthApi.getMonitoringConfig();
      monitoringConfig.value = config;
      return config;
    } catch (error) {
      console.error('[Health] Failed to fetch config:', error);
      return null;
    }
  }

  /**
   * Update monitoring configuration
   */
  async function updateConfig(config: Partial<healthApi.MonitoringConfig>): Promise<void> {
    try {
      const newConfig = { ...monitoringConfig.value, ...config };
      const response = await healthApi.updateMonitoringConfig(newConfig);
      monitoringConfig.value = response;
      console.log('[Health] Updated monitoring config:', response);
    } catch (error) {
      console.error('[Health] Failed to update config:', error);
    }
  }

  /**
   * Get monitoring status
   */
  async function fetchStatus(): Promise<healthApi.MonitoringStatus | null> {
    try {
      const status = await healthApi.getMonitoringStatus();
      monitoringStatus.value = status;
      return status;
    } catch (error) {
      console.error('[Health] Failed to fetch status:', error);
      return null;
    }
  }

  /**
   * Fetch all cached metrics from the server
   */
  async function fetchAllCachedMetrics(): Promise<Record<string, DeviceMetrics>> {
    try {
      const data = await healthApi.getAllCachedMetrics();
      cachedMetrics.value = data;
      const deviceCount = Object.keys(data).length;
      if (deviceCount > 0) {
        console.log(`[Health] Fetched cached metrics for ${deviceCount} devices`);
      }
      return data;
    } catch (error) {
      const apiError = toApiError(error);
      const isUpstreamUnavailable = [502, 503, 504].includes(apiError.status);

      if (isUpstreamUnavailable) {
        const now = Date.now();
        if (now - lastCachedMetricsUnavailableLogAt >= CACHED_METRICS_ERROR_LOG_COOLDOWN_MS) {
          console.warn(
            `[Health] Cached metrics temporarily unavailable (${apiError.status}): ${apiError.message}`
          );
          lastCachedMetricsUnavailableLogAt = now;
        }
        return cachedMetrics.value;
      }

      console.error('[Health] Failed to fetch cached metrics:', error);
      return cachedMetrics.value;
    }
  }

  /**
   * Get cached metrics for a specific device
   */
  function getCachedMetrics(ip: string): DeviceMetrics | null {
    return cachedMetrics.value[ip] || null;
  }

  /**
   * Trigger an immediate health check of all monitored devices
   */
  async function triggerImmediateCheck(): Promise<void> {
    try {
      await healthApi.triggerHealthCheck();
      // Fetch updated cached metrics after check
      await fetchAllCachedMetrics();
    } catch (error) {
      const apiError = toApiError(error);
      const detail = apiError.detail || apiError.message;
      const isExpectedSkip =
        apiError.status === 400 &&
        (detail.includes('disabled in cloud deployment') ||
          detail.includes('No devices registered for monitoring'));

      if (isExpectedSkip) {
        // Expected in cloud mode or before any device registration completes.
        console.log(`[Health] Immediate check skipped: ${detail}`);
        await fetchAllCachedMetrics();
        return;
      }

      console.error('[Health] Failed to trigger check:', error);
    }
  }

  /**
   * Start polling for cached metrics updates
   */
  function startPolling(intervalMs = 10000): void {
    if (isPolling.value) return;

    isPolling.value = true;
    fetchAllCachedMetrics(); // Initial fetch

    pollInterval = setInterval(() => {
      fetchAllCachedMetrics();
    }, intervalMs);

    console.log(`[Health] Started polling every ${intervalMs}ms`);
  }

  /**
   * Stop polling for cached metrics
   */
  function stopPolling(): void {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    isPolling.value = false;
    console.log('[Health] Stopped polling');
  }

  return {
    // State
    cachedMetrics: computed(() => cachedMetrics.value),
    monitoringConfig: computed(() => monitoringConfig.value),
    monitoringStatus: computed(() => monitoringStatus.value),
    isPolling: computed(() => isPolling.value),

    // Methods
    registerDevices,
    fetchConfig,
    updateConfig,
    fetchStatus,
    fetchAllCachedMetrics,
    getCachedMetrics,
    triggerImmediateCheck,
    startPolling,
    stopPolling,
  };
}
