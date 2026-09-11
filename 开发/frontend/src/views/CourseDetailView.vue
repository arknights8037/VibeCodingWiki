<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { Course } from "@/types";

const route = useRoute();
const auth = useAuthStore();
const course = ref<Course | null>(null);
const error = ref("");
const completed = ref(false);

onMounted(async () => {
  try {
    course.value = (
      await api.get<Course>(`/courses/${route.params.slug}`)
    ).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
});

async function markComplete() {
  const lesson = course.value?.lessons[0];
  if (!lesson) return;
  try {
    await api.post(`/courses/lessons/${lesson.slug}/complete`);
    completed.value = true;
  } catch (reason) {
    error.value = apiError(reason);
  }
}
</script>

<template>
  <div class="page narrow">
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="course">
      <header class="article-head">
        <div class="eyebrow">
          MODULE {{ String(course.order_index).padStart(2, "0") }}
        </div>
        <h1>{{ course.title }}</h1>
        <p class="lede">{{ course.summary }}</p>
      </header>
      <template v-for="lesson in course.lessons" :key="lesson.id">
        <p>
          <strong>学习目标：</strong>{{ lesson.objective }}　预计
          {{ lesson.estimated_minutes }} 分钟
        </p>
        <MarkdownBody :source="lesson.body_markdown" />
        <section class="practice-block">
          <h2>实践任务</h2>
          <p>{{ lesson.practice }}</p>
          <h3>完成标准</h3>
          <p>{{ lesson.completion_criteria }}</p>
        </section>
      </template>
      <button
        v-if="auth.signedIn && !completed"
        class="primary-button"
        type="button"
        @click="markComplete"
      >
        标记为已完成
      </button>
      <p v-if="completed">已记录本模块进度。</p>
    </template>
  </div>
</template>
