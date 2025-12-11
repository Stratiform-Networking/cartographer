import { ref } from "vue";
import axios from "axios";
import type { SavedLayout } from "./useMapLayout";

export interface Network {
	id: number;
	name: string;
	description: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
	last_sync_at: string | null;
	is_owner: boolean;
	permission: "viewer" | "editor" | "admin" | null;
}

export interface NetworkLayoutResponse {
	id: number;
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

// Shared state across components
const networks = ref<Network[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

export function useNetworks() {
	async function fetchNetworks(): Promise<void> {
		loading.value = true;
		error.value = null;

		try {
			const response = await axios.get<Network[]>("/api/networks");
			networks.value = response.data;
		} catch (e: any) {
			error.value = e.response?.data?.detail || e.message || "Failed to fetch networks";
			throw new Error(error.value!);
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

	async function getNetwork(id: number): Promise<Network> {
		try {
			const response = await axios.get<Network>(`/api/networks/${id}`);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to get network";
			throw new Error(message);
		}
	}

	async function updateNetwork(id: number, data: UpdateNetworkData): Promise<Network> {
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

	async function deleteNetwork(id: number): Promise<void> {
		try {
			await axios.delete(`/api/networks/${id}`);
			// Remove from local state
			networks.value = networks.value.filter((n) => n.id !== id);
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to delete network";
			throw new Error(message);
		}
	}

	async function getNetworkLayout(id: number): Promise<NetworkLayoutResponse> {
		try {
			const response = await axios.get<NetworkLayoutResponse>(`/api/networks/${id}/layout`);
			return response.data;
		} catch (e: any) {
			const message = e.response?.data?.detail || e.message || "Failed to get network layout";
			throw new Error(message);
		}
	}

	async function saveNetworkLayout(id: number, layoutData: SavedLayout): Promise<NetworkLayoutResponse> {
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

	return {
		// State
		networks,
		loading,
		error,

		// Actions
		fetchNetworks,
		createNetwork,
		getNetwork,
		updateNetwork,
		deleteNetwork,
		getNetworkLayout,
		saveNetworkLayout,

		// Helpers
		canWriteNetwork,
	};
}

