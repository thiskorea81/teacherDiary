<template>
    <div>
      <h2>성적</h2>
      <div style="display:flex; gap:8px; margin-bottom:12px;">
        <button @click="tab='mid'">중간</button>
        <button @click="tab='final'">기말</button>
        <button @click="tab='mock'">모의고사</button>
      </div>
  
      <section v-if="tab==='mid'">
        <h3>중간고사</h3>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="mid.student_id" type="number" placeholder="학생ID" />
          <input v-model.number="mid.subject_id" type="number" placeholder="과목ID" />
          <input v-model.number="mid.year" type="number" placeholder="연도" />
          <select v-model.number="mid.term"><option :value="1">1</option><option :value="2">2</option></select>
          <input v-model.number="mid.score" type="number" placeholder="점수(0~100)" />
          <input v-model="mid.comment" placeholder="메모" />
          <button @click="saveMid">저장</button>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="qMid.student_id" type="number" placeholder="학생ID" />
          <input v-model.number="qMid.year" type="number" placeholder="연도" />
          <select v-model.number="qMid.term"><option :value="1">1</option><option :value="2">2</option></select>
          <button @click="loadMid">요약 조회</button>
        </div>
        <pre v-if="midSummary">{{ midSummary }}</pre>
      </section>
  
      <section v-else-if="tab==='final'">
        <h3>기말고사</h3>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="fin.student_id" type="number" placeholder="학생ID" />
          <input v-model.number="fin.subject_id" type="number" placeholder="과목ID" />
          <input v-model.number="fin.year" type="number" placeholder="연도" />
          <select v-model.number="fin.term"><option :value="1">1</option><option :value="2">2</option></select>
          <input v-model.number="fin.score" type="number" placeholder="점수" />
          <input v-model="fin.comment" placeholder="메모" />
          <button @click="saveFinal">저장</button>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="qFin.student_id" type="number" placeholder="학생ID" />
          <input v-model.number="qFin.year" type="number" placeholder="연도" />
          <select v-model.number="qFin.term"><option :value="1">1</option><option :value="2">2</option></select>
          <button @click="loadFinal">요약 조회</button>
        </div>
        <pre v-if="finSummary">{{ finSummary }}</pre>
      </section>
  
      <section v-else>
        <h3>모의고사</h3>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="exam.student_id" type="number" placeholder="학생ID" />
          <input v-model.number="exam.year" type="number" placeholder="연도" />
          <input v-model.number="exam.round" type="number" placeholder="회차(월)" />
          <input v-model="exam.name" placeholder="이름(모평/학평 등)" />
          <input v-model="exam.exam_date" type="date" />
          <button @click="createExam">회차 생성</button>
        </div>
        <div v-if="examId" style="margin-bottom:8px;">
          <b>exam_id: {{ examId }}</b>
        </div>
        <div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px;">
          <input v-model.number="score.score" type="number" placeholder="점수" />
          <select v-model="score.subject_code">
            <option>KOR</option><option>ENG</option><option>MATH</option><option>HIST</option>
            <option>SOC1</option><option>SOC2</option><option>SCI1</option><option>SCI2</option>
          </select>
          <input v-model="score.comment" placeholder="메모" />
          <button @click="saveScore" :disabled="!examId">점수 저장</button>
          <button @click="loadSummary" :disabled="!examId">요약</button>
        </div>
        <pre v-if="mockSummary">{{ mockSummary }}</pre>
      </section>
  
      <p v-if="err" style="color:#c00;">{{ err }}</p>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import api from "@/services/api";
  
  const tab = ref("mid"); // mid | final | mock
  const err = ref("");
  
  // --- Midterm ---
  const mid = ref({ student_id: null, subject_id: null, year: null, term: 1, score: 0, comment: "" });
  const qMid = ref({ student_id: null, year: null, term: 1 });
  const midSummary = ref(null);
  
  async function saveMid(){ err.value=""; try{
    await api.post("/grades/midterm", mid.value); alert("저장됨");
  } catch(e){ err.value = e?.response?.data?.detail || "중간 저장 실패"; }}
  async function loadMid(){ err.value=""; try{
    const { data } = await api.get("/grades/midterm/summary", { params: qMid.value }); midSummary.value = data;
  } catch(e){ err.value = e?.response?.data?.detail || "중간 요약 실패"; }}
  
  // --- Final ---
  const fin = ref({ student_id: null, subject_id: null, year: null, term: 1, score: 0, comment: "" });
  const qFin = ref({ student_id: null, year: null, term: 1 });
  const finSummary = ref(null);
  
  async function saveFinal(){ err.value=""; try{
    await api.post("/grades/final", fin.value); alert("저장됨");
  } catch(e){ err.value = e?.response?.data?.detail || "기말 저장 실패"; }}
  async function loadFinal(){ err.value=""; try{
    const { data } = await api.get("/grades/final/summary", { params: qFin.value }); finSummary.value = data;
  } catch(e){ err.value = e?.response?.data?.detail || "기말 요약 실패"; }}
  
  // --- Mock ---
  const exam = ref({ student_id:null, year:null, round:null, name:"모의고사", exam_date:"" });
  const examId = ref(null);
  const score = ref({ exam_id: null, subject_code: "KOR", score: 0, comment: "" });
  const mockSummary = ref(null);
  
  async function createExam(){ err.value=""; try{
    const { data } = await api.post("/grades/mock/exams", exam.value);
    examId.value = data.id; score.value.exam_id = data.id;
  } catch(e){ err.value = e?.response?.data?.detail || "회차 생성 실패"; }}
  
  async function saveScore(){ err.value=""; try{
    await api.post("/grades/mock/scores", score.value); alert("저장됨");
  } catch(e){ err.value = e?.response?.data?.detail || "점수 저장 실패"; }}
  
  async function loadSummary(){ err.value=""; try{
    const { data } = await api.get(`/grades/mock/summary/${examId.value}`);
    mockSummary.value = data;
  } catch(e){ err.value = e?.response?.data?.detail || "요약 실패"; }}
  </script>
  