/**
 * Composables module exports
 *
 * Centralized exports for all composables.
 * NOTE: Types should be imported from 'types/' directory directly.
 */

export { useAuth } from './useAuth';
export { useNetworks } from './useNetworks';
export { useNotifications } from './useNotifications';
export { useUserNotifications } from './useUserNotifications';
export { useHealthMonitoring } from './useHealthMonitoring';
export { useVersionCheck } from './useVersionCheck';
export { useNetworkData } from './useNetworkData';
export { useMapLayout } from './useMapLayout';
export { useDarkMode } from './useDarkMode';
export { useAutoSave } from './useAutoSave';

// NOTE: Type re-exports removed. Import types from their canonical locations:
// - Network types: import from 'types/networks'
// - Notification types: import from 'types/notifications'
// - Layout types: import from 'types/layout'
// - Version types: import from 'types/version'
// - Health types: import from 'composables/useHealthMonitoring' (MonitoringConfig, MonitoringStatus)
