/**
 * Auto-save composable
 *
 * Provides debounced auto-save functionality for network map changes.
 * Extracts the auto-save pattern from MainApp.vue for reuse.
 */

import { ref, computed, readonly, onBeforeUnmount } from 'vue';

export interface AutoSaveOptions {
  /** Delay in ms before auto-save triggers after last change (default: 2000) */
  delay?: number;
  /** Callback to execute the save */
  onSave: () => Promise<void>;
  /** Optional callback on save error */
  onError?: (error: unknown) => void;
}

export function useAutoSave(options: AutoSaveOptions) {
  const { delay = 2000, onSave, onError } = options;

  // State
  const isSaving = ref(false);
  const lastSaveError = ref<string | null>(null);
  const savedStateHash = ref<string>('');
  let autoSaveTimer: ReturnType<typeof setTimeout> | null = null;

  /**
   * Compute a simple hash of state for change detection.
   * Pass your reactive state object to this function.
   */
  function computeStateHash(state: unknown): string {
    if (!state) return '';
    try {
      return JSON.stringify(state);
    } catch {
      return '';
    }
  }

  /**
   * Check if there are unsaved changes.
   */
  function hasUnsavedChanges(currentHash: string): boolean {
    if (!savedStateHash.value) return true; // No saved state yet
    return currentHash !== savedStateHash.value;
  }

  /**
   * Mark current state as saved.
   */
  function markAsSaved(currentHash: string): void {
    savedStateHash.value = currentHash;
    lastSaveError.value = null;
  }

  /**
   * Trigger auto-save with debouncing.
   * Call this whenever the data changes.
   */
  function triggerAutoSave(): void {
    // Cancel any pending save
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer);
    }

    autoSaveTimer = setTimeout(async () => {
      if (isSaving.value) return;

      isSaving.value = true;
      lastSaveError.value = null;

      try {
        await onSave();
        console.log('[AutoSave] Save completed');
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Save failed';
        lastSaveError.value = message;
        console.error('[AutoSave] Save failed:', error);
        onError?.(error);
      } finally {
        isSaving.value = false;
      }
    }, delay);
  }

  /**
   * Cancel any pending auto-save.
   */
  function cancelAutoSave(): void {
    if (autoSaveTimer) {
      clearTimeout(autoSaveTimer);
      autoSaveTimer = null;
    }
  }

  /**
   * Force an immediate save (bypasses debounce).
   */
  async function saveNow(): Promise<void> {
    cancelAutoSave();

    if (isSaving.value) return;

    isSaving.value = true;
    lastSaveError.value = null;

    try {
      await onSave();
      console.log('[AutoSave] Immediate save completed');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed';
      lastSaveError.value = message;
      console.error('[AutoSave] Immediate save failed:', error);
      onError?.(error);
      throw error;
    } finally {
      isSaving.value = false;
    }
  }

  // Cleanup on unmount
  onBeforeUnmount(() => {
    cancelAutoSave();
  });

  return {
    // State
    isSaving: readonly(isSaving),
    lastSaveError: readonly(lastSaveError),
    savedStateHash: readonly(savedStateHash),

    // Methods
    computeStateHash,
    hasUnsavedChanges,
    markAsSaved,
    triggerAutoSave,
    cancelAutoSave,
    saveNow,

    // Direct access to update saved hash (for external save operations)
    setSavedStateHash: (hash: string) => {
      savedStateHash.value = hash;
    },
  };
}
