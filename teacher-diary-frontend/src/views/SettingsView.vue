<template>
     <div class="settings">
      <h2>환경설정</h2>
  
      <section style="margin-top:16px;">
        <h3>AI 제공자 & API 키</h3>
  
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <label>제공자</label>
          <select v-model="provider" @change="onProviderChange" style="min-width:180px;">
            <option value="gemini">Gemini (Google)</option>
            <option value="openai">OpenAI</option>
          </select>
          <span v-if="state.has_key" class="badge">저장됨: {{ state.masked }}</span>
          <span v-else class="badge" style="background:#ffe;">미저장</span>
          <button @click="loadKey" :disabled="loading">새로고침</button>
        </div>
  
        <p style="color:#666; font-size:14px; margin-top:8px;">
          키는 서버에서 <b>암호화</b>되어 저장됩니다. 조회 시 마지막 4자리만 표시됩니다.
        </p>
  
        <!-- 모델 선택 -->
        <div style="margin-top:12px; padding:12px; border:1px solid #eee; border-radius:10px;">
          <h4 style="margin:0 0 8px;">모델 선택</h4>
          <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <label><input type="checkbox" v-model="manualModel" /> 직접 입력</label>
  
            <template v-if="!manualModel">
              <select v-model="selectedModel" style="min-width:240px;">
                <option v-for="m in presetModels" :key="m" :value="m">{{ m }}</option>
              </select>
            </template>
  
            <template v-else>
              <input v-model="customModel" placeholder="모델명을 직접 입력하세요" style="min-width:280px;" />
            </template>
          </div>
          <p style="color:#777; font-size:12px; margin-top:6px;">
            OpenAI: gpt-5, gpt-5-mini, gpt-5-nano &nbsp;|&nbsp;
            Gemini: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-live-2.5-flash-preview
          </p>
        </div>
  
        <!-- 키 저장/삭제 + 테스트 -->
        <form @submit.prevent="save" style="display:grid; gap:10px; margin-top:12px;">
          <label>새 {{ providerLabel }} API 키</label>
          <input v-model="apiKey" type="password" :placeholder="placeholderFor(provider)" />
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button :disabled="saving || !apiKey">저장</button>
            <button type="button" :disabled="deleting || !state.has_key" @click="remove">삭제</button>
            <button type="button" :disabled="testing" @click="testCall">테스트 호출</button>
          </div>
          <p v-if="msg" :style="{color: ok ? '#0a0' : '#c00', whiteSpace:'pre-wrap'}">{{ msg }}</p>
        </form>
  
        <div v-if="testResult" style="margin-top:12px; padding:12px; border:1px solid #eee; border-radius:10px;">
          <div style="font-weight:600; margin-bottom:6px;">{{ providerLabel }} 응답</div>
          <pre style="white-space:pre-wrap; margin:0;">{{ testResult }}</pre>
        </div>
      </section>

      <!-- 담임 반 설정 (교사/관리자만) -->
      <section class="panel">
        <HomeroomSelector />
      </section>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, watch, onMounted } from "vue";
  import { useAuthStore } from "@/stores/auth";
  import api from "@/services/api";
  import HomeroomSelector from "@/components/HomeroomSelector.vue";
  
  const provider = ref("gemini");           // "gemini" | "openai"
  const state = ref({ has_key:false, masked:null });
  const apiKey = ref("");
  const loading = ref(false);
  const saving = ref(false);
  const deleting = ref(false);
  const testing = ref(false);
  const msg = ref(""); const ok = ref(false);
  const testResult = ref("");
  const auth = useAuthStore();
  const isTeacherOrAdmin = computed(() => ["teacher","admin"].includes(auth.user?.role));
  
  // 모델 관련
  const manualModel = ref(false);
  const selectedModel = ref("");   // 프리셋 중 선택
  const customModel = ref("");     // 직접 입력
  const providerLabel = computed(() => provider.value === "gemini" ? "Gemini" : "OpenAI");
  
  const OPENAI_PRESETS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"];
  const GEMINI_PRESETS = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-live-2.5-flash-preview"];
  
  const presetModels = computed(() =>
    provider.value === "gemini" ? GEMINI_PRESETS : OPENAI_PRESETS
  );
  
  // provider가 바뀔 때 적절한 기본 모델 세팅
  function onProviderChange(){
    manualModel.value = false;
    selectedModel.value = (provider.value === "gemini" ? "gemini-2.5-flash" : "gpt-5-mini");
    customModel.value = "";
    loadKey();
  }
  
  watch(provider, () => onProviderChange());
  
  function placeholderFor(p){
    return p === "gemini" ? "예: AIza... (Google API 키)" : "예: sk-..."
  }
  
  async function loadKey(){
    loading.value = true; msg.value = ""; ok.value = false; testResult.value = "";
    try{
      const { data } = await api.get(`/settings/me/ai-key/${provider.value}`);
      state.value = data;
    }catch(e){
      state.value = { has_key:false, masked:null };
      msg.value = e?.response?.data?.detail || "조회 실패";
    }finally{
      loading.value = false;
    }
  }
  
  async function save(){
    saving.value = true; msg.value=""; ok.value=false;
    try{
      const { data } = await api.post("/settings/me/ai-key", {
        provider: provider.value,
        api_key: apiKey.value,
      });
      state.value = data;
      apiKey.value = "";
      ok.value = true; msg.value = "저장되었습니다.";
    }catch(e){
      msg.value = e?.response?.data?.detail || "저장 실패";
    }finally{
      saving.value = false;
    }
  }
  
  async function remove(){
    deleting.value = true; msg.value=""; ok.value=false;
    try{
      await api.delete(`/settings/me/ai-key/${provider.value}`);
      await loadKey();
      ok.value = true; msg.value = "삭제되었습니다.";
    }catch(e){
      msg.value = e?.response?.data?.detail || "삭제 실패";
    }finally{
      deleting.value = false;
    }
  }
  
  function currentModel(){
    if (manualModel.value) {
      return (customModel.value || "").trim();
    }
    return (selectedModel.value || "").trim();
  }
  
  async function testCall(){
    const model = currentModel();
    testing.value = true; msg.value=""; ok.value=false; testResult.value="";
    try{
      const { data } = await api.post("/settings/ai/test", {
        provider: provider.value,
        prompt: "이 시스템(담임 상담 프로그램)을 한 줄로 소개해줘.",
        model: model || undefined, // 비어있으면 서버 디폴트
      });
      ok.value = true;
      testResult.value = data.output_text || "(빈 응답)";
    }catch(e){
      msg.value = e?.response?.data?.detail || "테스트 실패";
    }finally{
      testing.value = false;
    }
  }
  
  onMounted(() => {
    selectedModel.value = "gemini-2.5-flash";
    loadKey();
  });
  </script>
  
  <style>
  .badge { padding: 2px 8px; border-radius: 999px; background:#eef; font-size: 12px; }
  .settings { display:grid; gap:16px; }
  .panel { padding:12px; border:1px solid #eee; border-radius:12px; background:#fff; }
  </style>
  