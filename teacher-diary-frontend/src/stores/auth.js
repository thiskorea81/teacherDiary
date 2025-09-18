import { defineStore } from "pinia";
import api from "@/services/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("token") || "",
    me: JSON.parse(localStorage.getItem("me") || "null"),
    passwordChangeRequired: JSON.parse(localStorage.getItem("pwdreq") || "false"),
    loading: false,
    error: "",
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    role: (s) => s?.me?.role || null,
    displayName: (s) => s?.me?.full_name || s?.me?.username || "사용자",
  },
  actions: {
    async login(username, password) {
      this.loading = true; this.error = "";
      try {
        const form = new URLSearchParams();
        form.append("username", username);
        form.append("password", password);
        const { data } = await api.post("/auth/token", form, {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });
        this.token = data.access_token;
        this.passwordChangeRequired = !!data.password_change_required;
        localStorage.setItem("token", this.token);
        localStorage.setItem("pwdreq", JSON.stringify(this.passwordChangeRequired));

        const me = await api.get("/auth/me");
        this.me = me.data;
        localStorage.setItem("me", JSON.stringify(this.me));
        return true;
      } catch (e) {
        this.error = e?.response?.data?.detail || "로그인 실패";
        this.logout();
        return false;
      } finally {
        this.loading = false;
      }
    },
    markPasswordChanged() {
      this.passwordChangeRequired = false;
      localStorage.setItem("pwdreq", JSON.stringify(false));
    },
    logout() {
      this.token = ""; this.me = null; this.passwordChangeRequired = false;
      localStorage.removeItem("token"); localStorage.removeItem("me"); localStorage.removeItem("pwdreq");
    },
  },
});
