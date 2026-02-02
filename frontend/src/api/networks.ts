/**
 * Networks API module
 *
 * All network management API calls.
 * Types are defined in types/networks.ts - import from there for type definitions.
 */

import client from './client';
import type {
  Network,
  NetworkLayoutResponse,
  CreateNetworkData,
  UpdateNetworkData,
  NetworkPermission,
  CreateNetworkPermission,
} from '../types/networks';
import type { SavedLayout } from '../types/layout';

// Re-export types for backwards compatibility (consumers should import from types/ directly)
export type {
  Network,
  NetworkLayoutResponse,
  CreateNetworkData,
  UpdateNetworkData,
  NetworkPermission,
  CreateNetworkPermission,
} from '../types/networks';

// ==================== Network CRUD ====================

export async function fetchNetworks(): Promise<Network[]> {
  const response = await client.get<Network[]>('/api/networks', {
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      Pragma: 'no-cache',
    },
    params: {
      _t: Date.now(),
    },
  });
  return response.data;
}

export async function getNetwork(id: string): Promise<Network> {
  const response = await client.get<Network>(`/api/networks/${id}`);
  return response.data;
}

export async function createNetwork(data: CreateNetworkData): Promise<Network> {
  const response = await client.post<Network>('/api/networks', data);
  return response.data;
}

export async function updateNetwork(id: string, data: UpdateNetworkData): Promise<Network> {
  const response = await client.patch<Network>(`/api/networks/${id}`, data);
  return response.data;
}

export async function deleteNetwork(id: string): Promise<void> {
  await client.delete(`/api/networks/${id}`);
}

// ==================== Layout ====================

export async function getNetworkLayout(id: string): Promise<NetworkLayoutResponse> {
  const response = await client.get<NetworkLayoutResponse>(`/api/networks/${id}/layout`);
  return response.data;
}

export async function saveNetworkLayout(
  id: string,
  layoutData: SavedLayout
): Promise<NetworkLayoutResponse> {
  const response = await client.post<NetworkLayoutResponse>(`/api/networks/${id}/layout`, {
    layout_data: layoutData,
  });
  return response.data;
}

// ==================== Permissions ====================

export async function listNetworkPermissions(networkId: string): Promise<NetworkPermission[]> {
  const response = await client.get<NetworkPermission[]>(`/api/networks/${networkId}/permissions`);
  return response.data;
}

export async function addNetworkPermission(
  networkId: string,
  data: CreateNetworkPermission
): Promise<NetworkPermission> {
  const response = await client.post<NetworkPermission>(
    `/api/networks/${networkId}/permissions`,
    data
  );
  return response.data;
}

export async function removeNetworkPermission(networkId: string, userId: string): Promise<void> {
  await client.delete(`/api/networks/${networkId}/permissions/${userId}`);
}

// ==================== Network Limit ====================

export interface NetworkLimitStatus {
  used: number; // Number of networks owned
  limit: number; // Max networks allowed (-1 = unlimited)
  remaining: number; // Networks that can still be created (-1 = unlimited)
  is_exempt: boolean; // Whether user is exempt from limits
  message: string | null; // Message to display when limit is reached
}

export async function getNetworkLimitStatus(): Promise<NetworkLimitStatus> {
  const response = await client.get<NetworkLimitStatus>('/api/auth/network-limit');
  return response.data;
}
