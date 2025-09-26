<template>
    <div class="wrap">
      <h2>담임: 학생정보 엑셀 업로드</h2>
  
      <section class="card">
        <h3>1) 템플릿 다운로드</h3>
        <p>헤더/순서를 반드시 유지해 주세요.</p>
        <button @click="downloadTemplate" :disabled="downloading">
          {{ downloading ? "다운로드 중..." : "템플릿(.xlsx) 받기" }}
        </button>
        <p v-if="downErr" class="err">{{ downErr }}</p>
      </section>
  
      <section class="card">
        <h3>2) 엑셀 업로드(업서트)</h3>
        <ul class="hint">
          <li>학년/반은 현재 로그인한 담임 매핑에 한해서만 처리됩니다.</li>
          <li>“학생개인번호”는 <b>PK(Student.id)</b>로 사용되어 있으면 업데이트, 없으면 생성됩니다.</li>
        </ul>
        <div class="row">
          <input type="file" accept=".xlsx" @change="onFile" />
          <button :disabled="!file || uploading" @click="uploadXlsx">
            {{ uploading ? "업로드 중..." : "업로드" }}
          </button>
        </div>
        <p v-if="upErr" class="err">{{ upErr }}</p>
  
        <div v-if="result" class="grid">
          <div><b>생성</b> ({{ result.created.length }}): {{ result.created.join(", ") || "-" }}</div>
          <div><b>업데이트</b> ({{ result.updated.length }}): {{ result.updated.join(", ") || "-" }}</div>
          <div><b>스킵</b> ({{ result.skipped.length }}): {{ result.skipped.join(", ") || "-" }}</div>
          <div v-if="result.skipped_reasons && Object.keys(result.skipped_reasons).length">
            <h4>스킵 사유</h4>
            <ul>
              <li v-for="(reason, key) in result.skipped_reasons" :key="key">
                <code>{{ key }}</code>: {{ reason }}
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import api from "@/services/api"; // 기존 axios 인스턴스 (Authorization 헤더 자동 포함)
  
  const downloading = ref(false);
  const downErr = ref("");
  
  async function downloadTemplate() {
    downErr.value = "";
    downloading.value = true;
    try {
      const res = await api.get("/homeroom/students/template.xlsx", {
        responseType: "blob",
      });
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "학생업로드_템플릿.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      downErr.value = e?.response?.data?.detail || "다운로드 실패";
    } finally {
      downloading.value = false;
    }
  }
  
  const file = ref(null);
  const uploading = ref(false);
  const upErr = ref("");
  const result = ref(null);
  
  function onFile(e) {
    file.value = e.target.files?.[0] || null;
  }
  
  async function uploadXlsx() {
    if (!file.value) return;
    upErr.value = ""; result.value = null; uploading.value = true;
    try {
      const fd = new FormData();
      fd.append("file", file.value);
      const { data } = await api.post("/homeroom/students/upload-xlsx", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      result.value = data;
    } catch (e) {
      upErr.value = e?.response?.data?.detail || "업로드 실패";
    } finally {
      uploading.value = false;
    }
  }
  </script>
  
  <style scoped>
  .wrap { max-width: 920px; margin: 0 auto; padding: 16px; }
  .card { background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 12px; margin: 12px 0; }
  .row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .grid { display: grid; gap: 8px; margin-top: 12px; }
  .hint { color:#666; margin: 6px 0 8px; }
  .err { color: #c00; }
  button { padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; background: #f8f9ff; cursor: pointer; }
  button:disabled { opacity: .6; cursor: not-allowed; }
  </style>
  