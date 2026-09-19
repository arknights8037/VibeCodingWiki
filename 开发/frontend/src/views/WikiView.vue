<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, apiError } from "@/services/api";
import type { WikiArticle } from "@/types";

const route = useRoute();
const router = useRouter();
const filters = reactive({
  q: String(route.query.q || ""),
  phrase: "",
  category: "",
  tags: "",
  difficulty: "",
  updated_after: "",
  sort: "relevance",
  page: 1,
});
const categories = ref<{ slug: string; name: string }[]>([]);
const articles = ref<WikiArticle[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const pageSize = 10;
const lifecycle = new AbortController();
let searchVersion = 0;

async function search() {
  const version = ++searchVersion;
  loading.value = true;
  error.value = "";
  try {
    const response = await api.get<{ items: WikiArticle[]; total: number }>(
      "/wiki",
      {
        signal: lifecycle.signal,
        params: {
          q: filters.q || undefined,
          phrase: filters.phrase || undefined,
          category: filters.category || undefined,
          tags: filters.tags
            ? filters.tags
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean)
            : undefined,
          difficulty: filters.difficulty || undefined,
          updated_after: filters.updated_after
            ? `${filters.updated_after}T00:00:00Z`
            : undefined,
          sort: filters.sort,
          page: filters.page,
          page_size: pageSize,
        },
      },
    );
    if (version !== searchVersion || lifecycle.signal.aborted) return;
    await router.replace({ query: filters.q ? { q: filters.q } : {} });
    if (version !== searchVersion || lifecycle.signal.aborted) return;
    articles.value = response.data.items;
    total.value = response.data.total;
  } catch (reason) {
    if (version === searchVersion && !lifecycle.signal.aborted) error.value = apiError(reason);
  } finally {
    if (version === searchVersion) loading.value = false;
  }
}

watch(() => route.query.q, (value) => {
  if (String(value || '') !== filters.q) { filters.q = String(value || ''); filters.page = 1; void search(); }
});

function changePage(delta: number) {
  filters.page += delta;
  void search();
}

onMounted(async () => {
  const initialSearch = search();
  try { categories.value = (await api.get<{ slug: string; name: string }[]>("/wiki/categories")).data; }
  catch { /* Search remains available when category options cannot load. */ }
  await initialSearch;
  if (lifecycle.signal.aborted) return;
  const context = document.modelContext;
  if (context?.registerTool) {
    await Promise.resolve(
      context.registerTool(
        {
          name: "search_vibecodingwiki",
          title: "查询 VibeCodingWiki",
          description:
            "搜索当前站点中已发布的 Vibe Coding 技术词条，并同步更新页面结果。",
          inputSchema: {
            type: "object",
            properties: {
              query: { type: "string", minLength: 1, maxLength: 100 },
            },
            required: ["query"],
            additionalProperties: false,
          },
          annotations: { readOnlyHint: true, untrustedContentHint: false },
          async execute(input) {
            const query = (input as { query?: unknown }).query;
            if (typeof query !== "string" || !query.trim())
              throw new Error("query 必须是非空字符串");
            filters.q = query.trim();
            filters.page = 1;
            await search();
            return {
              total: total.value,
              results: articles.value.map(({ slug, title, summary }) => ({
                slug,
                title,
                summary,
              })),
            };
          },
        },
        { signal: lifecycle.signal },
      ),
    );
  }
});
onBeforeUnmount(() => lifecycle.abort());
</script>

<template>
  <div class="page">
    <div class="eyebrow">知识库</div>
    <h1>查问题、找解释</h1>
    <p class="lede">搜索已发布词条，并按分类、标签、难度和更新时间缩小结果。</p>
    <form
      class="filter-bar"
      @submit.prevent="
        filters.page = 1;
        search();
      "
    >
      <input v-model="filters.q" aria-label="关键词" placeholder="关键词" />
      <input
        v-model="filters.phrase"
        aria-label="精确短语"
        placeholder="精确短语"
      />
      <select v-model="filters.category" aria-label="分类">
        <option value="">全部分类</option>
        <option v-for="item in categories" :key="item.slug" :value="item.slug">
          {{ item.name }}
        </option>
      </select>
      <select v-model="filters.difficulty" aria-label="难度">
        <option value="">全部难度</option>
        <option value="beginner">入门</option>
        <option value="intermediate">进阶</option>
        <option value="advanced">高级</option>
      </select>
      <select v-model="filters.sort" aria-label="排序">
        <option value="relevance">相关度</option>
        <option value="updated_desc">最近更新</option>
        <option value="title_asc">标题</option>
      </select>
      <button type="submit">查询</button>
      <input
        v-model="filters.tags"
        aria-label="标签"
        placeholder="标签，以逗号分隔"
      />
      <label class="compact-label"
        >更新晚于<input v-model="filters.updated_after" type="date"
      /></label>
    </form>
    <p class="status-line" :class="{ error }">
      {{ loading ? "正在查询…" : error || `找到 ${total} 个词条` }}
    </p>
    <div v-if="!loading" class="result-list">
      <RouterLink
        v-for="article in articles"
        :key="article.id"
        class="result-item"
        :to="`/wiki/${article.slug}`"
      >
        <div class="result-meta">{{ article.category.name }}</div>
        <div>
          <h2>{{ article.title }}</h2>
          <p>{{ article.summary }}</p>
          <div class="tag-row">
            <span v-for="tag in article.tags" :key="tag.slug" class="tag">{{
              tag.name
            }}</span>
          </div>
        </div>
        <div class="result-meta">{{ article.difficulty }}</div>
      </RouterLink>
    </div>
    <div class="pagination">
      <button :disabled="filters.page <= 1" @click="changePage(-1)">
        上一页</button
      ><span>第 {{ filters.page }} 页</span
      ><button
        :disabled="filters.page * pageSize >= total"
        @click="changePage(1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>
