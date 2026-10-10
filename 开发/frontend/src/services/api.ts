import axios, { type InternalAxiosRequestConfig } from "axios";

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

// Share one refresh request when several protected requests expire together.
let refreshRequest: Promise<unknown> | null = null;
api.interceptors.response.use(response => response, async (error: unknown) => {
  if (!axios.isAxiosError(error)) return Promise.reject(error);
  const config = error.config as (InternalAxiosRequestConfig & { retried?: boolean }) | undefined;
  const canRefresh = config && error.response?.status === 401 && !config.retried &&
    cookie("csrf_token") && !/\/auth\/(login|register|refresh|logout)$/.test(config.url || "");
  if (!canRefresh) return Promise.reject(error);
  config.retried = true;
  try {
    refreshRequest ??= api.post("/auth/refresh").finally(() => { refreshRequest = null; });
    await refreshRequest;
    return await api.request(config);
  } catch (refreshError) {
    return Promise.reject(refreshError);
  }
});

export function apiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.slice(1).join(".") || "输入"}: ${item.msg}`).join("；");
    return "请求失败，请稍后重试";
  }
  if (error instanceof Error) return error.message;
  return "发生未知错误";
}
