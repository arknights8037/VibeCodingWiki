<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import { api, apiError } from "@/services/api";
import type { WikiArticle } from "@/types";

const route = useRoute();
const article = ref<WikiArticle | null>(null);
const error = ref("");
const loading = ref(true);
async function load() {
  loading.value = true; error.value = "";
  try {
    article.value = (
      await api.get<WikiArticle>(`/wiki/${route.params.slug}`)
    ).data;
  } catch (reason) {
    error.value = apiError(reason);
  } finally { loading.value = false; }
}
onMounted(load);
</script>

<template>
  <div class="page narrow">
    <p v-if="loading" role="status">正在加载正文…</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button text @click="load">重新加载</el-button><RouterLink to="/courses">返回课程列表</RouterLink></el-alert>
    <template v-if="article">
      <header class="article-head">
        <div class="eyebrow">{{ article.category.name }}</div>
        <h1>{{ article.title }}</h1>
        <p class="lede">{{ article.summary }}</p>
        <div class="tag-row">
          <span v-for="tag in article.tags" :key="tag.slug" class="tag">{{
            tag.name
          }}</span>
        </div>
      </header>
      <MarkdownBody :source="article.body_markdown || ''" />
    </template>
  </div>
</template>
