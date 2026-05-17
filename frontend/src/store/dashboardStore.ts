import { create } from "zustand";
import type { Dashboard, Widget } from "@/types/api";

interface DashboardState {
  activeDashboard: Dashboard | null;
  widgets: Widget[];
  isEditing: boolean;
  setActiveDashboard: (dashboard: Dashboard | null) => void;
  setWidgets: (widgets: Widget[]) => void;
  setEditing: (editing: boolean) => void;
  updateWidgetPosition: (id: string, x: number, y: number) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  activeDashboard: null,
  widgets: [],
  isEditing: false,
  setActiveDashboard: (dashboard) => set({ activeDashboard: dashboard }),
  setWidgets: (widgets) => set({ widgets }),
  setEditing: (editing) => set({ isEditing: editing }),
  updateWidgetPosition: (id, x, y) =>
    set((state) => ({
      widgets: state.widgets.map((w) =>
        w.id === id ? { ...w, position_x: x, position_y: y } : w
      ),
    })),
}));
