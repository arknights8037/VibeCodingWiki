<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import WikiTermPopover from "@/components/WikiTermPopover.vue";
import type { WikiTerm } from "@/services/wikiTerms";
import { api, apiError } from "@/services/api";
import type { WikiArticle } from "@/types";

const route = useRoute();
const article = ref<WikiArticle | null>(null);
const error = ref("");
const loading = ref(true);
const terms = ref<WikiTerm[]>([]);
const selectedSlug = ref('');
const selectedTerm = computed(() => terms.value.find(term => term.slug === selectedSlug.value));
let trigger: HTMLElement | undefined;
function selectTerm(term: WikiTerm, element: HTMLElement) { trigger = element; selectedSlug.value = term.slug; }
function closeTerm() { selectedSlug.value = ''; if (trigger?.isConnected) trigger.focus(); }
async function load() {
  loading.value = true; error.value = "";
  try {
    const [articleResponse, termsResponse] = await Promise.allSettled([
      api.get<WikiArticle>(`/wiki/${route.params.slug}`),
      api.get<WikiTerm[]>('/wiki/terms'),
    ]);
    if (articleResponse.status === 'rejected') throw articleResponse.reason;
    article.value = articleResponse.value.data;
    if (termsResponse.status === 'fulfilled') terms.value = termsResponse.value.data;
  } catch (reason) {
    error.value = apiError(reason);
  } finally { loading.value = false; }
}
onMounted(load);
onBeforeUnmount(closeTerm);
</script>

<template>
  <div class="page narrow">
    <p v-if="loading" role="status">正在加载正文…</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button text @click="load">重新加载</el-button><RouterLink to="/wiki">返回知识库</RouterLink></el-alert>
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
      <MarkdownBody :source="article.body_markdown || ''" :title-to-omit="article.title" :content-json="article.content_json" :terms="terms" @term-select="selectTerm" />
      <WikiTermPopover v-if="selectedTerm" :term="selectedTerm" @close="closeTerm" />
    </template>
  </div>
</template>
