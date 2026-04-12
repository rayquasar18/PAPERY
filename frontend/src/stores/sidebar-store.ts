import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SidebarState {
  /** Whether the main navigation sidebar is expanded (true) or collapsed (false). */
  isExpanded: boolean;
  /** Whether the floating chat panel overlay is visible. */
  isChatPanelOpen: boolean;
  /** Width of the chat panel in pixels (draggable by user). */
  chatPanelWidth: number;

  toggleSidebar: () => void;
  toggleChatPanel: () => void;
  setChatPanelWidth: (width: number) => void;
}

/**
 * Persisted store for sidebar and chat panel UI state.
 * Survives page reloads via localStorage under the key 'papery-sidebar'.
 */
export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isExpanded: true,
      isChatPanelOpen: false,
      chatPanelWidth: 480,

      toggleSidebar: () => set((s) => ({ isExpanded: !s.isExpanded })),
      toggleChatPanel: () => set((s) => ({ isChatPanelOpen: !s.isChatPanelOpen })),
      setChatPanelWidth: (width) => set({ chatPanelWidth: width }),
    }),
    { name: 'papery-sidebar' }
  )
);
