<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { Project } from "@/types";

const auth = useAuthStore();
const projects = ref<Project[]>([]);
const error = ref("");
onMounted(async () => {
  try {
    projects.value = (await api.get<Project[]>("/projects")).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
});
</script>

<template>
  <div class="page">
    <div class="section-heading">
      <div>
        <div class="eyebrow">Open Source</div>
        <h1>自由开源项目</h1>
      </div>
      <RouterLink :to="auth.signedIn ? '/projects/submit' : '/auth'"
        >提交项目</RouterLink
      >
    </div>
    <p class="lede">
      这里只展示通过人工审核的公开仓库。详情、许可证和技术栈由提交者提供。
    </p>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="project-grid" style="margin-top: 34px">
      <a
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        :href="project.repository_url"
        target="_blank"
        rel="noreferrer"
      >
        <span v-if="project.is_featured" class="tag featured">推荐</span
        ><span class="tag">{{ project.license_name }}</span>
        <h3>{{ project.name }}</h3>
        <p>{{ project.summary }}</p>
        <div class="tag-row">
          <span v-for="tech in project.tech_stack" :key="tech" class="tag">{{
            tech
          }}</span>
        </div>
      </a>
    </div>
  </div>
</template>
