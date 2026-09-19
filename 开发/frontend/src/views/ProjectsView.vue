<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import ContentDisclosure from "@/components/ContentDisclosure.vue";
import MarkdownBody from "@/components/MarkdownBody.vue";
import type { Project } from "@/types";

const projects = ref<Project[]>([]);
const error = ref("");
const query = ref(""); const featuredOnly = ref(false); const copied = ref("");
const filteredProjects = computed(() => projects.value.filter(p => (!featuredOnly.value || p.is_featured) && `${p.name} ${p.summary} ${p.tech_stack.join(" ")}`.toLowerCase().includes(query.value.toLowerCase())));
async function share(project: Project) { const url = `${location.origin}/projects#project-${project.slug}`; try { if (navigator.share) await navigator.share({ title: project.name, url }); else await navigator.clipboard.writeText(url); copied.value = project.slug; setTimeout(() => copied.value = "", 1800); } catch {} }
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
      <RouterLink to="/projects/submit"
        >提交项目</RouterLink
      >
    </div>
    <p class="lede">
      这里只展示通过人工审核的公开仓库。详情、许可证和技术栈由提交者提供。
    </p>
    <div class="content-toolbar"><el-input v-model="query" clearable placeholder="搜索项目、技术栈…" /><el-checkbox v-model="featuredOnly">只看推荐</el-checkbox></div>
    <RouterLink class="new-submission-button" to="/projects/submit"><span>＋</span> 新建投稿</RouterLink>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="project-grid content-list">
      <article
        v-for="project in filteredProjects"
        :key="project.id"
        :id="`project-${project.slug}`"
        class="project-card"
      >
        <span v-if="project.is_featured" class="tag featured">推荐</span
        ><span class="tag">{{ project.license_name }}</span>
        <h3>{{ project.name }}</h3>
        <p>{{ project.summary }}</p>
        <ContentDisclosure title="查看项目说明"><MarkdownBody :source="project.description_markdown" /></ContentDisclosure>
        <div class="form-actions">
          <a :href="project.repository_url" target="_blank" rel="noreferrer">查看源代码</a>
          <a v-if="project.demo_url" :href="project.demo_url" target="_blank" rel="noreferrer">打开演示</a>
          <span v-else class="result-meta">暂未提供演示地址</span>
          <el-button text @click="share(project)">{{ copied === project.slug ? '已复制链接' : '分享' }}</el-button>
        </div>
        <div class="tag-row">
          <span v-for="tech in project.tech_stack" :key="tech" class="tag">{{
            tech
          }}</span>
        </div>
      </article>
    </div>
  </div>
</template>
