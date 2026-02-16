/**
 * Networks composable
 *
 * Manages network state and orchestrates network API calls.
 */

import { ref } from 'vue';
import * as networksApi from '../api/networks';
import { extractErrorMessage } from '../api/client';
import type { SavedLayout } from '../types/layout';
import type {
  Network,
  NetworkLayoutResponse,
  CreateNetworkData,
  UpdateNetworkData,
  NetworkPermission,
  CreateNetworkPermission,
} from '../types/networks';

// Re-export types for backwards compatibility
// NOTE: Types should be imported from 'types/networks' directly
export type {
  Network,
  NetworkLayoutResponse,
  CreateNetworkData,
  UpdateNetworkData,
  NetworkPermission,
  CreateNetworkPermission,
} from '../types/networks';

// Shared state across components
const networks = ref<Network[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

export function useNetworks() {
  // Clear networks state (call when switching accounts)
  function clearNetworks(): void {
    networks.value = [];
    error.value = null;
    loading.value = true;
  }

  async function fetchNetworks(): Promise<void> {
    loading.value = true;
    error.value = null;

    console.log('[Networks] Fetching networks');

    try {
      const data = await networksApi.fetchNetworks();
      console.log('[Networks] Fetched', data.length, 'networks');
      networks.value = data;
    } catch (e: unknown) {
      const axiosError = e as { response?: { status?: number }; message?: string };
      console.error('[Networks] Fetch failed:', axiosError.response?.status, axiosError.message);
      const message = extractErrorMessage(e);
      error.value = message;
      const err = new Error(message) as Error & { status?: number };
      err.status = axiosError.response?.status;
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function createNetwork(data: CreateNetworkData): Promise<Network> {
    try {
      const network = await networksApi.createNetwork(data);
      // Add to local state
      networks.value.unshift(network);
      return network;
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function getNetwork(id: string): Promise<Network> {
    try {
      return await networksApi.getNetwork(id);
    } catch (e: unknown) {
      const axiosError = e as { response?: { status?: number } };
      const message = extractErrorMessage(e);
      const err = new Error(message) as Error & { status?: number };
      err.status = axiosError.response?.status;
      throw err;
    }
  }

  async function updateNetwork(id: string, data: UpdateNetworkData): Promise<Network> {
    try {
      const network = await networksApi.updateNetwork(id, data);
      // Update local state
      const index = networks.value.findIndex((n) => n.id === id);
      if (index !== -1) {
        networks.value[index] = network;
      }
      return network;
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function deleteNetwork(id: string): Promise<void> {
    try {
      await networksApi.deleteNetwork(id);
      // Remove from local state
      networks.value = networks.value.filter((n) => n.id !== id);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function getNetworkLayout(id: string): Promise<NetworkLayoutResponse> {
    try {
      return await networksApi.getNetworkLayout(id);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function saveNetworkLayout(
    id: string,
    layoutData: SavedLayout
  ): Promise<NetworkLayoutResponse> {
    try {
      return await networksApi.saveNetworkLayout(id, layoutData);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  // Check if user can write to a specific network
  function canWriteNetwork(network: Network): boolean {
    if (network.is_owner) return true;
    return network.permission === 'editor' || network.permission === 'admin';
  }

  // ==================== Network Permission Management ====================

  async function listNetworkPermissions(networkId: string): Promise<NetworkPermission[]> {
    try {
      return await networksApi.listNetworkPermissions(networkId);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function addNetworkPermission(
    networkId: string,
    data: CreateNetworkPermission
  ): Promise<NetworkPermission> {
    try {
      return await networksApi.addNetworkPermission(networkId, data);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  async function removeNetworkPermission(networkId: string, userId: string): Promise<void> {
    try {
      await networksApi.removeNetworkPermission(networkId, userId);
    } catch (e) {
      throw new Error(extractErrorMessage(e));
    }
  }

  return {
    // State
    networks,
    loading,
    error,

    // Actions
    clearNetworks,
    fetchNetworks,
    createNetwork,
    getNetwork,
    updateNetwork,
    deleteNetwork,
    getNetworkLayout,
    saveNetworkLayout,

    // Network permissions
    listNetworkPermissions,
    addNetworkPermission,
    removeNetworkPermission,

    // Helpers
    canWriteNetwork,
  };
}
