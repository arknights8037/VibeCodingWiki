<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import WikiTermPopover from "@/components/WikiTermPopover.vue";
import type { WikiTerm } from "@/services/wikiTerms";
import { api, apiError } from "@/services/api";
import type { Course } from "@/types";

const route = useRoute();
const course = ref<Course | null>(null);
const error = ref("");
const loading = ref(true);
const terms = ref<WikiTerm[]>([]);
const termsError = ref(false);
const selectedSlug = ref('');
const selectedTerm = computed(() => terms.value.find(term => term.slug === selectedSlug.value));
let trigger: HTMLElement | undefined;
let requestId = 0;
let timer: ReturnType<typeof setInterval>;

function selectTerm(term: WikiTerm, element: HTMLElement) {
  trigger = element;
  selectedSlug.value = term.slug;
}
function closeTerm() {
  selectedSlug.value = '';
  if (trigger?.isConnected) trigger.focus();
}
async function load(background = false) {
  const id = ++requestId;
  if (!background) { loading.value = true; error.value = ''; }
  const [content, index] = await Promise.allSettled([
    api.get<Course>(`/courses/${route.params.slug}`),
    api.get<WikiTerm[]>('/wiki/terms'),
  ]);
  if (id !== requestId) return;
  if (content.status === 'fulfilled') {
    course.value = content.value.data;
    error.value = '';
  } else if (!background || content.reason?.response?.status === 404) {
    course.value = null;
    closeTerm();
    error.value = apiError(content.reason);
  }
  termsError.value = index.status === 'rejected';
  if (index.status === 'fulfilled') {
    terms.value = index.value.data;
    if (!selectedTerm.value) closeTerm();
  }
  loading.value = false;
}
function refreshVisible() {
  if (document.visibilityState === 'visible') void load(true);
}
watch(() => route.params.slug, () => {
  course.value = null;
  closeTerm();
  void load();
});
onMounted(() => {
  void load();
  timer = setInterval(refreshVisible, 30_000);
  window.addEventListener('focus', refreshVisible);
});
onBeforeUnmount(() => {
  requestId++;
  clearInterval(timer);
  window.removeEventListener('focus', refreshVisible);
});

</script>

<template>
  <div class="page narrow">
    <p v-if="loading" role="status">正在加载正文…</p>
    <el-alert v-if="error" :title="error" type="error" :closable="false"><el-button text @click="load()">重新加载</el-button><RouterLink to="/courses">返回课程列表</RouterLink></el-alert>
    <template v-if="course">
      <header class="article-head">
        <div class="eyebrow">
          MODULE {{ String(course.order_index).padStart(2, "0") }}
        </div>
        <h1>{{ course.title }}</h1>
        <p class="lede">{{ course.summary }}</p>
      </header>
      <p v-if="termsError" class="term-index-status" role="status">术语释义暂时无法更新，正文仍可阅读。<el-button text @click="load(true)">重试</el-button></p>
      <section v-for="lesson in course.lessons" :key="lesson.id" :id="`lesson-${lesson.slug}`">
        <MarkdownBody :source="lesson.body_markdown" :content-json="lesson.content_json" :terms="terms" @term-select="selectTerm" />
      </section>
      <WikiTermPopover v-if="selectedTerm" :term="selectedTerm" @close="closeTerm" />
    </template>
  </div>
</template>
