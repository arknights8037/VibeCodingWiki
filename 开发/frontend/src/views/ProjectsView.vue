<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, apiError } from "@/services/api";
import ContentDisclosure from "@/components/ContentDisclosure.vue";
import MarkdownBody from "@/components/MarkdownBody.vue";
import type { Project } from "@/types";

const projects = ref<Project[]>([]);
const route = useRoute();
const error = ref("");
const query = ref(String(route.query.q || "")); const featuredOnly = ref(false); const copied = ref("");
watch(() => route.query.q, value => { query.value = String(value || ""); void load(); });
const filteredProjects = computed(() => projects.value.filter(p => (!featuredOnly.value || p.is_featured) && `${p.name} ${p.summary} ${p.tech_stack.join(" ")}`.toLowerCase().includes(query.value.toLowerCase())));
async function share(project: Project) { const url = `${location.origin}/projects#project-${project.slug}`; try { if (navigator.share) await navigator.share({ title: project.name, url }); else await navigator.clipboard.writeText(url); copied.value = project.slug; setTimeout(() => copied.value = "", 1800); } catch {} }
async function load() {
  try {
    projects.value = (await api.get<Project[]>("/projects", { params: { q: query.value || undefined } })).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
}
onMounted(load);
</script>

<template>
  <div class="page">
    <div class="content-toolbar"><el-checkbox v-model="featuredOnly">只看推荐</el-checkbox></div>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="project-grid content-list">
      <article
        v-for="project in filteredProjects"
        :key="project.id"
        :id="`project-${project.slug}`"
        class="project-card"
      >
        <span v-if="project.content_category" class="tag">{{ project.content_category.name }}</span><span v-if="project.is_featured" class="tag featured">推荐</span
        ><span class="tag">{{ project.license_name }}</span>
        <h3>{{ project.name }}</h3>
        <p>{{ project.summary }}</p>
        <ContentDisclosure title="查看项目说明"><MarkdownBody :source="project.description_markdown" /></ContentDisclosure>
        <div class="form-actions">
          <a :href="project.repository_url" target="_blank" rel="noreferrer">查看源代码</a>
          <a v-if="project.demo_url" :href="project.demo_url" target="_blank" rel="noreferrer">打开演示</a>
          <span v-else class="result-meta">暂未提供演示地址</span>
          <el-button class="share-button" @click="share(project)">{{ copied === project.slug ? '已复制链接' : '分享' }}</el-button>
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
