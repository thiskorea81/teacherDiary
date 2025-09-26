<!-- src/views/AdminUsersView.vue -->
<template>
  <div>
    <h2>관리자: 사용자 관리</h2>

    <!-- Tabs -->
    <nav class="tabs">
      <button :class="{active: tab==='upload'}" @click="tab='upload'">CSV 업로드</button>
      <button :class="{active: tab==='pending'}" @click="tab='pending'">승인 대기</button>
      <button :class="{active: tab==='active'}" @click="tab='active'">승인된 사용자</button>
      <button :class="{active: tab==='archived'}" @click="tab='archived'">보관된 사용자</button>
      <button :class="{active: tab==='danger'}" @click="tab='danger'">DB 전체 삭제</button>
    </nav>

    <!-- ============ 탭: CSV 업로드(단일/간단형) ============ -->
    <section v-if="tab==='upload'" class="panel">
      <h3>일괄 업로드 (간단 형식)</h3>
      <p>
        형식:
        <code>username,password,full_name,role</code>
        <small style="color:#666;"> (교사는 <b>t*</b>, 학생은 <b>s*</b>로 시작)</small>
      </p>
      <details style="margin:8px 0 12px;">
        <summary>예시 보기</summary>
        <pre>
username,password,full_name,role
t01,Temp!234,김교사,teacher
s1001,Std!234,홍학생,student
        </pre>
      </details>

      <div class="row">
        <input type="file" @change="onFile" accept=".csv" />
        <button :disabled="!file || loading" @click="uploadSimple">업로드</button>
        <button @click="downloadTemplate('simple')">양식 다운로드</button>
        <span v-if="err" class="err">{{ err }}</span>
        <span v-if="msg" :class="{'ok': msgOk, 'err': !msgOk}">{{ msg }}</span>
      </div>

      <div v-if="result" class="grid">
        <div><b>생성</b> ({{ result.created.length }}): {{ result.created.join(", ") || "-" }}</div>
        <div><b>업데이트</b> ({{ (result.updated||[]).length }}): {{ (result.updated||[]).join(", ") || "-" }}</div>
        <div><b>스킵</b> ({{ (result.skipped||[]).length }}): {{ (result.skipped||[]).join(", ") || "-" }}</div>
        <div v-if="result.skipped_reasons">
          <h4 style="margin:6px 0 0;">스킵 사유</h4>
          <ul style="margin:0;">
            <li v-for="(reason, uname) in result.skipped_reasons" :key="uname">
              <code>{{ uname }}</code>: {{ reason }}
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- ============ 탭: 승인 대기 ============ -->
    <section v-if="tab==='pending'" class="panel">
      <div class="row">
        <h3>승인 대기 사용자</h3>
        <button @click="loadPending" :disabled="pendingLoading" title="새로고침">새로고침</button>
      </div>

      <table class="table">
        <thead>
        <tr>
          <th>ID</th><th>username</th><th>email</th><th>role</th><th>이름</th>
          <th>teacher_id</th><th>student_id</th><th style="width:220px;">작업</th>
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
          <td class="cell-actions">
            <button @click="approve(u.id, true)" :disabled="actBusy === u.id">승인</button>
            <button @click="resetPasswordFor(u)" :disabled="actBusy === u.id">비번 초기화</button>
          </td>
        </tr>
        <tr v-if="!pending.length">
          <td colspan="8">대기 중인 사용자가 없습니다.</td>
        </tr>
        </tbody>
      </table>
      <p v-if="pendingErr" class="err">{{ pendingErr }}</p>
    </section>

    <!-- ============ 탭: 승인된 사용자 ============ -->
    <section v-if="tab==='active'" class="panel">
      <div class="row wrap">
        <h3>승인된 사용자</h3>
        <input v-model="kw" placeholder="이름/아이디/이메일 검색" />
        <select v-model="roleFilter">
          <option value="">전체</option>
          <option value="teacher">teacher</option>
          <option value="student">student</option>
          <option value="admin">admin</option>
        </select>
        <button @click="loadActive" :disabled="activeLoading">새로고침</button>
        <button @click="toggleSelectAllActive" :disabled="!filteredActive.length">전체선택/해제</button>
        <span class="badge" v-if="selectedActiveIds.length">{{ selectedActiveIds.length }} 선택됨</span>
      </div>

      <!-- 퀵 액션 바 -->
      <div class="row">
        <span class="badge">선택: {{ selectedActiveIds.length }}</span>
        <input v-model.number="archiveYear" type="number" placeholder="보관 연도(예: 2025)" style="width:140px" />
        <button :disabled="!selectedActiveIds.length || !archiveYear || busyArchive" @click="archiveSelected">보관 처리</button>
        <button :disabled="!selectedActiveIds.length || busyDelete" @click="deleteSelected">삭제</button>
        <button :disabled="!selectedActiveIds.length || busyBulkReset" @click="bulkResetSelected" title="선택 사용자 비밀번호를 a123456789! 로 초기화">비번 일괄 초기화</button>
        <span v-if="barMsg" :class="{'ok': barOk, 'err': !barOk}">{{ barMsg }}</span>
      </div>

      <table class="table">
        <thead>
        <tr>
          <th style="width:36px;"></th>
          <th>ID</th><th>username</th><th>email</th><th>role</th><th>이름</th><th>teacher_id</th><th>student_id</th><th style="width:220px;">작업</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="u in filteredActive" :key="u.id">
          <td><input type="checkbox" :value="u.id" v-model="selectedActiveIds" /></td>
          <td>{{ u.id }}</td>
          <td>{{ u.username }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.role }}</td>
          <td>{{ u.full_name || '-' }}</td>
          <td>{{ u.teacher_id ?? '-' }}</td>
          <td>{{ u.student_id ?? '-' }}</td>
          <td class="cell-actions">
            <button @click="approve(u.id, false)" :disabled="actBusy === u.id">비활성화</button>
            <button @click="resetPasswordFor(u)" :disabled="actBusy === u.id">비번 초기화</button>
          </td>
        </tr>
        <tr v-if="!filteredActive.length">
          <td colspan="9">일치하는 사용자가 없습니다.</td>
        </tr>
        </tbody>
      </table>
      <p v-if="activeErr" class="err">{{ activeErr }}</p>
    </section>

    <!-- ============ 탭: 보관된 사용자 ============ -->
    <section v-if="tab==='archived'" class="panel">
      <div class="row">
        <h3>보관된 사용자</h3>
        <button @click="loadArchived" :disabled="archivedLoading">새로고침</button>
        <button @click="toggleSelectAllArchived" :disabled="!archived.length">전체선택/해제</button>
        <button :disabled="!selectedArchivedIds.length || busyUnarchive" @click="unarchiveSelected">보관 해제</button>
        <span class="badge" v-if="selectedArchivedIds.length">{{ selectedArchivedIds.length }} 선택됨</span>
        <span v-if="archMsg" :class="{'ok': archOk, 'err': !archOk}">{{ archMsg }}</span>
      </div>

      <table class="table">
        <thead>
        <tr>
          <th style="width:36px;"></th>
          <th>ID</th><th>username</th><th>email</th><th>role</th><th>이름</th><th>보관연도</th><th style="width:140px;">작업</th>
        </tr>
        </thead>
        <tbody>
        <tr v-for="u in archived" :key="u.id">
          <td><input type="checkbox" :value="u.id" v-model="selectedArchivedIds" /></td>
          <td>{{ u.id }}</td>
          <td>{{ u.username }}</td>
          <td>{{ u.email }}</td>
          <td>{{ u.role }}</td>
          <td>{{ u.full_name || '-' }}</td>
          <td>{{ u.archived_year ?? '-' }}</td>
          <td class="cell-actions">
            <button @click="resetPasswordFor(u)" :disabled="busyUnarchive">비번 초기화</button>
          </td>
        </tr>
        <tr v-if="!archived.length">
          <td colspan="8">보관된 사용자가 없습니다.</td>
        </tr>
        </tbody>
      </table>
    </section>

    <!-- ============ 탭: DB 전체 삭제 ============ -->
    <section v-if="tab==='danger'" class="panel danger">
      <h3>DB 전체 삭제 (초치명)</h3>
      <p class="err" style="margin:6px 0 10px;">
        이 작업은 <b>모든 테이블을 드롭 후 재생성</b>합니다. 되돌릴 수 없습니다.
      </p>
      <div class="row">
        <input v-model="wipeConfirm" placeholder="WIPE-ALL 입력" />
        <button :disabled="wipeBusy || wipeConfirm !== 'WIPE-ALL'" @click="wipeAll">전체 삭제</button>
        <span v-if="wipeMsg" :class="{'ok': wipeOk, 'err': !wipeOk}">{{ wipeMsg }}</span>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from "vue";
