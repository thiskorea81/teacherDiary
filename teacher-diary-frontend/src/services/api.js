// src/services/api.js
import axios from "axios";

// .env.development 에서 VITE_API_BASE_URL=http://127.0.0.1:8000
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  withCredentials: false, // JWT는 헤더로 전송. (쿠키 사용 아님)
});

// 요청 인터셉터: 로컬스토리지의 토큰을 항상 Authorization에 실어 보냄
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// (선택) 응답 인터셉터: 401이면 토큰 삭제 후 로그인으로 유도
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      // 토큰 만료/유효하지 않음
      localStorage.removeItem("token");
      localStorage.removeItem("me");
      localStorage.removeItem("pwdreq");
      // 페이지에 따라 자동 이동을 원치 않으면 이 부분은 주석 처리
      // window.location.href = "/login?session=expired";
    }
    return Promise.reject(err);
  }
);

export default api;
