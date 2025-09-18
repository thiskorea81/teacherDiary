<template>
    <div>
      <h2>대시보드</h2>
      <p v-if="!auth.isLoggedIn">왼쪽 상단에서 로그인하세요.</p>
      <template v-else>
        <p>안녕하세요, <b>{{ auth.displayName }}</b>님!</p>
        <ul>
          <li v-if="isTeacherOrAdmin">상단 메뉴에서 학생/출결/상담/성적을 관리할 수 있습니다.</li>
          <li v-else>학생 계정은 <b>내 정보</b>와 <b>(추가 구현 시) 내 성적</b>만 보이도록 구성할 수 있어요.</li>
        </ul>
      </template>
    </div>
  </template>
  
  <script setup>
  import { useAuthStore } from "@/stores/auth";
  const auth = useAuthStore();
  const isTeacherOrAdmin = ["teacher","admin"].includes(auth.role);
  </script>
  