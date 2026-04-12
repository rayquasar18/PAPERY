import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type SplitMode = 'single' | 'split-2' | 'split-3';

interface UIState {
  /**
   * Number of document panes visible simultaneously.
   * - 'single'  — full-width single pane (default)
   * - 'split-2' — two side-by-side panes
   * - 'split-3' — three panes (power users / wide screens)
   */
  splitMode: SplitMode;

  setSplitMode: (mode: SplitMode) => void;
}

/**
 * Persisted store for global UI layout preferences.
 * Survives page reloads via localStorage under the key 'papery-ui'.
 */
export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      splitMode: 'single',

      setSplitMode: (mode) => set({ splitMode: mode }),
    }),
    { name: 'papery-ui' }
  )
);
