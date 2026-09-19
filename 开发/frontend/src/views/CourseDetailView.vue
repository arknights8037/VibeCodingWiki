<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import MarkdownBody from "@/components/MarkdownBody.vue";
import { api, apiError } from "@/services/api";
import type { Course } from "@/types";

const route = useRoute();
const course = ref<Course | null>(null);
const error = ref("");
const loading = ref(true);

async function load() {
  loading.value = true; error.value = "";
  try {
    course.value = (
      await api.get<Course>(`/courses/${route.params.slug}`)
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
    <template v-if="course">
      <header class="article-head">
        <div class="eyebrow">
          MODULE {{ String(course.order_index).padStart(2, "0") }}
        </div>
        <h1>{{ course.title }}</h1>
        <p class="lede">{{ course.summary }}</p>
      </header>
      <section v-for="lesson in course.lessons" :key="lesson.id" :id="`lesson-${lesson.slug}`">
        <MarkdownBody :source="lesson.body_markdown" />
      </section>
    </template>
  </div>
</template>
