import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Organization } from "@/types/api";

interface AuthState {
  user: User | null;
  organization: Organization | null;
  role: string | null;
  isAuthenticated: boolean;
  _hasHydrated: boolean;
  setHasHydrated: (v: boolean) => void;
  setAuth: (user: User, org: Organization, role: string, token: string) => void;
  updateOrganization: (org: Partial<Organization>) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      organization: null,
      role: null,
      isAuthenticated: false,
      _hasHydrated: false,
      setHasHydrated: (v) => set({ _hasHydrated: v }),
      setAuth: (user, organization, role, token) => {
        localStorage.setItem("access_token", token);
        set({ user, organization, role, isAuthenticated: true });
      },
      updateOrganization: (org) =>
        set((state) => ({
          organization: state.organization ? { ...state.organization, ...org } : state.organization,
        })),
      clearAuth: () => {
        localStorage.removeItem("access_token");
        set({ user: null, organization: null, role: null, isAuthenticated: false });
      },
    }),
    {
      name: "wexa-auth",
      partialize: (state) => ({
        user: state.user,
        organization: state.organization,
        role: state.role,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
