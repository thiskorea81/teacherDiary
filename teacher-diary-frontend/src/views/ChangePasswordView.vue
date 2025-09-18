<template>
    <div style="max-width:480px; margin:40px auto;">
      <h2>비밀번호 변경</h2>
      <p v-if="auth.passwordChangeRequired" class="badge" style="background:#ffd966; color:#333;">
        보안을 위해 비밀번호 변경이 필요합니다.
      </p>
  
      <form @submit.prevent="change" style="display:grid; gap:10px; margin-top:12px;">
        <label>현재 비밀번호</label>
        <input v-model="old_password" type="password" required />
        <label>새 비밀번호</label>
        <input v-model="new_password" type="password" required />
        <button :disabled="loading">변경</button>
        <p v-if="err" style="color:#c00;">{{ err }}</p>
        <p v-if="ok" style="color:#0a0;">변경되었습니다.</p>
      </form>
    </div>
  </template>
  
  <script setup>
import { ref } from "vue";
import api from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import { useRouter, useRoute } from "vue-router";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();

const old_password = ref("");
const new_password = ref("");
const loading = ref(false);
const err = ref("");
const ok = ref(false);

async function change() {
  loading.value = true; err.value = ""; ok.value = false;
  try {
    await api.post("/auth/change_password", {
      old_password: old_password.value,
      new_password: new_password.value
    });
    auth.markPasswordChanged();
    ok.value = true;

    // ✅ 로그인 유지 + 이동 (redirect 쿼리가 있으면 그쪽으로, 기본은 대시보드)
    const to = (route.query.redirect && String(route.query.redirect)) || "/";
    setTimeout(() => router.push(to), 600);
  } catch (e) {
    err.value = e?.response?.data?.detail || "변경 실패";
  } finally {
    loading.value = false;
  }
}
</script>
