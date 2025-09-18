<!-- src/views/AdminUsersView.vue -->
<template>
  <div>
    <h2>관리자: 사용자 관리</h2>

    <!-- ============ 섹션 1: CSV 업로드 ============ -->
    <section style="margin:16px 0 24px;">
      <h3>일괄 업로드 (CSV)</h3>
      <p>형식: <code>username,email,role,password,full_name,teacher_id,student_id</code></p>
      <details style="margin:8px 0 12px;">
        <summary>예시 보기</summary>
        <pre>
username,email,role,password,full_name,teacher_id,student_id
t01,t01@sch.kr,teacher,Temp!234,김교사,1,
s1001,s1001@sch.kr,student,Std!234,홍학생,,101
        </pre>
      </details>

      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <input type="file" @change="onFile" accept=".csv" />
        <button :disabled="!file || loading" @click="upload">업로드</button>
        <span v-if="err" style="color:#c00;">{{ err }}</span>
        <span v-if="msg" :style="{color: msgOk ? '#0a0' : '#c00'}">{{ msg }}</span>
      </div>

      <div v-if="result" style="margin-top:16px; display:grid; gap:8px;">
        <div><b>생성</b> ({{ result.created.length }}): {{ result.created.join(", ") || "-" }}</div>
        <div><b>업데이트</b> ({{ result.updated.length }}): {{ result.updated.join(", ") || "-" }}</div>
        <div><b>스킵</b> ({{ result.skipped.length }}): {{ result.skipped.join(", ") || "-" }}</div>
      </div>
    </section>

    <hr/>

    <!-- ============ 섹션 2: 개별 비밀번호 초기화 ============ -->
    <section style="margin:24px 0;">
      <h3>개별 비밀번호 초기화</h3>
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <input v-model.number="resetUserId" type="number" placeholder="user_id" />
        <input v-model="resetPwd" type="text" placeholder="새 비밀번호" />
        <button :disabled="loading || !resetUserId || !resetPwd" @click="resetPassword">초기화</button>
        <span v-if="resetMsg" :style="{color: resetOk ? '#0a0' : '#c00'}">{{ resetMsg }}</span>
      </div>
      <p style="font-size:12px; color:#666; margin-top:6px;">
        초기화하면 해당 사용자는 <b>다음 로그인 시 비밀번호 변경이 강제</b>됩니다.
      </p>
    </section>

    <hr/>

    <!-- ============ 섹션 3: 승인 대기 사용자 목록 ============ -->
    <section style="margin:24px 0;">
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <h3 style="margin:0;">승인 대기 사용자</h3>
        <button @click="loadPending" :disabled="pendingLoading" title="새로고침">새로고침</button>
      </div>

      <table class="table" style="margin-top:12px;">
        <thead>
          <tr>
            <th>ID</th><th>username</th><th>email</th><th>role</th><th>이름</th><th>teacher_id</th><th>student_id</th><th>작업</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in pending" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.role }}</td>
            <td>{{ u.full_name || '-' }}</td>
            <td>{{ u.teacher_id ?? '-' }}</td>
            <td>{{ u.student_id ?? '-' }}</td>
            <td>
              <button @click="approve(u.id, true)" :disabled="actBusy === u.id">승인</button>
              <button @click="approve(u.id, false)" :disabled="actBusy === u.id" style="margin-left:6px;">거부(비활성)</button>
            </td>
          </tr>
          <tr v-if="!pending.length">
            <td colspan="8">대기 중인 사용자가 없습니다.</td>
          </tr>
        </tbody>
      </table>
      <p v-if="pendingErr" style="color:#c00;">{{ pendingErr }}</p>
    </section>

    <hr/>

    <!-- ============ 섹션 4: 승인된(활성) 사용자 목록 ============ -->
    <section style="margin:24px 0;">
      <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
        <h3 style="margin:0;">승인된 사용자</h3>
        <input v-model="kw" placeholder="이름/아이디/이메일 검색" />
        <select v-model="roleFilter">
          <option value="">전체</option>
          <option value="teacher">teacher</option>
          <option value="student">student</option>
          <option value="admin">admin</option>
        </select>
        <button @click="loadActive" :disabled="activeLoading" title="새로고침">새로고침</button>
      </div>

      <table class="table" style="margin-top:12px;">
        <thead>
          <tr>
            <th>ID</th><th>username</th><th>email</th><th>role</th><th>이름</th><th>teacher_id</th><th>student_id</th><th>작업</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in filteredActive" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.role }}</td>
            <td>{{ u.full_name || '-' }}</td>
            <td>{{ u.teacher_id ?? '-' }}</td>
            <td>{{ u.student_id ?? '-' }}</td>
            <td>
              <!-- 승인 취소 = 비활성화 -->
              <button @click="approve(u.id, false)" :disabled="actBusy === u.id">비활성화</button>
              <!-- 재승인 버튼도 같이 제공 -->
              <button @click="approve(u.id, true)" :disabled="actBusy === u.id" style="margin-left:6px;">재승인</button>
            </td>
          </tr>
          <tr v-if="!filteredActive.length">
            <td colspan="8">일치하는 사용자가 없습니다.</td>
          </tr>
        </tbody>
      </table>
      <p v-if="activeErr" style="color:#c00;">{{ activeErr }}</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import api from "@/services/api";

