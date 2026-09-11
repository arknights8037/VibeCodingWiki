<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, apiError } from "@/services/api";
import type { Skill } from "@/types";

const skills = ref<Skill[]>([]);
const error = ref("");
onMounted(async () => {
  try {
    skills.value = (await api.get<Skill[]>("/skills")).data;
  } catch (reason) {
    error.value = apiError(reason);
  }
});
</script>

<template>
  <div class="page">
    <div class="eyebrow">Agent Skills</div>
    <h1>标准 Skills 安装地址</h1>
    <p class="lede">
      每个下载包至少包含规范的 SKILL.md。平台提供原始文件、ZIP 和
      SHA-256，但不会执行包内脚本。
    </p>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="skill-list" style="margin-top: 34px">
      <article
        v-for="skill in skills"
        :key="`${skill.slug}-${skill.version}`"
        class="skill-card"
      >
        <div class="tag-row">
          <span class="tag">v{{ skill.version }}</span
          ><span class="tag">{{ skill.license_name || "未声明许可证" }}</span>
        </div>
        <h2>{{ skill.name }}</h2>
        <p>{{ skill.summary }}</p>
        <p><strong>兼容性：</strong>{{ skill.compatibility || "未声明" }}</p>
        <p class="result-meta">SHA-256 {{ skill.sha256.slice(0, 20) }}…</p>
        <div class="form-actions">
          <a
            class="primary-button"
            :href="`/skills/${skill.slug}/${skill.version}/download.zip`"
            >下载 ZIP</a
          ><a
            :href="`/skills/${skill.slug}/${skill.version}/SKILL.md`"
            target="_blank"
            >查看原始文件</a
          >
        </div>
      </article>
    </div>
  </div>
</template>
