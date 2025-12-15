/**
 * Network types for multi-network support.
 * These match the backend schemas for API communication.
 */

export type PermissionRole = "viewer" | "editor" | "admin";

export interface Network {
	id: string; // UUID string
	name: string;
	description: string | null;
	is_active: boolean;
	created_at: string;
	updated_at: string;
	last_sync_at: string | null;
	is_owner: boolean;
	permission: PermissionRole | null;
}

export interface NetworkCreate {
	name: string;
	description?: string;
}

export interface NetworkUpdate {
	name?: string;
	description?: string;
}

export interface NetworkLayoutResponse {
	id: string; // UUID string
	name: string;
	layout_data: Record<string, unknown> | null;
	updated_at: string;
}

export interface NetworkPermission {
	id: number;
	network_id: string; // UUID string
	user_id: string;
	role: PermissionRole;
	created_at: string;
	username?: string;
}

export interface PermissionCreate {
	user_id: string;
	role: PermissionRole;
}

