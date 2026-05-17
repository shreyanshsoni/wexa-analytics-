import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  fullscreen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setFullscreen: (fs: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  fullscreen: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setFullscreen: (fullscreen) => set({ fullscreen }),
}));