/* ---------------- CSV 업로드 ---------------- */
const file = ref(null);
const loading = ref(false);
const err = ref("");
const msg = ref("");
const msgOk = ref(false);
const result = ref(null);

function onFile(e){ file.value = e.target.files?.[0] || null; }

async function upload(){
  if(!file.value) return;
  loading.value = true; err.value = ""; msg.value = ""; result.value = null;
  try{
    const fd = new FormData();
    fd.append("file", file.value);
    const { data } = await api.post("/auth/admin/bulk_csv", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    result.value = data;
    msg.value = "업로드 완료"; msgOk.value = true;
    await Promise.all([loadPending(), loadActive()]);
  }catch(e){
    err.value = e?.response?.data?.detail || "업로드 실패";
    msg.value = ""; msgOk.value = false;
  }finally{
    loading.value = false;
  }
}

/* ---------------- 개별 비번 초기화 ---------------- */
const resetUserId = ref(null);
const resetPwd = ref("");
const resetMsg = ref("");
const resetOk = ref(false);

async function resetPassword(){
  resetMsg.value = ""; resetOk.value = false;
  try{
    await api.post("/auth/admin/reset_password", {
      user_id: resetUserId.value,
      new_password: resetPwd.value
    });
    resetMsg.value = "초기화 완료 (다음 로그인 시 비번 변경 강제)";
    resetOk.value = true;
  }catch(e){
    resetMsg.value = e?.response?.data?.detail || "초기화 실패";
  }
}

/* ---------------- 승인 대기 목록 ---------------- */
const pending = ref([]);
const pendingLoading = ref(false);
const pendingErr = ref("");

async function loadPending(){
  pendingLoading.value = true; pendingErr.value = "";
  try{
    const { data } = await api.get("/auth/admin/pending");
    pending.value = data;
  }catch(e){
    pendingErr.value = e?.response?.data?.detail || "대기 목록 조회 실패";
  }finally{
    pendingLoading.value = false;
  }
}

/* ---------------- 승인된(활성) 목록 ---------------- */
const active = ref([]);
const activeLoading = ref(false);
const activeErr = ref("");
const kw = ref("");
const roleFilter = ref("");

async function loadActive(){
  activeLoading.value = true; activeErr.value = "";
  try{
    const { data } = await api.get("/auth/admin/active");
    active.value = data;
  }catch(e){
    activeErr.value = e?.response?.data?.detail || "활성 목록 조회 실패";
  }finally{
    activeLoading.value = false;
  }
}

const filteredActive = computed(() => {
  const q = kw.value.trim().toLowerCase();
  const rf = roleFilter.value;
  return active.value.filter(u => {
    const hit = !q || `${u.username} ${u.email} ${u.full_name || ""}`.toLowerCase().includes(q);
    const roleOk = !rf || u.role === rf;
    return hit && roleOk;
  });
});

/* ---------------- 공통: 승인/거부(비활성) ---------------- */
const actBusy = ref(null);
async function approve(user_id, approve=true){
  actBusy.value = user_id;
  try{
    await api.post("/auth/admin/approve", { user_id, approve });
    // 두 목록 모두 갱신
    await Promise.all([loadPending(), loadActive()]);
  }catch(e){
    const m = e?.response?.data?.detail || "처리 실패";
    // 에러를 섹션별 메시지로 보여주기
    pendingErr.value = m;
    activeErr.value = m;
  }finally{
    actBusy.value = null;
  }
}

onMounted(() => { loadPending(); loadActive(); });
</script>

<style>
.table { width:100%; border-collapse: collapse; }
.table th, .table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; }
.badge { padding: 2px 8px; border-radius: 999px; background:#eee; font-size: 12px; }
</style>
