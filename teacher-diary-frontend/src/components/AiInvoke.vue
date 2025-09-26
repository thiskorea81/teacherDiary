<!-- src/components/AiInvoke.vue -->
<template>
    <div :style="wrapStyle">
      <!-- 헤더 -->
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <strong>AI 호출</strong>
        <span class="badge" v-if="busy">요청 중…</span>
        <span class="badge" v-else>대기</span>
        <span style="margin-left:auto; font-size:12px; color:#666;">
          저장된 키를 사용합니다. <router-link to="/settings">환경설정</router-link>
        </span>
      </div>
  
      <!-- 제공자/모델 -->
      <div style="display:grid; gap:8px; grid-template-columns: 1fr; margin-top:8px;">
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
          <label>제공자</label>
          <select v-model="provider" :disabled="busy" style="min-width:180px;">
            <option value="gemini">Gemini (Google)</option>
            <option value="openai">OpenAI</option>
          </select>
  
          <label style="margin-left:8px;">
            <input type="checkbox" v-model="manualModel" :disabled="busy" />
            직접 입력
          </label>
  
          <template v-if="!manualModel">
            <select v-model="selectedModel" :disabled="busy" style="min-width:240px;">
              <option v-for="m in presetModels" :key="m" :value="m">{{ m }}</option>
            </select>
          </template>
          <template v-else>
            <input v-model="customModel" :disabled="busy" placeholder="모델명 직접 입력" style="min-width:280px;" />
          </template>
        </div>
      </div>
  
      <!-- 프롬프트 입력 -->
      <div style="margin-top:8px;">
        <textarea
          v-model="innerPrompt"
          :placeholder="promptPlaceholder"
          :rows="compact ? 3 : 6"
          :disabled="busy"
          style="width:100%; padding:10px; border:1px solid #ddd; border-radius:10px; resize:vertical;"
        />
      </div>
  
      <!-- 액션 -->
      <div style="display:flex; gap:8px; align-items:center; margin-top:10px;">
        <button @click="invoke" :disabled="busy || !canSend">실행</button>
        <button @click="clearAll" :disabled="busy || (!innerPrompt && !resultText && !errMsg)">지우기</button>
        <span v-if="errMsg" style="color:#c00;">{{ errMsg }}</span>
      </div>
  
      <!-- 결과 -->
      <div v-if="resultText" style="margin-top:12px; padding:12px; border:1px solid #eee; border-radius:10px;">
        <div style="font-weight:600; margin-bottom:6px;">
          {{ providerLabel }} 응답 (모델: {{ effectiveModel }})
        </div>
        <pre style="white-space:pre-wrap; margin:0;">{{ resultText }}</pre>
      </div>
  
      <!-- 슬롯으로 커스텀 표시 -->
      <slot name="footer"></slot>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, watch, onMounted } from "vue";
  import api from "@/services/api";
  
  /**
   * Props
   * - modelPresets: { gemini: string[], openai: string[] }
   * - defaultProvider: "gemini" | "openai"
   * - defaultModel: string | undefined
   * - prompt: string (초기값)
   * - compact: boolean (작게 표시)
   */
  const props = defineProps({
    modelPresets: {
      type: Object,
      default: () => ({
        openai: ["gpt-5", "gpt-5-mini", "gpt-5-nano"],
        gemini: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-live-2.5-flash-preview"],
      }),
    },
    defaultProvider: { type: String, default: "gemini" },
    defaultModel: { type: String, default: "" },
    prompt: { type: String, default: "" },
    compact: { type: Boolean, default: false },
  });
  
  /** Emits: result(text, meta), error(message) */
  const emit = defineEmits(["result", "error"]);
  
  const provider = ref(props.defaultProvider);
  const manualModel = ref(false);
  const selectedModel = ref("");
  const customModel = ref("");
  const innerPrompt = ref(props.prompt);
  const resultText = ref("");
  const errMsg = ref("");
  const busy = ref(false);
  
  const providerLabel = computed(() => (provider.value === "gemini" ? "Gemini" : "OpenAI"));
  const presetModels = computed(() => (provider.value === "gemini" ? props.modelPresets.gemini : props.modelPresets.openai));
  const effectiveModel = computed(() => (manualModel.value ? (customModel.value || "").trim() : (selectedModel.value || "").trim()));
  const canSend = computed(() => !!(innerPrompt.value && (effectiveModel.value || true))); // 모델 비우면 서버 기본값 사용
  
  const promptPlaceholder = computed(() =>
    `프롬프트를 입력하세요. (예: 담임 상담 프로그램을 한 줄로 소개해줘)`
  );
  
  const wrapStyle = computed(() =>
    props.compact
      ? "padding:12px; border:1px solid #eee; border-radius:12px; background:#fff;"
      : "padding:16px; border:1px solid #eee; border-radius:12px; background:#fff;"
  );
  
  function applyDefaults() {
    // 초기 모델: props.defaultModel 있으면 그대로, 없으면 제공자별 추천
    if (props.defaultModel) {
      manualModel.value = true;
      customModel.value = props.defaultModel;
    } else {
      manualModel.value = false;
      selectedModel.value = provider.value === "gemini" ? "gemini-2.5-flash" : "gpt-5-mini";
    }
  }
  
  watch(() => props.defaultProvider, (v) => {
    provider.value = v || "gemini";
    applyDefaults();
  });
  
  function clearAll() {
    resultText.value = "";
    errMsg.value = "";
  }
  
  async function invoke() {
    errMsg.value = "";
    resultText.value = "";
    busy.value = true;
    try {
      const body = {
        provider: provider.value,
        prompt: innerPrompt.value,
      };
      if (effectiveModel.value) body.model = effectiveModel.value;
  
      const { data } = await api.post("/settings/ai/test", body);
      resultText.value = data.output_text || "(빈 응답)";
      emit("result", resultText.value, { provider: provider.value, model: data.model });
    } catch (e) {
      const msg = e?.response?.data?.detail || "호출 실패";
      errMsg.value = msg;
      emit("error", msg);
    } finally {
      busy.value = false;
    }
  }
  
  onMounted(() => {
    applyDefaults();
  });
  </script>
  
  <style scoped>
  .badge {
    padding: 2px 8px;
    border-radius: 999px;
    background: #eef;
    font-size: 12px;
  }
  </style>
  