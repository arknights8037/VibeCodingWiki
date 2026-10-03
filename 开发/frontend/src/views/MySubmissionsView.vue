<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import type { Project } from "@/types";

const projects = ref<Project[]>([]);
const error = ref("");
onMounted(async () => {
  try {
    projects.value = (await api.get<Project[]>("/projects/mine")).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
});
</script>

<template>
  <div class="page">
    <p v-if="error" class="error">{{ error }}</p>
    <table class="data-table">
      <thead>
        <tr>
          <th>项目</th>
          <th>状态</th>
          <th>审核说明</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in projects" :key="item.id">
          <td>{{ item.name }}</td>
          <td>{{ item.status }}</td>
          <td>{{ item.review_note || "—" }}</td>
          <td>
            <a :href="item.repository_url" target="_blank" rel="noreferrer"
              >仓库</a
            ><span v-if="['draft', 'rejected'].includes(item.status)">
              ·
              <RouterLink :to="`/projects/submit?edit=${item.id}`"
                >编辑重投</RouterLink
              ></span
            >
          </td>
        </tr>
        <tr v-if="!projects.length">
          <td colspan="4">尚无投稿</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
