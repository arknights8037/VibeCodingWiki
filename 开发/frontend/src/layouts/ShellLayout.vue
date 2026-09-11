<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink class="brand" to="/" aria-label="VibeCodingWiki 首页">
        <span class="brand-mark">VC</span><span>VibeCodingWiki</span>
      </RouterLink>
      <nav class="main-nav" aria-label="主要导航">
        <RouterLink to="/courses">课程</RouterLink>
        <RouterLink to="/wiki">Wiki</RouterLink>
        <RouterLink to="/projects">项目</RouterLink>
        <RouterLink to="/skills">Skills</RouterLink>
        <RouterLink v-if="auth.canReview" to="/admin">管理</RouterLink>
      </nav>
      <div class="account-actions">
        <template v-if="auth.user">
          <RouterLink to="/projects/mine">{{
            auth.user.display_name
          }}</RouterLink>
          <button class="text-button" type="button" @click="auth.logout">
            退出
          </button>
        </template>
        <RouterLink v-else class="login-link" to="/auth">登录</RouterLink>
      </div>
    </header>
    <main><RouterView /></main>
    <footer class="site-footer">
      <span>VibeCodingWiki</span>
      <span>课程 · Wiki · 开源项目 · MCP · Agent Skills</span>
    </footer>
  </div>
</template>
