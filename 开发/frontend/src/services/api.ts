import axios from "axios";

export const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  paramsSerializer: { indexes: null },
});

function cookie(name: string): string | undefined {
  return document.cookie
    .split("; ")
    .find((item) => item.startsWith(`${name}=`))
    ?.split("=")
    .slice(1)
    .join("=");
}

api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();
  if (method && !["GET", "HEAD", "OPTIONS"].includes(method)) {
    const token = cookie("csrf_token");
    if (token) config.headers.set("X-CSRF-Token", decodeURIComponent(token));
  }
  return config;
});

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error))
    return error.response?.data?.detail || "请求失败，请稍后重试";
  return "发生未知错误";
}
