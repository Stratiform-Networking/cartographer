/**
 * Layout types for network map visualization
 */

import type { TreeNode } from './network';

export interface SavedLayout {
  version: number;
  timestamp: string;
  positions: Record<string, { x: number; y: number }>;
  root?: TreeNode;
}
