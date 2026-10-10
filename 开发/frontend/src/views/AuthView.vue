<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const route = useRoute();
const mode = computed(() => route.path === "/register" ? "register" : "login");
const form = reactive({ display_name: "", email: "", password: "", confirm_password: "" });
const error = ref("");
const busy = ref(false);

async function submit() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  if (mode.value === "register" && form.password !== form.confirm_password) { error.value = "两次输入的密码不一致"; busy.value = false; return; }
  try {
    if (mode.value === "register")
      await auth.register(form.display_name, form.email, form.password);
    else await auth.login(form.email, form.password);
    const returnTo = route.query.returnTo;
    await router.replace(
      typeof returnTo === "string" && returnTo.startsWith("/") &&
      !returnTo.startsWith("//") && !returnTo.includes("\\") && !/^\/(auth|login|register)([/?#]|$)/.test(returnTo)
        ? returnTo : "/",
    );
  } catch (reason) {
    error.value = apiError(reason);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="auth-screen">
    <header class="auth-header"><RouterLink class="auth-brand" to="/"><span>W</span>VibeCoding Wiki</RouterLink><RouterLink to="/">返回知识库 ↗</RouterLink></header>
    <main class="auth-main">
      <section class="auth-card">
        <div class="auth-symbol" aria-hidden="true">{{ mode === 'login' ? '↗' : '+' }}</div>
        <p class="auth-eyebrow">你的学习空间</p>
        <h1>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h1>
        <p class="auth-description">{{ mode === 'login' ? '登录后，继续你的学习与创作。' : '保存学习进度，分享作品，记录每一次进步。' }}</p>
        <nav class="auth-switch" aria-label="账号页面"><RouterLink :to="{ path:'/login', query: route.query }">登录</RouterLink><RouterLink :to="{ path:'/register', query: route.query }">注册</RouterLink></nav>
        <form class="auth-form" @submit.prevent="submit">
          <fieldset :disabled="busy">
            <label v-if="mode === 'register'" for="auth-name">显示名称<input id="auth-name" v-model="form.display_name" required minlength="2" maxlength="80" autocomplete="nickname" placeholder="你希望大家怎么称呼你" /></label>
            <label for="auth-email">邮箱<input id="auth-email" v-model="form.email" type="email" required autocomplete="email" placeholder="you@example.com" /></label>
            <label for="auth-password">密码<input id="auth-password" v-model="form.password" type="password" required minlength="8" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" placeholder="至少 8 个字符" /></label>
            <label v-if="mode === 'register'" for="auth-confirm-password">确认密码<input id="auth-confirm-password" v-model="form.confirm_password" type="password" required minlength="8" autocomplete="new-password" placeholder="再次输入密码" /></label>
            <p v-if="error" class="auth-error" role="alert">{{ error }}</p>
            <el-button type="primary" native-type="submit" :loading="busy" class="auth-submit">{{ mode === 'login' ? '登录' : '注册并登录' }}</el-button>
          </fieldset>
        </form>
        <p class="auth-alternate">{{ mode === 'login' ? '还没有账号？' : '已经有账号？' }}<RouterLink :to="{path:mode === 'login' ? '/register' : '/login', query:route.query}">{{ mode === 'login' ? '立即注册' : '前往登录' }}</RouterLink></p>
        <div class="auth-note">阅读课程和知识库无需账号。<RouterLink to="/">先去看看 →</RouterLink></div>
      </section>
    </main>
    <footer class="auth-footer">VibeCoding Wiki · 按自己的节奏学习</footer>
  </div>
</template>
<style scoped>
.auth-screen { min-height:100vh; display:flex; flex-direction:column; background:#fafaf8; color:#37352f; --el-color-primary:#496a81; }
.auth-header { display:flex; justify-content:space-between; align-items:center; padding:25px 38px; font-size:12px; color:#898477; }
.auth-brand { display:flex; align-items:center; gap:10px; font-size:14px; font-weight:600; color:#37352f; }
.auth-brand span { background:#fff; border:1px solid #dddcd5; border-radius:5px; padding:0 5px; font: bold 27px Georgia,serif; }
.auth-main { display:grid; place-items:center; padding:35px 20px 60px; }
.auth-card { width:min(100%,420px); }
.auth-symbol { width:44px; height:44px; display:grid; place-items:center; background:#eeeFE9; border-radius:9px; font-size:24px; color:#7a8470; margin-bottom:25px; }
.auth-eyebrow { font-size:11px; color:#969083; margin:0 0 8px; }
.auth-card h1 { font-size:29px; margin:0 0 13px; letter-spacing:-.5px; }
.auth-description { color:#939083; font-size:13px; margin:0 0 28px; }
.auth-switch { display:grid; grid-template-columns:1fr 1fr; background:#efeee9; border-radius:6px; padding:4px; margin-bottom:26px; text-align:center; font-size:13px; }
.auth-switch a { padding:7px; color:#8b8577; border-radius:4px; }
.auth-switch a.router-link-active { background:white; color:#38362d; box-shadow:0 1px 3px #0000000d; }
.auth-form fieldset { border:0; padding:0; margin:0; min-width:0; display:grid; gap:20px; }
.auth-form label { display:grid; gap:8px; color:#6a6558; font-size:12px; }
.auth-form input { width:100%; border:1px solid #dedbd2; padding:11px 13px; background:white; border-radius:5px; font-size:14px; color:#37352f; }
.auth-form input:focus { outline:2px solid #c4d3db; outline-offset:1px; }
.auth-form input::placeholder { color:#b1aa9d; font-size:12px; }
.auth-submit { width:100%; height:41px; margin-top:3px; }
.auth-error { color:#b42318; font-size:12px; margin:0; }
.auth-alternate { text-align:center; font-size:12px; color:#9a9487; margin:23px 0; }
.auth-alternate a { color:#4b7086; padding-left:7px; }
.auth-note { font-size:11px; color:#aaa293; border-top:1px solid #eae6dd; padding-top:22px; display:flex; justify-content:space-between; gap:10px; }
.auth-footer { text-align:center; padding:20px; font-size:11px; color:#aca596; }
@media(max-width:500px) { .auth-header { padding:20px; } .auth-main { padding-top:25px; } .auth-card h1 { font-size:27px; } }
</style>
