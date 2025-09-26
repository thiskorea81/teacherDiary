<!-- src/components/HomeroomSelector.vue -->
<template>
    <div class="card">
      <h3>담임 반 설정</h3>
      <p class="hint">학년도/학년/반을 선택해 저장하면, 현재 계정에 담임 반이 매핑됩니다.</p>
  
      <div class="row">
        <label>학년도</label>
        <input type="number" v-model.number="year" min="2000" max="2100" />
        <button @click="toThisYear">올해로</button>
      </div>
  
      <div class="row">
        <label>학년</label>
        <select v-model.number="grade">
          <option v-for="g in [1,2,3]" :key="g" :value="g">{{ g }}</option>
        </select>
  
        <label>반</label>
        <select v-model.number="classNo">
          <option v-for="c in classRange" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
  
      <div class="row">
        <button :disabled="busy" @click="save">저장</button>
        <span v-if="msg" :class="{'ok': ok, 'err': !ok}">{{ msg }}</span>
      </div>
  
      <div class="current">
        <b>현재 배정</b>:
        <span v-if="current"> {{ current.school_year }}학년도 {{ current.grade }}학년 {{ current.class_no }}반 </span>
        <span v-else> 없음 </span>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted, computed } from "vue";
  import api from "@/services/api";
  
  const busy = ref(false);
  const msg = ref("");
  const ok = ref(false);
  
  const year = ref(new Date().getFullYear());
  const grade = ref(1);
  const classNo = ref(1);
  const classRange = computed(() => Array.from({length: 30}, (_,i)=>i+1));
  
  const current = ref(null);
  
  function toThisYear(){ year.value = new Date().getFullYear(); }
  
  async function loadCurrent(){
    msg.value=""; ok.value=false;
    try{
      const { data } = await api.get(`/settings/me/homeroom`, { params: { year: year.value }});
      current.value = data; // null 가능
      if(data){
        grade.value = data.grade;
        classNo.value = data.class_no;
      }
    }catch(e){
      // 권한이 없으면 숨죽이기
    }
  }
  
  async function save(){
    busy.value = true; msg.value=""; ok.value=false;
    try{
      const { data } = await api.put(`/settings/me/homeroom`, {
        school_year: Number(year.value),
        grade: Number(grade.value),
        class_no: Number(classNo.value),
      });
      current.value = data;
      ok.value = true; msg.value = "저장되었습니다.";
    }catch(e){
      ok.value = false;
      msg.value = e?.response?.data?.detail || "저장 실패";
    }finally{
      busy.value = false;
    }
  }
  
  onMounted(loadCurrent);
  </script>
  
  <style scoped>
  .card { padding:12px; border:1px solid #eee; border-radius:12px; background:#fff; }
  .row { display:flex; gap:8px; align-items:center; margin:8px 0; flex-wrap:wrap; }
  .hint { color:#666; margin:4px 0 12px; }
  .current { margin-top:10px; }
  .ok { color:#0a0; }
  .err { color:#c00; }
  label { font-size:14px; color:#444; }
  </style>
  