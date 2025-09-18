import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

import LoginView from "@/views/LoginView.vue";
import Dashboard from "@/views/Dashboard.vue";
import StudentsView from "@/views/StudentsView.vue";
import AttendanceView from "@/views/AttendanceView.vue";
import CounselView from "@/views/CounselView.vue";
import GradesView from "@/views/GradesView.vue";
import SignupView from "@/views/SignupView.vue";
import ChangePasswordView from "@/views/ChangePasswordView.vue";
import AdminUsersView from "@/views/AdminUsersView.vue";
import PendingApprovalView from "@/views/PendingApprovalView.vue";

const routes = [
  { path: "/login", name: "login", component: LoginView, meta: { public: true } },
  { path: "/signup", name: "signup", component: SignupView, meta: { public: true } },
  { path: "/pending-approval", name: "pending-approval", component: PendingApprovalView, meta: { public: true } },

  { path: "/change-password", name: "change-password", component: ChangePasswordView },

  { path: "/", name: "dashboard", component: Dashboard },

  { path: "/students", name: "students", component: StudentsView, meta: { roles: ["teacher","admin"] } },
  { path: "/attendance", name: "attendance", component: AttendanceView, meta: { roles: ["teacher","admin"] } },
  { path: "/counsel", name: "counsel", component: CounselView, meta: { roles: ["teacher","admin"] } },
  { path: "/grades", name: "grades", component: GradesView, meta: { roles: ["teacher","admin"] } },

  // 관리자 전용
  { path: "/admin/users", name: "admin-users", component: AdminUsersView, meta: { roles: ["admin"] } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 글로벌 가드
router.beforeEach((to, from, next) => {
  const auth = useAuthStore();

  // 공개 라우트는 그대로 통과
  if (to.meta.public) return next();

  // 로그인 필요
  if (!auth.isLoggedIn) return next({ name: "login", query: { redirect: to.fullPath } });

  // 비밀번호 변경 강제: /change-password 이외 페이지 접근 시 차단
  if (auth.passwordChangeRequired && to.name !== "change-password") {
    return next({ name: "change-password" });
  }

  // 역할 체크
  const roles = to.meta.roles;
  if (!roles) return next();
  if (roles.includes(auth.role)) return next();

  return next({ name: "dashboard" });
});

export default router;
