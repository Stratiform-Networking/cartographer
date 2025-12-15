import { ref } from "vue";
import axios from "axios";
import type { SavedLayout } from "./useMapLayout";

export interface Network {
	id: string; // UUID string
	name: string;
	description: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
	last_sync_at: string | null;
	owner_id: string | null;
	is_owner: boolean;
	permission: "viewer" | "editor" | "admin" | null;
}

export interface NetworkLayoutResponse {
	id: string; // UUID string
	name: string;
	layout_data: SavedLayout | null;
	updated_at: string;
}

export interface CreateNetworkData {
	name: string;
	description?: string;
}

export interface UpdateNetworkData {
	name?: string;
	description?: string;
}

// Network permission types
export type NetworkPermissionRole = "viewer" | "editor";

export interface NetworkPermission {
	id: number;
	network_id: string; // UUID string
	user_id: string;
	role: NetworkPermissionRole;
	created_at: string;
	username?: string;
}

export interface CreateNetworkPermission {
	user_id: string;
	role: NetworkPermissionRole;
}

export interface UpdateNetworkPermission {
	role: NetworkPermissionRole;
}

// Shared state across components
const networks = ref<Network[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

export function useNetworks() {
	// Clear networks state (call when switching accounts)
	// Sets loading to true to show loading state instead of "no networks"
	function clearNetworks(): void {
		networks.value = [];
		error.value = null;
		loading.value = true;
	}

	async function fetchNetworks(): Promise<void> {
		loading.value = true;
		error.value = null;

		// Log the current auth header for debugging
		const authHeader = axios.defaults.headers.common["Authorization"];
		console.log("[Networks] Fetching networks, auth header present:", !!authHeader);

		try {
			// Add cache-busting to ensure fresh data after login/logout
			const response = await axios.get<Network[]>("/api/networks", {
				headers: {
					"Cache-Control": "no-cache, no-store, must-revalidate",
					"Pragma": "no-cache",
				},
				params: {
					_t: Date.now(), // Cache buster
				},
			});
			console.log("[Networks] Fetched", response.data.length, "networks");
			networks.value = response.data;
		} catch (e: any) {
			console.error("[Networks] Fetch failed:", e.response?.status, e.message);
			error.value = e.response?.data?.detail || e.message || "Failed to fetch networks";
			const err = new Error(error.value!) as Error & { status?: number };
			err.status = e.response?.status;
			throw err;
		} finally {
			loading.value = false;
		}
	}

	async function createNetwork(data: CreateNetworkData): Promise<Network> {
		try {
			const response = await axios.post<Network>("/api/networks", data);
			// Add to local state
			networks.value.unshift(response.data);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to create network";
			throw new Error(message);
		}
	}

	async function getNetwork(id: string): Promise<Network> {
		try {
			const response = await axios.get<Network>(`/api/networks/${id}`);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to get network";
			const error = new Error(message) as Error & { status?: number };
			error.status = e.response?.status;
			throw error;
		}
	}

	async function updateNetwork(id: string, data: UpdateNetworkData): Promise<Network> {
		try {
			const response = await axios.patch<Network>(`/api/networks/${id}`, data);
			// Update local state
			const index = networks.value.findIndex((n) => n.id === id);
			if (index !== -1) {
				networks.value[index] = response.data;
			}
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to update network";
			throw new Error(message);
		}
	}

	async function deleteNetwork(id: string): Promise<void> {
		try {
			await axios.delete(`/api/networks/${id}`);
			// Remove from local state
			networks.value = networks.value.filter((n) => n.id !== id);
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to delete network";
			throw new Error(message);
		}
	}

	async function getNetworkLayout(id: string): Promise<NetworkLayoutResponse> {
		try {
			const response = await axios.get<NetworkLayoutResponse>(`/api/networks/${id}/layout`);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to get network layout";
			throw new Error(message);
		}
	}

	async function saveNetworkLayout(id: string, layoutData: SavedLayout): Promise<NetworkLayoutResponse> {
		try {
			const response = await axios.post<NetworkLayoutResponse>(`/api/networks/${id}/layout`, {
				layout_data: layoutData,
			});
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to save network layout";
			throw new Error(message);
		}
	}

	// Check if user can write to a specific network
	function canWriteNetwork(network: Network): boolean {
		if (network.is_owner) return true;
		return network.permission === "editor" || network.permission === "admin";
	}

	// ==================== Network Permission Management ====================

	async function listNetworkPermissions(networkId: string): Promise<NetworkPermission[]> {
		try {
			const response = await axios.get<NetworkPermission[]>(`/api/networks/${networkId}/permissions`);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to get network permissions";
			throw new Error(message);
		}
	}

	async function addNetworkPermission(networkId: string, data: CreateNetworkPermission): Promise<NetworkPermission> {
		try {
			const response = await axios.post<NetworkPermission>(`/api/networks/${networkId}/permissions`, data);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to add user to network";
			throw new Error(message);
		}
	}

	async function removeNetworkPermission(networkId: string, userId: string): Promise<void> {
		try {
			await axios.delete(`/api/networks/${networkId}/permissions/${userId}`);
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to remove user from network";
			throw new Error(message);
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

