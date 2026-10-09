<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Document, Link, Share, VideoPlay } from "@element-plus/icons-vue";
import { api, apiError } from "@/services/api";
import MarkdownBody from "@/components/MarkdownBody.vue";
import type { Project } from "@/types";

const projects = ref<Project[]>([]);
const route = useRoute();
const router = useRouter();
const error = ref("");
const loading = ref(true);
const query = ref(String(route.query.q || ""));
const featuredOnly = ref(route.query.featured === '1');
const copied = ref("");
const lifecycle = new AbortController();
let copyTimer: ReturnType<typeof setTimeout>;
const selectedProject = computed(() => projects.value.find(project => project.slug === route.params.slug));
const listQuery = computed(() => ({ ...(query.value ? { q: query.value } : {}), ...(featuredOnly.value ? { featured: '1' } : {}) }));
watch(() => route.query.q, value => { query.value = String(value || ""); });
watch(() => route.query.featured, value => { featuredOnly.value = value === '1'; });
const filteredProjects = computed(() => projects.value.filter(p => (!featuredOnly.value || p.is_featured) && `${p.name} ${p.summary} ${p.tech_stack.join(" ")}`.toLowerCase().includes(query.value.toLowerCase())));
function openProject(project: Project) { void router.push({ path: `/projects/${project.slug}`, query: listQuery.value }); }
function backToProjects() { void router.push({ path: '/projects', query: listQuery.value, hash: selectedProject.value ? `#project-${selectedProject.value.slug}` : '' }); }
async function share(project: Project) {
  const url = `${location.origin}/projects/${project.slug}`;
  try {
    if (navigator.share) await navigator.share({ title: project.name, url });
    else await navigator.clipboard.writeText(url);
    copied.value = project.slug;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => copied.value = "", 1800);
  } catch { /* Dismissing the share dialog leaves the page unchanged. */ }
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    projects.value = (await api.get<Project[]>("/projects", { signal: lifecycle.signal })).data;
  } catch (reason) {
    if (!lifecycle.signal.aborted) error.value = apiError(reason);
  } finally { loading.value = false; }
}
onMounted(load);
onBeforeUnmount(() => { lifecycle.abort(); clearTimeout(copyTimer); });
</script>

<template>
  <div class="page projects-page">
    <template v-if="route.params.slug">
      <el-button class="project-back" :icon="ArrowLeft" @click="backToProjects">返回作品列表</el-button>
      <article v-if="selectedProject" class="project-detail">
        <header class="article-head">
          <div class="tag-row"><span v-if="selectedProject.content_category" class="tag">{{ selectedProject.content_category.name }}</span><span v-if="selectedProject.is_featured" class="tag featured">推荐</span><span class="tag">{{ selectedProject.license_name }}</span></div>
          <h1>{{ selectedProject.name }}</h1>
          <p class="lede">{{ selectedProject.summary }}</p>
          <div class="tag-row"><span v-for="tech in selectedProject.tech_stack" :key="tech" class="tag">{{ tech }}</span></div>
        </header>
        <MarkdownBody :source="selectedProject.description_markdown" :title-to-omit="selectedProject.name" />
        <div class="project-actions">
          <el-button tag="a" :href="selectedProject.repository_url" target="_blank" rel="noopener noreferrer" :icon="Link">查看源代码</el-button>
          <el-button v-if="selectedProject.demo_url" tag="a" :href="selectedProject.demo_url" target="_blank" rel="noopener noreferrer" :icon="VideoPlay">打开演示</el-button>
          <el-button :icon="Share" @click="share(selectedProject)">{{ copied === selectedProject.slug ? '已复制链接' : '分享' }}</el-button>
        </div>
      </article>
      <p v-else-if="!loading && !error" role="status">该作品不存在或尚未发布。</p>
    </template>
    <template v-else>
      <div class="content-toolbar"><el-checkbox v-model="featuredOnly">只看推荐</el-checkbox></div>
      <div class="project-grid content-list">
        <article v-for="project in filteredProjects" :key="project.id" :id="`project-${project.slug}`" class="project-card">
          <div class="tag-row"><span v-if="project.content_category" class="tag">{{ project.content_category.name }}</span><span v-if="project.is_featured" class="tag featured">推荐</span><span class="tag">{{ project.license_name }}</span></div>
          <h3>{{ project.name }}</h3>
          <p class="project-summary">{{ project.summary }}</p>
          <div class="project-card-footer">
            <div class="tag-row"><span v-for="tech in project.tech_stack" :key="tech" class="tag">{{ tech }}</span></div>
            <div class="project-actions">
              <el-button :icon="Document" @click="openProject(project)">查看项目说明</el-button>
              <el-button tag="a" :href="project.repository_url" target="_blank" rel="noopener noreferrer" :icon="Link">查看源代码</el-button>
              <el-button v-if="project.demo_url" tag="a" :href="project.demo_url" target="_blank" rel="noopener noreferrer" :icon="VideoPlay">打开演示</el-button>
              <el-button :icon="Share" @click="share(project)">{{ copied === project.slug ? '已复制链接' : '分享' }}</el-button>
            </div>
          </div>
        </article>
      </div>
      <p v-if="!loading && !error && !filteredProjects.length" role="status">没有匹配的作品，试试其他关键词。</p>
    </template>
    <p v-if="loading" role="status">正在加载作品…</p>
    <p v-if="error" class="error" role="alert">{{ error }} <el-button text @click="load">重新加载</el-button></p>
  </div>
</template>

<style scoped>
.projects-page .project-grid { gap: 10px; background: transparent; border: 0; }
.projects-page .project-card { display: flex; flex-direction: column; min-height: 0; padding: 14px 16px; }
.projects-page .project-card h3 { margin: 8px 0 4px; overflow-wrap: anywhere; }
.project-summary { margin: 0 0 10px; line-height: 1.65; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
.project-card-footer { display: flex; align-items: flex-end; flex-wrap: wrap; gap: 8px 12px; margin-top: auto; }
.project-card-footer > .tag-row { flex: 1 1 160px; }
.project-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; margin-left: auto; }
.project-actions .el-button { margin: 0; padding: 5px 8px; min-height: 28px; height: auto; font-size: 11px; }
.project-back { margin-bottom: 20px; }
.project-detail .article-head h1 { margin-top: 12px; }
.project-detail > .project-actions { margin-top: 24px; }
@media (max-width: 760px) {
  .project-card-footer > .tag-row { flex-basis: 100%; }
  .project-card-footer .project-actions { width: 100%; }
}
</style>
