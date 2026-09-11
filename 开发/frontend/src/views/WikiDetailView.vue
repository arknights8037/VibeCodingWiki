<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import { api, apiError } from "@/services/api";
import type { WikiArticle } from "@/types";

const route = useRoute();
const article = ref<WikiArticle | null>(null);
const error = ref("");
onMounted(async () => {
  try {
    article.value = (
      await api.get<WikiArticle>(`/wiki/${route.params.slug}`)
    ).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
});
</script>

<template>
  <div class="page narrow">
    <p v-if="error" class="error">{{ error }}</p>
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
