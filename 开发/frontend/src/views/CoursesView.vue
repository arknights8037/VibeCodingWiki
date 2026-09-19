<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import { usePreferencesStore } from "@/stores/preferences";
import type { Course } from "@/types";
const prefs = usePreferencesStore();
const t = prefs.text;
const courses = ref<Course[]>([]);
const loading = ref(true);
const error = ref("");
const query = ref("");
const filtered = computed(() => courses.value.filter(c => (prefs.level === "all" || prefs.level === c.difficulty) && (c.title + c.summary).toLowerCase().includes(query.value.trim().toLowerCase())));
const level = (value: string) => ({ beginner: t('基础','Beginner'), intermediate: t('进阶','Intermediate'), advanced: t('专业','Advanced') }[value] || value);
async function load() {
  loading.value = true; error.value = "";
  try { courses.value = (await api.get<Course[]>("/courses")).data; }
  catch (reason) { error.value = apiError(reason); }
  finally { loading.value = false; }
}
onMounted(load);
</script>
<template>
  <div class="page course-directory">
    <div class="docs-page-icon" aria-hidden="true">▤</div>
    <h1>{{ t("课程列表", "Course library") }}</h1>
    <p class="lede">{{ t("从这里开始，按自己的节奏学习。点击课程即可阅读，无需登录。", "Learn at your own pace. Open any course to read, no account required.") }}</p>
    <div class="docs-callout"><span aria-hidden="true">☞</span><div>{{ t("第一次来？从第一课开始。", "New here? Start with the first course.") }}<br /><span>{{ t("也可以直接选择你现在需要的内容，边做边学。", "Or choose what you need and learn by doing.") }}</span></div></div>
    <section>
      <div class="directory-toolbar flex items-center justify-between gap-4"><h2>{{ t("课程", "Courses") }} <span>{{ filtered.length }}</span></h2><el-input v-model="query" clearable aria-label="筛选课程" :placeholder="t('查找课程…', 'Find a course…')" /></div>
      <p v-if="loading" role="status">正在加载课程…</p>
      <el-alert v-else-if="error" :title="error" type="error" :closable="false"><el-button text @click="load">重新加载</el-button></el-alert>
      <div v-else class="course-document-list">
        <RouterLink v-for="course in filtered" :key="course.id" class="course-document-row" :to="`/courses/${course.slug}`">
          <span class="document-number">{{ String(course.order_index).padStart(2, '0') }}</span>
          <div class="min-w-0"><h3>{{ course.title }}</h3><p>{{ course.summary }}</p></div>
          <span class="document-level">{{ level(course.difficulty) }}</span><span class="document-arrow" aria-hidden="true">↗</span>
        </RouterLink>
        <el-empty v-if="!filtered.length" :description="query ? t('没有匹配的课程，试试其他关键词。', 'No matching courses. Try another search.') : t('该等级暂无课程，可以切换到全部等级。', 'No courses at this level. Try all levels.')" :image-size="60" />
      </div>
    </section>
    <section class="docs-help"><h2>{{ t('学习时遇到问题？', 'Need a hand?') }}</h2><p>{{ t('先查找相关解释，再回到课程继续实践。', 'Find an explanation, then return to your course.') }}</p><RouterLink to="/wiki">{{ t('查问题、找解释 →', 'Explore the wiki →') }}</RouterLink></section>
  </div>
</template>
