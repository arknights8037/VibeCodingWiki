<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import type { Course } from "@/types";

const courses = ref<Course[]>([]);
const loading = ref(true);
const error = ref("");
onMounted(async () => {
  try {
    courses.value = (await api.get<Course[]>("/courses")).data;
  } catch (reason) {
    error.value = apiError(reason);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="page">
    <div class="eyebrow">Learning Path</div>
    <h1>Vibe Coding 标准课程</h1>
    <p class="lede">
      按顺序完成九个模块。每个模块包含概念正文、实践任务和可以检查的完成标准。
    </p>
    <p class="status-line" :class="{ error }">
      {{ loading ? "正在加载课程…" : error }}
    </p>
    <div class="course-grid">
      <RouterLink
        v-for="course in courses"
        :key="course.id"
        class="course-card"
        :to="`/courses/${course.slug}`"
      >
        <span class="course-number"
          >MODULE {{ String(course.order_index).padStart(2, "0") }}</span
        >
        <h3>{{ course.title }}</h3>
        <p>{{ course.summary }}</p>
        <span class="tag">{{ course.difficulty }}</span>
      </RouterLink>
    </div>
  </div>
</template>
