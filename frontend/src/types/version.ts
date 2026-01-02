/**
 * Version check types
 */

export type VersionType = 'major' | 'minor' | 'patch';

export interface VersionPreferences {
  enabledTypes: VersionType[];
  dismissed: string[];
  lastChecked: number;
}

export interface VersionInfo {
  current: string;
  latest: string;
  updateAvailable: boolean;
  updateType: VersionType | null;
}
