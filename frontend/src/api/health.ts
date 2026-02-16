/**
 * Health monitoring API module
 *
 * All health check and monitoring API calls.
 */

import client from './client';
import type {
  DeviceMetrics,
  GatewayTestIP,
  GatewayTestIPConfig,
  GatewayTestIPsResponse,
  SpeedTestResult,
} from '../types/network';

// ==================== Types ====================

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

export interface RegisterDevicesResponse {
  message: string;
  devices: string[];
  network_id: string;
  active_monitoring: boolean;
}

// Re-export types for convenience
export type { GatewayTestIP, GatewayTestIPConfig, GatewayTestIPsResponse, SpeedTestResult };

// ==================== Monitoring API ====================

export async function registerDevices(
  ips: string[],
  networkId: string
): Promise<RegisterDevicesResponse> {
  const response = await client.post<RegisterDevicesResponse>('/api/health/monitoring/devices', {
    ips,
    network_id: networkId,
  });
  return response.data;
}

export async function getMonitoringConfig(): Promise<MonitoringConfig> {
  const response = await client.get<MonitoringConfig>('/api/health/monitoring/config');
  return response.data;
}

export async function updateMonitoringConfig(
  config: Partial<MonitoringConfig>
): Promise<MonitoringConfig> {
  const response = await client.post<MonitoringConfig>('/api/health/monitoring/config', config);
  return response.data;
}

export async function getMonitoringStatus(): Promise<MonitoringStatus> {
  const response = await client.get<MonitoringStatus>('/api/health/monitoring/status');
  return response.data;
}

export async function getAllCachedMetrics(): Promise<Record<string, DeviceMetrics>> {
  const response = await client.get<Record<string, DeviceMetrics>>('/api/health/cached');
  return response.data;
}

export async function triggerHealthCheck(): Promise<void> {
  await client.post('/api/health/monitoring/check-now');
}

// ==================== Device Health API ====================

export async function checkDeviceHealth(ip: string): Promise<DeviceMetrics> {
  const response = await client.get<DeviceMetrics>(`/api/health/check/${ip}`, {
    timeout: 30000,
  });
  return response.data;
}

// ==================== Gateway Test IPs API ====================

export async function getGatewayTestIPsConfig(gatewayIp: string): Promise<GatewayTestIPConfig> {
  const response = await client.get<GatewayTestIPConfig>(
    `/api/health/gateway/${gatewayIp}/test-ips`
  );
  return response.data;
}

export async function getGatewayTestIPsCached(gatewayIp: string): Promise<GatewayTestIPsResponse> {
  const response = await client.get<GatewayTestIPsResponse>(
    `/api/health/gateway/${gatewayIp}/test-ips/cached`
  );
  return response.data;
}

export async function saveGatewayTestIPs(
  gatewayIp: string,
  testIPs: GatewayTestIP[]
): Promise<void> {
  await client.post(`/api/health/gateway/${gatewayIp}/test-ips`, {
    gateway_ip: gatewayIp,
    test_ips: testIPs,
  });
}

export async function checkGatewayTestIPs(gatewayIp: string): Promise<GatewayTestIPsResponse> {
  const response = await client.get<GatewayTestIPsResponse>(
    `/api/health/gateway/${gatewayIp}/test-ips/check`
  );
  return response.data;
}

export async function deleteGatewayTestIPs(gatewayIp: string): Promise<void> {
  await client.delete(`/api/health/gateway/${gatewayIp}/test-ips`);
}

// ==================== Speed Test API ====================

export async function getSpeedTestResult(gatewayIp?: string): Promise<SpeedTestResult> {
  const endpoint = gatewayIp
    ? `/api/health/gateway/${gatewayIp}/speedtest`
    : '/api/health/speedtest';
  const response = await client.get<SpeedTestResult>(endpoint);
  return response.data;
}

export async function runSpeedTest(gatewayIp?: string): Promise<SpeedTestResult> {
  const endpoint = gatewayIp
    ? `/api/health/gateway/${gatewayIp}/speedtest`
    : '/api/health/speedtest';
  const response = await client.post<SpeedTestResult>(
    endpoint,
    {},
    { timeout: 120000 } // 2 minute timeout for speed test
  );
  return response.data;
}