import api from "@/services/api";

/* ---------------- Tabs ---------------- */
const tab = ref("upload");

/* ---------------- CSV 업로드(간단) ---------------- */
const file = ref(null);
const loading = ref(false);
const err = ref("");
const msg = ref("");
const msgOk = ref(false);
const result = ref(null);

function onFile(e){ file.value = e.target.files?.[0] || null; }

async function uploadSimple(){
  if(!file.value) return;
  loading.value = true; err.value=""; msg.value=""; result.value=null;
  try{
    const fd = new FormData();
    fd.append("file", file.value);
    const { data } = await api.post("/auth/admin/bulk_users_simple", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    result.value = data;
    msg.value = "업로드 완료"; msgOk.value = true;
    await Promise.all([loadPending(), loadActive(), loadArchived()]);
  }catch(e){
    err.value = e?.response?.data?.detail || "업로드 실패";
    msg.value = ""; msgOk.value = false;
  }finally{
    loading.value = false;
  }
}

async function downloadTemplate(kind = "simple"){
  try{
    const { data } = await api.get(`/auth/admin/csv_template`, {
      params: { kind },
      responseType: "blob",
    });
    const blob = new Blob([data], { type: "text/csv;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    const now = new Date();
    const ts = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,"0")}${String(now.getDate()).padStart(2,"0")}_${String(now.getHours()).padStart(2,"0")}${String(now.getMinutes()).padStart(2,"0")}${String(now.getSeconds()).padStart(2,"0")}`;
    a.href = url;
    a.download = `bulk_users_simple_${ts}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    window.URL.revokeObjectURL(url);
  }catch(e){
    alert(e?.response?.data?.detail || "템플릿 다운로드 실패");
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

/* ---------------- 승인/비활성 ---------------- */
const actBusy = ref(null);
async function approve(user_id, approve=true){
  actBusy.value = user_id;
  try{
    await api.post("/auth/admin/approve", { user_id, approve });
    await Promise.all([loadPending(), loadActive()]);
  }catch(e){
    const m = e?.response?.data?.detail || "처리 실패";
    pendingErr.value = m; activeErr.value = m;
  }finally{
    actBusy.value = null;
  }
}

/* ---------------- 행 버튼: 비번 초기화 ---------------- */
async function resetPasswordFor(user){
  const input = prompt(`새 비밀번호를 입력하세요\n(사용자: ${user.username})`);
  if(!input) return;
  try{
    await api.post("/auth/admin/reset_password", {
      user_id: user.id,
      new_password: input
    });
    alert("초기화 완료 (다음 로그인 시 비밀번호 변경이 강제됩니다)");
  }catch(e){
    alert(e?.response?.data?.detail || "초기화 실패");
  }
}

/* ---------------- 선택/보관/삭제/일괄 초기화 ---------------- */
const selectedActiveIds = ref([]);
function toggleSelectAllActive(){
  if(selectedActiveIds.value.length === filteredActive.value.length){
    selectedActiveIds.value = [];
  }else{
    selectedActiveIds.value = filteredActive.value.map(u => u.id);
  }
}

const archiveYear = ref();
const busyArchive = ref(false);
const busyDelete = ref(false);
const barMsg = ref(""); const barOk = ref(false);

async function archiveSelected(){
  if(!selectedActiveIds.value.length || !archiveYear.value) return;
  busyArchive.value = true; barMsg.value=""; barOk.value=false;
  try{
    await api.post("/auth/admin/users/archive", {
      user_ids: selectedActiveIds.value,
      year: Number(archiveYear.value),
    });
    barOk.value = true; barMsg.value = "보관 처리 완료";
    selectedActiveIds.value = [];
    await Promise.all([loadActive(), loadArchived()]);
  }catch(e){
    barMsg.value = e?.response?.data?.detail || "보관 처리 실패";
  }finally{
    busyArchive.value = false;
  }
}

async function deleteSelected(){
  if(!selectedActiveIds.value.length) return;
  if(!confirm("선택한 사용자를 삭제합니다. 관리자/본인은 삭제되지 않습니다. 계속할까요?")) return;
  busyDelete.value = true; barMsg.value=""; barOk.value=false;
  try{
    await api.post("/auth/admin/users/delete", {
      user_ids: selectedActiveIds.value
    });
    barOk.value = true; barMsg.value = "삭제 처리 완료";
    selectedActiveIds.value = [];
    await Promise.all([loadPending(), loadActive(), loadArchived()]);
  }catch(e){
    barMsg.value = e?.response?.data?.detail || "삭제 실패";
  }finally{
    busyDelete.value = false;
  }
}

const busyBulkReset = ref(false);
async function bulkResetSelected(){
  if(!selectedActiveIds.value.length) return;
  if(!confirm(`선택된 ${selectedActiveIds.value.length}명의 비밀번호를 'a123456789!' 로 초기화합니다. 계속할까요?`)) return;
  busyBulkReset.value = true; barMsg.value = ""; barOk.value = false;
  try{
    const { data } = await api.post("/auth/admin/reset_password_bulk", {
      user_ids: selectedActiveIds.value
    });
    barOk.value = true;
    barMsg.value = `초기화 완료: ${data.updated.length}명 (비번: ${data.password})`;
    selectedActiveIds.value = [];
    await Promise.all([loadActive(), loadArchived()]);
  }catch(e){
    barMsg.value = e?.response?.data?.detail || "일괄 초기화 실패";
  }finally{
    busyBulkReset.value = false;
  }
}

/* ---------------- 보관 목록 / 보관 해제 ---------------- */
const archived = ref([]);
const archivedLoading = ref(false);
const selectedArchivedIds = ref([]);
const archMsg = ref(""); const archOk = ref(false);
const busyUnarchive = ref(false);

async function loadArchived(){
  archivedLoading.value = true; archMsg.value="";
  try{
    const { data } = await api.get("/auth/admin/users/archived");
    archived.value = data;
  }catch(e){
    archMsg.value = e?.response?.data?.detail || "보관 목록 조회 실패"; archOk.value = false;
  }finally{
    archivedLoading.value = false;
  }
}

function toggleSelectAllArchived(){
  if(selectedArchivedIds.value.length === archived.value.length){
    selectedArchivedIds.value = [];
  }else{
    selectedArchivedIds.value = archived.value.map(u => u.id);
  }
}

async function unarchiveSelected(){
  if(!selectedArchivedIds.value.length) return;
  busyUnarchive.value = true; archMsg.value=""; archOk.value=false;
  try{
    await api.post("/auth/admin/users/unarchive", {
      user_ids: selectedArchivedIds.value
    });
    archOk.value = true; archMsg.value = "보관 해제 완료";
    selectedArchivedIds.value = [];
    await Promise.all([loadActive(), loadArchived()]);
  }catch(e){
    archMsg.value = e?.response?.data?.detail || "보관 해제 실패";
  }finally{
    busyUnarchive.value = false;
  }
}

/* ---------------- DB 전체 삭제 ---------------- */
const wipeConfirm = ref("");
const wipeBusy = ref(false);
const wipeMsg = ref(""); const wipeOk = ref(false);

async function wipeAll(){
  if(wipeConfirm.value !== "WIPE-ALL") return;
  if(!confirm("정말 DB 전체를 삭제하고 재생성할까요? 이 작업은 되돌릴 수 없습니다.")) return;
  wipeBusy.value = true; wipeMsg.value=""; wipeOk.value=false;
  try{
    await api.post("/auth/admin/db/wipe_all", { confirm: "WIPE-ALL" });
    wipeOk.value = true; wipeMsg.value = "DB 초기화 완료 (모든 테이블 재생성)";
  }catch(e){
    wipeMsg.value = e?.response?.data?.detail || "DB 초기화 실패";
  }finally{
    wipeBusy.value = false;
  }
}

/* ---------------- Init ---------------- */
onMounted(() => { loadPending(); loadActive(); loadArchived(); });
</script>

<style>
.tabs { display:flex; gap:8px; margin:10px 0 16px; flex-wrap:wrap; }
.tabs button { padding:8px 12px; border:1px solid #ddd; border-radius:8px; background:#fff; cursor:pointer; }
.tabs button.active { background:#f2f6ff; border-color:#8aa0ff; color:#2a47cc; }

.panel { padding:12px; border:1px solid #eee; border-radius:12px; background:#fff; }
.panel.danger { border-color:#f3c; background:#fff6fb; }

.row { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:8px 0; }
.row.wrap { flex-wrap:wrap; }
.grid { margin-top:16px; display:grid; gap:8px; }
.table { width:100%; border-collapse: collapse; margin-top:12px; }
.table th, .table td { border-bottom: 1px solid #eee; padding: 8px; text-align: left; vertical-align: middle; }
.badge { padding: 2px 8px; border-radius: 999px; background:#eee; font-size: 12px; }
.ok { color:#0a0; }
.err { color:#c00; }
.cell-actions { display:flex; gap:6px; align-items:center; }
</style>
