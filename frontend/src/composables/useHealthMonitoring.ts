import { ref, computed } from 'vue';
import axios from 'axios';
import type { DeviceMetrics } from '../types/network';

export interface MonitoringConfig {
	enabled: boolean;
	check_interval_seconds: number;
	include_dns: boolean;
}

export interface MonitoringStatus {
	enabled: boolean;
	check_interval_seconds: number;
	include_dns: boolean;
	monitored_devices: string[];
	last_check: string | null;
	next_check: string | null;
}

// Global state for health monitoring
const cachedMetrics = ref<Record<string, DeviceMetrics>>({});
const monitoringConfig = ref<MonitoringConfig>({
	enabled: true,
	check_interval_seconds: 30,
	include_dns: true
});
const monitoringStatus = ref<MonitoringStatus | null>(null);
const isPolling = ref(false);
let pollInterval: ReturnType<typeof setInterval> | null = null;

export function useHealthMonitoring() {
	/**
	 * Register devices for passive monitoring and trigger immediate check
	 */
	async function registerDevices(ips: string[], triggerCheck = true): Promise<void> {
		try {
			await axios.post('/api/health/monitoring/devices', { ips });
			console.log(`[Health] Registered ${ips.length} devices for monitoring`);
			
			// Trigger an immediate check so we have data right away
			if (triggerCheck && ips.length > 0) {
				console.log('[Health] Triggering immediate health check...');
				await triggerImmediateCheck();
			}
		} catch (error) {
			console.error('[Health] Failed to register devices:', error);
		}
	}

	/**
	 * Get monitoring configuration
	 */
	async function fetchConfig(): Promise<MonitoringConfig | null> {
		try {
			const response = await axios.get<MonitoringConfig>('/api/health/monitoring/config');
			monitoringConfig.value = response.data;
			return response.data;
		} catch (error) {
			console.error('[Health] Failed to fetch config:', error);
			return null;
		}
	}

	/**
	 * Update monitoring configuration
	 */
	async function updateConfig(config: Partial<MonitoringConfig>): Promise<void> {
		try {
			const newConfig = { ...monitoringConfig.value, ...config };
			const response = await axios.post<MonitoringConfig>('/api/health/monitoring/config', newConfig);
			monitoringConfig.value = response.data;
			console.log('[Health] Updated monitoring config:', response.data);
		} catch (error) {
			console.error('[Health] Failed to update config:', error);
		}
	}

	/**
	 * Get monitoring status
	 */
	async function fetchStatus(): Promise<MonitoringStatus | null> {
		try {
			const response = await axios.get<MonitoringStatus>('/api/health/monitoring/status');
			monitoringStatus.value = response.data;
			return response.data;
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
			const response = await axios.get<Record<string, DeviceMetrics>>('/api/health/cached');
			cachedMetrics.value = response.data;
			return response.data;
		} catch (error) {
			console.error('[Health] Failed to fetch cached metrics:', error);
			return {};
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
			await axios.post('/api/health/monitoring/check-now');
			// Fetch updated cached metrics after check
			await fetchAllCachedMetrics();
		} catch (error) {
			console.error('[Health] Failed to trigger check:', error);
		}
	}

	/**
	 * Start polling for cached metrics updates
	 */
	function startPolling(intervalMs: number = 10000): void {
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

