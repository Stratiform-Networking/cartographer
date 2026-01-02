/**
 * API module exports
 *
 * Centralized exports for all API modules.
 */

// Client utilities
export { client, setOnUnauthorized, extractErrorMessage, toApiError } from './client';
export type { ApiError } from './client';

// Auth API
export * as authApi from './auth';

// Networks API
export * as networksApi from './networks';
export type {
  Network,
  NetworkLayoutResponse,
  CreateNetworkData,
  UpdateNetworkData,
  NetworkPermissionRole,
  NetworkPermission,
  CreateNetworkPermission,
} from './networks';

// Health API
export * as healthApi from './health';
export type { MonitoringConfig, MonitoringStatus } from './health';

// Notifications API
export * as notificationsApi from './notifications';

// Embeds API
export * as embedsApi from './embeds';
export type { Embed, EmbedListResponse, EmbedDataResponse, CreateEmbedRequest } from './embeds';

// Assistant API
export * as assistantApi from './assistant';
export type {
  RateLimitStatus,
  ProviderConfig,
  AssistantConfig,
  ContextSummary,
  ContextStatus,
  ChatMessage,
  ChatRequest,
  ChatResponse,
} from './assistant';
