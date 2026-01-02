/**
 * Embeds API module
 *
 * All embed (shareable network map) API calls.
 */

import client from './client';
import type { TreeNode } from '../types/network';

// ==================== Types ====================

export interface Embed {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  sensitive_mode: boolean;
  network_id?: string;
}

export interface EmbedListResponse {
  embeds: Embed[];
}

export interface EmbedDataResponse {
  exists: boolean;
  root?: TreeNode;
  name?: string;
  sensitive_mode?: boolean;
}

export interface CreateEmbedRequest {
  name: string;
  sensitiveMode: boolean;
  networkId?: string;
}

// ==================== API Calls ====================

export async function listEmbeds(networkId?: string): Promise<Embed[]> {
  const params = networkId ? { network_id: networkId } : {};
  const response = await client.get<EmbedListResponse>('/api/embeds', { params });
  return response.data.embeds || [];
}

export async function createEmbed(request: CreateEmbedRequest): Promise<Embed> {
  const response = await client.post<Embed>('/api/embeds', {
    name: request.name,
    sensitiveMode: request.sensitiveMode,
    network_id: request.networkId,
  });
  return response.data;
}

export async function deleteEmbed(embedId: string): Promise<void> {
  await client.delete(`/api/embeds/${embedId}`);
}

export async function getEmbedData(embedId: string): Promise<EmbedDataResponse> {
  const response = await client.get<EmbedDataResponse>(`/api/embed-data/${embedId}`);
  return response.data;
}

// ==================== Embed Health API ====================

export async function registerEmbedDevices(embedId: string, deviceIds: string[]): Promise<void> {
  await client.post(`/api/embed/${embedId}/health/register`, {
    device_ids: deviceIds,
  });
}

export async function triggerEmbedHealthCheck(embedId: string): Promise<void> {
  await client.post(`/api/embed/${embedId}/health/check-now`);
}

export async function getEmbedHealthMetrics(embedId: string): Promise<Record<string, unknown>> {
  const response = await client.get(`/api/embed/${embedId}/health/cached`);
  return response.data;
}
