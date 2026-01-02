/**
 * Assistant API module
 *
 * All AI assistant and chat API calls.
 */

import client from './client';

// ==================== Types ====================

export interface RateLimitStatus {
  remaining: number;
  limit: number;
  reset_at?: string;
  is_limited: boolean;
}

export interface ProviderConfig {
  id: string;
  name: string;
  enabled: boolean;
  models: string[];
}

export interface AssistantConfig {
  providers: ProviderConfig[];
  default_provider?: string;
  default_model?: string;
}

export interface ContextSummary {
  device_count: number;
  network_summary?: string;
  last_updated?: string;
}

export interface ContextStatus {
  is_stale: boolean;
  last_refresh?: string;
  needs_refresh: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  message: string;
  provider?: string;
  model?: string;
  network_id?: string;
  history?: ChatMessage[];
}

export interface ChatResponse {
  response: string;
  provider: string;
  model: string;
  tokens_used?: number;
}

// ==================== API Calls ====================

export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const response = await client.get<RateLimitStatus>('/api/assistant/chat/limit');
  return response.data;
}

export async function getAssistantConfig(): Promise<AssistantConfig> {
  const response = await client.get<AssistantConfig>('/api/assistant/config');
  return response.data;
}

export async function getContext(networkId?: string): Promise<ContextSummary> {
  const params = networkId ? { network_id: networkId } : {};
  const response = await client.get<ContextSummary>('/api/assistant/context', { params });
  return response.data;
}

export async function getContextStatus(networkId?: string): Promise<ContextStatus> {
  const params = networkId ? { network_id: networkId } : {};
  const response = await client.get<ContextStatus>('/api/assistant/context/status', { params });
  return response.data;
}

export async function refreshContext(networkId?: string): Promise<void> {
  const params = networkId ? { network_id: networkId } : {};
  await client.post('/api/assistant/context/refresh', null, { params });
}

export async function sendChatMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await client.post<ChatResponse>('/api/assistant/chat', request);
  return response.data;
}
