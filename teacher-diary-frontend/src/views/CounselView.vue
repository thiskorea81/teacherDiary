<template>
    <div>
      <h2>상담</h2>
      <section style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px;">
        <input v-model.number="studentId" type="number" placeholder="학생 ID" />
        <button @click="fetchList">조회</button>
      </section>
  
      <section style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; margin-bottom:12px;">
        <input v-model.number="form.student_id" type="number" placeholder="학생 ID" />
        <input v-model="form.date" type="date" />
        <input v-model="form.title" placeholder="제목" />
        <input v-model="form.channel" placeholder="채널(대면/전화 등)" />
        <textarea v-model="form.content" placeholder="내용" style="grid-column: 1 / -1;"></textarea>
        <input v-model="form.summary" placeholder="요약(선택)" style="grid-column: 1 / -1;" />
        <button @click="create" style="grid-column: 1 / -1;">등록</button>
        <span v-if="err" style="color:#c00; grid-column: 1 / -1;">{{ err }}</span>
      </section>
  
      <table class="table">
        <thead><tr><th>일자</th><th>제목</th><th>채널</th><th>내용</th><th>요약</th></tr></thead>
        <tbody>
          <tr v-for="c in list" :key="c.id">
            <td>{{ c.date }}</td>
            <td>{{ c.title || '-' }}</td>
            <td>{{ c.channel || '-' }}</td>
            <td>{{ c.content }}</td>
            <td>{{ c.summary || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import api from "@/services/api";
  
  const studentId = ref("");
  const list = ref([]);
  const err = ref("");
  
  const form = ref({ student_id: "", date: "", title: "", channel: "", content: "", summary: "" });
  
  async function fetchList() {
    err.value = "";
    try {
      const { data } = await api.get("/counsels", { params: { student_id: studentId.value } });
      list.value = data;
    } catch (e) {
      err.value = e?.response?.data?.detail || "조회 실패(담임/관리자 권한 필요)";
    }
  }
  
  async function create() {
    err.value = "";
    try {
      await api.post("/counsels", form.value);
      await fetchList();
    } catch (e) {
      err.value = e?.response?.data?.detail || "등록 실패";
    }
  }
  </script>
  