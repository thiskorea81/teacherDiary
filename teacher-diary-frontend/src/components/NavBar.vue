<template>
    <nav style="background:#111; color:#fff; padding:10px 16px;">
      <div style="display:flex; gap:16px; align-items:center; max-width:1000px; margin:0 auto;">
        <router-link to="/">담임 상담</router-link>
  
        <template v-if="auth.isLoggedIn">
          <router-link v-if="isTeacherOrAdmin" to="/students">학생</router-link>
          <router-link v-if="isTeacherOrAdmin" to="/attendance">출결</router-link>
          <router-link v-if="isTeacherOrAdmin" to="/counsel">상담</router-link>
          <router-link v-if="isTeacherOrAdmin" to="/grades">성적</router-link>
  
          <!-- 관리자 전용 -->
          <router-link v-if="auth.role==='admin'" to="/admin/users">관리자: 사용자</router-link>
        </template>
  
        <div style="margin-left:auto; display:flex; gap:10px; align-items:center;">
          <router-link v-if="!auth.isLoggedIn" to="/login">로그인</router-link>
          <router-link v-if="!auth.isLoggedIn" to="/signup">회원가입</router-link>
          <span v-if="auth.isLoggedIn" class="badge">{{ auth.displayName }} ({{ auth.role }})</span>
          <router-link v-if="auth.isLoggedIn" to="/change-password">비밀번호 변경</router-link>
          <button v-if="auth.isLoggedIn" @click="onLogout">로그아웃</button>
        </div>
      </div>
    </nav>
  </template>
  
  <script setup>
  import { useAuthStore } from "@/stores/auth";
  import { useRouter } from "vue-router";
  const auth = useAuthStore();
  const router = useRouter();
  const isTeacherOrAdmin = ["teacher","admin"].includes(auth.role);
  function onLogout(){ auth.logout(); router.push({ name:"login" }); }
  </script>
  