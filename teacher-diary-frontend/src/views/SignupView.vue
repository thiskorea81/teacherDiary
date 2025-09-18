<script setup>
import { ref } from "vue";
import api from "@/services/api";
import { useRouter } from "vue-router";

const router = useRouter();
const f = ref({
  username: "", email: "", full_name: "",
  role: "teacher",              // 기본 교사
  password: "", teacher_id: null, student_id: null
});
const loading = ref(false); const err = ref(""); const ok = ref(false);

async function submit(){
  loading.value = true; err.value = ""; ok.value = false;
  try{
    // ✅ admin 가입 불가 (백엔드도 차단함)
    if (f.value.role === "admin") {
      err.value = "관리자 계정은 직접 가입할 수 없습니다."; loading.value=false; return;
    }
    await api.post("/auth/signup", f.value);
    ok.value = true;
    // ✅ 승인 대기 안내 페이지로
    setTimeout(()=> router.push({ name:"pending-approval" }), 600);
  }catch(e){
    err.value = e?.response?.data?.detail || "가입 실패";
  }finally{
    loading.value = false;
  }
}
</script>

<template>
  <div style="max-width:540px; margin:40px auto;">
    <h2>회원가입</h2>
    <p class="badge" style="background:#eef; color:#334;">가입 후 관리자의 승인이 필요합니다.</p>
    <form @submit.prevent="submit" style="display:grid; gap:10px;">
      <label>아이디</label>
      <input v-model="f.username" required />
      <label>이메일</label>
      <input v-model="f.email" type="email" required />
      <label>이름</label>
      <input v-model="f.full_name" />
      <label>역할</label>
      <select v-model="f.role">
        <option value="teacher">teacher</option>
        <option value="student">student</option>
      </select>
      <label>비밀번호</label>
      <input v-model="f.password" type="password" required />

      <label v-if="f.role==='teacher'">teacher_id (선택)</label>
      <input v-if="f.role==='teacher'" v-model.number="f.teacher_id" type="number" />
      <label v-if="f.role==='student'">student_id (선택)</label>
      <input v-if="f.role==='student'" v-model.number="f.student_id" type="number" />

      <button :disabled="loading">가입하기</button>
      <p v-if="err" style="color:#c00;">{{ err }}</p>
      <p v-if="ok" style="color:#0a0;">가입이 접수되었습니다. 승인 대기 화면으로 이동합니다…</p>
    </form>
  </div>
</template>
