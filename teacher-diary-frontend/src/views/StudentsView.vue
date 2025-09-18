<template>
    <div>
      <h2>학생</h2>
      <div style="display:flex; gap:8px; margin:12px 0;">
        <input v-model="kw" placeholder="이름/학번 검색" />
        <button @click="fetchList">검색</button>
      </div>
  
      <table class="table">
        <thead><tr>
          <th>ID</th><th>학번</th><th>이름</th><th>학년-반-번호</th><th>성별</th><th>담임</th>
          <th>전화</th><th>주소</th><th></th>
        </tr></thead>
        <tbody>
          <tr v-for="s in filtered" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.student_no }}</td>
            <td>{{ s.name }}</td>
            <td>{{ s.grade }}-{{ s.class_no }}-{{ s.number }}</td>
            <td>{{ s.gender }}</td>
            <td>{{ s.homeroom_teacher_id ?? '-' }}</td>
            <td>{{ s.phone ?? '-' }}</td>
            <td>{{ s.address ?? '-' }}</td>
            <td><button @click="select(s)">상세</button></td>
          </tr>
        </tbody>
      </table>
  
      <div v-if="detail" style="margin-top:20px;">
        <h3>학생 상세 #{{ detail.id }}</h3>
        <pre>{{ detail }}</pre>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, onMounted } from "vue";
  import api from "@/services/api";
  
  const list = ref([]);
  const detail = ref(null);
  const kw = ref("");
  
  async function fetchList() {
    const { data } = await api.get("/core/students");
    list.value = data;
  }
  async function select(s) {
    const { data } = await api.get(`/core/students/${s.id}`);
    detail.value = data;
  }
  
  const filtered = computed(() => {
    const q = kw.value.trim();
    if (!q) return list.value;
    return list.value.filter(s =>
      `${s.student_no} ${s.name}`.toLowerCase().includes(q.toLowerCase())
    );
  });
  
  onMounted(fetchList);
  </script>
  