<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, apiError } from "@/services/api";
import type { Project } from "@/types";

const router = useRouter();
const route = useRoute();
const editingId = Number(route.query.edit || 0);
const error = ref("");
const saving = ref(false);
const saveOnly = ref(false);
const loaded = ref(!editingId);
const savedId = ref(editingId);
const form = reactive({
  name: "",
  slug: "",
  summary: "",
  description_markdown: "",
  repository_url: "",
  demo_url: "",
  license_name: "MIT",
  tech_stack: "",
});

onMounted(async () => {
  if (!editingId) return;
  try {
    const items = (await api.get<Project[]>("/projects/mine")).data;
    const item = items.find((project) => project.id === editingId);
    if (!item || !["draft", "rejected"].includes(item.status))
      throw new Error("投稿不可编辑");
    Object.assign(form, {
      name: item.name,
      slug: item.slug,
      summary: item.summary,
      description_markdown: item.description_markdown,
      repository_url: item.repository_url,
      demo_url: item.demo_url || "",
      license_name: item.license_name,
      tech_stack: item.tech_stack.join(", "),
    });
    loaded.value = true;
  } catch (reason) {
    error.value = apiError(reason) || "投稿不可编辑";
  }
});

async function submit() {
  if (saving.value || !loaded.value) return;
  saving.value = true;
  error.value = "";
  try {
    const payload = {
      ...form,
      demo_url: form.demo_url || null,
      tech_stack: form.tech_stack
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };
    const project = savedId.value
      ? (await api.put(`/projects/${savedId.value}`, payload)).data
      : (await api.post("/projects", payload)).data;
    savedId.value = project.id;
    if (!saveOnly.value) await api.post(`/projects/${project.id}/submit`);
    await router.push("/projects/mine");
  } catch (reason) {
    error.value = apiError(reason);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="page narrow">
    <div class="eyebrow">Submission</div>
    <h1>{{ editingId ? "修改并重新提交" : "提交开源项目" }}</h1>
    <p class="lede">
      提交后进入人工审核。仓库必须公开，并清楚说明许可证、用途和运行方法。
    </p>
    <form class="form-grid form-panel" @submit.prevent="submit">
      <p v-if="!loaded && !error" role="status">正在加载投稿内容…</p>
      <fieldset :disabled="!loaded || saving" class="submission-fields">
      <label
        >项目名称<input v-model="form.name" required maxlength="160"
      /></label>
      <label
        >英文标识<input
          v-model="form.slug"
          required
          pattern="[a-z0-9]+(-[a-z0-9]+)*"
          placeholder="my-open-project"
      /></label>
      <label
        >一句话摘要<textarea v-model="form.summary" required maxlength="500" />
      </label>
      <label
        >详细说明 Markdown<textarea
          v-model="form.description_markdown"
          required
        />
      </label>
      <label
        >公开仓库地址<input v-model="form.repository_url" required type="url"
      /></label>
      <label>演示地址 可选<input v-model="form.demo_url" type="url" /></label>
      <div class="split">
        <label>许可证<input v-model="form.license_name" required /></label
        ><label>技术栈 逗号分隔<input v-model="form.tech_stack" /></label>
      </div>
      <div class="form-actions">
        <button type="submit" :disabled="saving || !loaded" @click="saveOnly = true">保存草稿</button>
        <button type="submit" :disabled="saving || !loaded" @click="saveOnly = false">
          {{ saving ? "提交中…" : "保存并提交审核" }}</button
        ><span class="error">{{ error }}</span>
      </div>
      </fieldset>
    </form>
  </div>
</template>
<style scoped>
.submission-fields { display: grid; gap: 18px; margin: 0; padding: 0; border: 0; min-width: 0; }
</style>
