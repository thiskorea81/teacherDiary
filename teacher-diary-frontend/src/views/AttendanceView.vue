<template>
    <div>
      <h2>출결</h2>
      <section style="display:grid; grid-template-columns: repeat(4, 1fr); gap:8px; max-width:900px;">
        <input v-model.number="studentId" type="number" placeholder="학생 ID" />
        <input v-model="start" type="date" />
        <input v-model="end" type="date" />
        <button @click="fetchList">조회</button>
      </section>
  
      <section style="margin:12px 0; display:flex; gap:8px; flex-wrap:wrap;">
        <input v-model.number="form.student_id" type="number" placeholder="학생 ID" />
        <input v-model="form.date" type="date" />
        <select v-model="form.type">
          <option>present</option><option>late</option><option>early_leave</option>
          <option>absent</option><option>period_absence</option>
        </select>
        <select v-model="form.reason">
          <option>NORMAL</option><option>EXTERNAL_DOMESTIC</option><option>EXTERNAL_OVERSEAS</option>
          <option>MENSTRUAL</option><option>OFFICIAL</option>
        </select>
        <input v-model.number="form.periods" type="number" min="0" placeholder="교시수" />
        <input v-model="form.note" placeholder="비고" />
        <button @click="create">등록</button>
        <span v-if="err" style="color:#c00;">{{ err }}</span>
      </section>
  
      <table class="table">
        <thead><tr><th>날짜</th><th>유형</th><th>사유</th><th>교시수</th><th>비고</th></tr></thead>
        <tbody>
          <tr v-for="r in rows" :key="r.id">
            <td>{{ r.date }}</td><td>{{ r.type }}</td><td>{{ r.reason }}</td><td>{{ r.periods }}</td><td>{{ r.note }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import api from "@/services/api";
  
  const studentId = ref("");
  const start = ref(""); const end = ref("");
  const rows = ref([]);
  const err = ref("");
  
  const form = ref({ student_id: "", date: "", type: "present", reason: "NORMAL", periods: 0, note: "" });
  
  async function fetchList() {
    if (!studentId.value) return;
    const { data } = await api.get("/attendance", { params: { student_id: studentId.value, start: start.value || undefined, end: end.value || undefined } });
    rows.value = data;
  }
  
  async function create() {
    err.value = "";
    try {
      await api.post("/attendance", form.value);
      await fetchList();
    } catch (e) {
      err.value = e?.response?.data?.detail || "에러";
    }
  }
  </script>
  