<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
const auth = useAuthStore();
const emit = defineEmits<{ saved: [] }>();
const mode = ref("upload");
const busy = ref(false);
const error = ref("");
const file = ref<File | null>(null);
const fileInput = ref<HTMLInputElement>();
const categories = ref<{ id:number; name:string }[]>([]);
const form = reactive({ name: "", description: "", instructions: "", summary: "", version: "1.0.0", publish: false, content_category_id: 0 });
const ready = computed(() => {
  const contentReady = mode.value === "upload" ? !!file.value : /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(form.name) && !!form.description.trim() && !!form.instructions.trim() && !!form.summary.trim();
  return /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,39}$/.test(form.version) && contentReady && form.content_category_id > 0;
});
function pickFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null;
  error.value = "";
  if (file.value && file.value.size > 5 * 1024 * 1024) {
    error.value = "文件不能超过 5 MB";
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
  }
}
async function save() {
  if (!ready.value || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    if (mode.value === "upload" && file.value) {
      const data = new FormData();
      data.append("archive", file.value);
      data.append("version", form.version);
      data.append("summary", form.summary);
      data.append("publish", String(form.publish)); data.append("content_category_id", String(form.content_category_id));
      await api.post("/skills/upload", data);
    } else { await api.post("/skills", form); }
    ElMessage.success(form.publish ? (auth.isAdmin ? "Skill 已发布，可通过公开 URL 安装" : "Skill 已提交审核，通过后将公开发布") : "Skill 已保存为草稿");
    Object.assign(form, { name: "", description: "", instructions: "", summary: "", version: "1.0.0", publish: false, content_category_id: 0 });
    file.value = null;
    if (fileInput.value) fileInput.value.value = "";
    emit("saved");
  } catch (reason) { error.value = apiError(reason); }
  finally { busy.value = false; }
}
onMounted(async () => { try { categories.value = (await api.get<{id:number;name:string}[]>("/content-categories?kind=skill")).data; } catch {} });
</script>
<template>
  <el-form label-position="top" class="skill-publisher" @submit.prevent="save">
    <el-tabs v-model="mode"><el-tab-pane label="上传 Skill" name="upload" /><el-tab-pane label="在线创建" name="create" /></el-tabs>
    <template v-if="mode === 'upload'">
      <el-form-item label="Skill 文件（ZIP 或 SKILL.md）"><input ref="fileInput" type="file" accept=".zip,.md" aria-label="选择 Skill 文件" :disabled="busy" @change="pickFile" /></el-form-item>
      <p class="result-meta">ZIP 内以 SKILL.md 为入口，可包含 scripts/、references/、assets/ 等目录；支持外层文件夹。最多 100 个文件，总大小 5 MB。</p>
    </template>
    <template v-else>
      <el-form-item label="名称"><el-input v-model="form.name" maxlength="64" placeholder="例如 code-review，小写字母、数字和连字符" /></el-form-item>
      <el-form-item label="用途与触发场景（写入 SKILL.md 的 description）"><el-input v-model="form.description" type="textarea" :rows="2" maxlength="1024" show-word-limit /></el-form-item>
      <el-form-item label="执行说明（Markdown）"><el-input v-model="form.instructions" type="textarea" :rows="9" maxlength="100000" placeholder="# 使用步骤&#10;&#10;描述任务步骤、输入输出和注意事项。" /></el-form-item>
    </template>
    <el-form-item :label="mode === 'upload' ? '简要说明（选填，默认使用包内 description）' : '简要说明'"><el-input v-model="form.summary" type="textarea" :rows="2" maxlength="2000" show-word-limit placeholder="用一两句话说明这个 Skill 能帮助用户做什么" /></el-form-item>
    <el-form-item label="内容分区"><el-select v-model="form.content_category_id" placeholder="请选择分区"><el-option v-for="category in categories" :key="category.id" :value="category.id" :label="category.name" /></el-select></el-form-item>
    <el-form-item label="版本"><el-input v-model="form.version" maxlength="40" placeholder="1.0.0" /></el-form-item>
    <el-checkbox v-model="form.publish">{{ auth.isAdmin ? "保存后立即公开发布，允许外部免登录下载" : "保存后提交审核，通过后允许外部免登录下载" }}</el-checkbox>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="form-actions"><el-button type="primary" native-type="submit" :disabled="!ready" :loading="busy">{{ form.publish ? (auth.isAdmin ? '保存并发布' : '提交审核') : '保存草稿' }}</el-button></div>
  </el-form>
</template>
<style scoped>
.skill-publisher { max-width: 760px; }
.skill-publisher .form-actions { margin-top: 16px; }
.skill-publisher .result-meta { margin-bottom: 20px; }
</style>
