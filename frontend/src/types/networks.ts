/**
 * Network types for multi-network support.
 * These are the canonical type definitions - import from here, not api/networks.ts.
 */

import type { SavedLayout } from './layout';

// ==================== Permission Types ====================

export type NetworkPermissionRole = 'viewer' | 'editor';

// Extended role type that includes admin (for API responses)
export type PermissionRole = 'viewer' | 'editor' | 'admin';

// ==================== Network Types ====================

export interface Network {
  id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_sync_at: string | null;
  owner_id: string | null;
  is_owner: boolean;
  permission: PermissionRole | null;
}

export interface NetworkLayoutResponse {
  id: string;
  name: string;
  layout_data: SavedLayout | null;
  updated_at: string;
}

// ==================== Create/Update Types ====================

export interface CreateNetworkData {
  name: string;
  description?: string;
}

export interface UpdateNetworkData {
  name?: string;
  description?: string;
}

// Aliases for backwards compatibility
export type NetworkCreate = CreateNetworkData;
export type NetworkUpdate = UpdateNetworkData;

// ==================== Permission Types ====================

export interface NetworkPermission {
  id: number;
  network_id: string;
  user_id: string;
  role: NetworkPermissionRole;
  created_at: string;
  username?: string;
}

export interface CreateNetworkPermission {
  user_id: string;
  role: NetworkPermissionRole;
}

// Alias for backwards compatibility
export type PermissionCreate = CreateNetworkPermission;
