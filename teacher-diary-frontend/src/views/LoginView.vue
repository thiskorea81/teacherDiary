<template>
    <div style="max-width:420px; margin:40px auto;">
      <h2>로그인</h2>
      <form @submit.prevent="submit">
        <label>아이디</label>
        <input v-model="username" required />
        <label>비밀번호</label>
        <input v-model="password" type="password" required />
        <div style="margin-top:12px; display:flex; gap:8px; align-items:center;">
          <button :disabled="auth.loading">로그인</button>
          <span v-if="auth.error" style="color:#c00;">{{ auth.error }}</span>
        </div>
      </form>
    </div>
    <p v-if="auth.passwordChangeRequired" class="badge" style="background:#ffd966; color:#333;">
      로그인 후 비밀번호 변경 페이지로 이동합니다.
    </p>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import { useAuthStore } from "@/stores/auth";
  import { useRoute, useRouter } from "vue-router";
  
  const auth = useAuthStore();
  const route = useRoute(); const router = useRouter();
  const username = ref(""); const password = ref("");
  const msg = ref("");
  
  async function submit() {
    const ok = await auth.login(username.value, password.value);
    if (ok) {
    router.push(route.query.redirect || "/");
    } else {
      const e = auth.error || "";
      msg.value = e;
      // ✅ 승인대기 에러면 대기 화면으로 이동 제안
      if (e.includes("승인 대기")) {
        setTimeout(()=> router.push({ name: "pending-approval" }), 800);
      }
    }
  }
  </script>
  