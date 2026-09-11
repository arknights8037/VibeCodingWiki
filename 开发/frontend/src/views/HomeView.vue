<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/services/api";
import type { Course, WikiArticle } from "@/types";

const router = useRouter();
const query = ref("");
const courses = ref<Course[]>([]);
const recent = ref<WikiArticle[]>([]);

onMounted(async () => {
  const [courseResponse, wikiResponse] = await Promise.all([
    api.get<Course[]>("/courses"),
    api.get<{ items: WikiArticle[] }>("/wiki", {
      params: { sort: "updated", page_size: 4 },
    }),
  ]);
  courses.value = courseResponse.data;
  recent.value = wikiResponse.data.items;
});

function launchSearch() {
  router.push({ path: "/wiki", query: { q: query.value } });
}
</script>

<template>
  <section class="home-intro">
    <div class="home-grid">
      <div>
        <div class="eyebrow">从零开始的工程化 AI 编程知识库</div>
        <h1>先理解，再生成。<br />每一步都有验证。</h1>
        <p class="lede">
          课程给出学习顺序，Wiki 负责随查随用，开源项目展示可运行的实践，MCP 与
          Agent Skills 让知识进入你的开发工具。
        </p>
        <form class="search-launch" @submit.prevent="launchSearch">
          <input
            v-model="query"
            aria-label="搜索 Wiki"
            placeholder="搜索 Git、FastAPI、MCP 或安全实践"
          />
          <button type="submit">查询 Wiki</button>
        </form>
      </div>
      <div class="module-index">
        <strong>09</strong><span>个连续模块，从需求到开放标准</span>
      </div>
    </div>
  </section>
  <div class="page">
    <div class="section-heading">
      <h2>标准课程路径</h2>
      <RouterLink to="/courses">查看完整路径</RouterLink>
    </div>
    <div class="course-grid">
      <RouterLink
        v-for="course in courses.slice(0, 6)"
        :key="course.id"
        class="course-card"
        :to="`/courses/${course.slug}`"
      >
        <span class="course-number"
          >MODULE {{ String(course.order_index).padStart(2, "0") }}</span
        >
        <h3>{{ course.title }}</h3>
        <p>{{ course.summary }}</p>
      </RouterLink>
    </div>
    <div class="section-heading">
      <h2>最近更新</h2>
      <RouterLink to="/wiki">进入高级查询</RouterLink>
    </div>
    <div class="result-list">
      <RouterLink
        v-for="article in recent"
        :key="article.id"
        class="result-item"
        :to="`/wiki/${article.slug}`"
      >
        <div class="result-meta">{{ article.category.name }}</div>
        <div>
          <h2>{{ article.title }}</h2>
          <p>{{ article.summary }}</p>
        </div>
        <div class="result-meta">{{ article.difficulty }}</div>
      </RouterLink>
    </div>
  </div>
</template>
