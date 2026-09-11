import { defineStore } from "pinia";
import { api } from "@/services/api";
import type { User } from "@/types";

export const useAuthStore = defineStore("auth", {
  state: () => ({ user: null as User | null, initialized: false }),
  getters: {
    signedIn: (state) => Boolean(state.user),
    canReview: (state) =>
      state.user?.role === "reviewer" || state.user?.role === "admin",
    isAdmin: (state) => state.user?.role === "admin",
  },
  actions: {
    async initialize() {
      if (this.initialized) return;
      try {
        this.user = (await api.get<User>("/auth/me")).data;
      } catch {
        this.user = null;
      }
      this.initialized = true;
    },
    async login(email: string, password: string) {
      this.user = (
        await api.post<User>("/auth/login", { email, password })
      ).data;
    },
    async register(display_name: string, email: string, password: string) {
      await api.post("/auth/register", { display_name, email, password });
      await this.login(email, password);
    },
    async logout() {
      await api.post("/auth/logout");
      this.user = null;
    },
  },
});
