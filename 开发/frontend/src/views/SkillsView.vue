<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { CopyDocument, Delete, Download, Edit, Upload } from "@element-plus/icons-vue";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import MarkdownEditor from "@/components/MarkdownEditor.vue";
import type { Skill } from "@/types";
type ManagedSkill = Skill & { id: number; status: string; review_note?: string | null };
const auth = useAuthStore();
const route = useRoute();
const skills = ref<Skill[]>([]);
const mine = ref<ManagedSkill[]>([]);
const tab = ref(route.query.tab === 'mine' && auth.signedIn ? 'mine' : 'public');
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const categories = ref<{ id: number; name: string }[]>([]);
const editOpen = ref(false);
const contentOpen = ref(false);
const editing = ref<ManagedSkill>();
const editError = ref('');
const editForm = reactive({ summary: '', tags: '', content_category_id: 0 });
const contentForm = reactive({ body_markdown: '' });
const query = ref(String(route.query.q || ""));
watch(() => route.query.q, value => { query.value = String(value || ""); });
const filteredSkills = computed(() => (tab.value === "mine" ? mine.value : skills.value).filter(s =>
  `${s.name} ${s.summary} ${s.compatibility || ""} ${s.content_category?.name || ''} ${(s.tags || []).join(' ')}`.toLowerCase().includes(query.value.trim().toLowerCase())));
function installUrl(skill: Skill) { return `${location.origin}/skills/${skill.slug}/${skill.version}/download.zip`; }
function skillLocation(skill: Skill) { return { path: `/skills/${skill.slug}/${skill.version}`, query: { ...(query.value ? { q: query.value } : {}), ...(tab.value === 'mine' ? { tab: 'mine' } : {}) } }; }
async function copyUrl(skill: Skill) {
  try { await navigator.clipboard.writeText(installUrl(skill)); ElMessage.success("已复制公开安装 URL"); }
  catch { ElMessage.error("复制失败，请进入详情页手动复制安装地址"); }
}
async function load() {
  loading.value = true; error.value = "";
  try {
    const [published, owned, categoryResponse] = await Promise.all([api.get<Skill[]>("/skills"), auth.signedIn ? api.get<ManagedSkill[]>("/skills/mine") : Promise.resolve({ data: [] }), api.get<{id: number; name: string}[]>('/content-categories?kind=skill').catch(() => ({ data: [] }))]);
    skills.value = published.data; mine.value = owned.data;
    categories.value = categoryResponse.data;
  } catch (reason) { error.value = apiError(reason); }
  finally { loading.value = false; }
}
async function manage(skill: Skill, action: "intro" | "status" | "delete") {
  const item = skill as ManagedSkill;
  if (busy.value) return;
  busy.value = true;
  try {
    if (action === "intro") {
      editing.value = item;
      Object.assign(editForm, { summary: item.summary, tags: (item.tags || []).join(', '), content_category_id: item.content_category_id || 0 });
      editError.value = '';
      editOpen.value = true;
      return;
    } else if (action === "status") {
      await api.patch(`/skills/${item.id}/status`, { status: ["published", "pending_review"].includes(item.status) ? "draft" : (auth.isAdmin ? "published" : "pending_review") });
    } else {
      await ElMessageBox.confirm(`删除 ${item.name} / ${item.version} 后，此版本的安装 URL 将失效。`, "删除 Skill", { type: "warning", confirmButtonText: "删除", cancelButtonText: "取消" });
      await api.delete(`/skills/${item.id}`);
    }
    await load();
  } catch (reason) { if (reason !== "cancel" && reason !== "close") ElMessage.error(apiError(reason)); }
  finally { busy.value = false; }
}
async function saveMetadata() {
  if (!editing.value || busy.value) return;
  if (!editForm.summary.trim()) { editError.value = '请填写简要说明'; return; }
  busy.value = true; editError.value = '';
  try {
    await api.patch(`/skills/${editing.value.id}/intro`, { summary: editForm.summary, tags: editForm.tags.split(/[,，]/).map(value => value.trim()).filter(Boolean), ...(editForm.content_category_id ? { content_category_id: editForm.content_category_id } : {}) });
    editOpen.value = false;
    await load();
  } catch (reason) { editError.value = apiError(reason); }
  finally { busy.value = false; }
}
async function openContentEditor(skill: Skill) {
  const item = skill as ManagedSkill;
  if (busy.value) return;
  busy.value = true; editError.value = '';
  try {
    const source = (await api.get<string>(`/skills/${item.id}/content`, { responseType: 'text' })).data;
    Object.assign(contentForm, { body_markdown: source.replace(/^\uFEFF?---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, '').trim() });
    editing.value = item; contentOpen.value = true;
  } catch (reason) { ElMessage.error(apiError(reason)); }
  finally { busy.value = false; }
}
async function saveContent() {
  if (!editing.value || busy.value) return;
  if (!contentForm.body_markdown.trim()) { editError.value = '请填写说明内容'; return; }
  busy.value = true; editError.value = '';
  try {
    await api.patch(`/skills/${editing.value.id}/content`, { body_markdown: contentForm.body_markdown });
    contentOpen.value = false;
    ElMessage.success(auth.isAdmin ? '说明内容已更新' : '说明内容已保存，已进入审核流程');
    await load();
  } catch (reason) { editError.value = apiError(reason); }
  finally { busy.value = false; }
}
onMounted(load);
</script>
<template>
  <div class="page">
    <el-tabs v-if="auth.signedIn" v-model="tab"><el-tab-pane label="公开 Skills" name="public" /><el-tab-pane :label="`我的 Skills (${mine.length})`" name="mine" /></el-tabs>
    <p v-if="error" class="error" role="alert">{{ error }} <el-button text @click="load">重试</el-button></p>
    <div v-loading="loading" class="skill-list content-list">
      <el-empty v-if="!loading && !error && !filteredSkills.length" :description="tab === 'mine' ? '还没有 Skill，上传文件或在线创建一个吧' : '没有匹配的 Skill'" />
      <article v-for="skill in filteredSkills" :key="`${skill.slug}-${skill.version}`" :id="`skill-${skill.slug}-${skill.version}`" class="skill-card">
        <div class="tag-row skill-labels" aria-label="分类和标签">
          <span class="tag skill-category">{{ skill.content_category?.name || '未分类' }}</span>
          <span v-for="tag in skill.tags || []" :key="tag" class="tag skill-tag">#{{ tag }}</span>
        </div>
        <h2><RouterLink class="skill-card-link" :to="skillLocation(skill)">{{ skill.name }}</RouterLink></h2>
        <p class="skill-summary">{{ skill.summary }}</p>
        <div class="skill-actions">
          <template v-if="tab === 'public' || (skill as ManagedSkill).status === 'published'">
            <el-button tag="a" :href="installUrl(skill)" :icon="Download">下载 ZIP</el-button>
            <el-button :icon="CopyDocument" @click="copyUrl(skill)">复制安装 URL</el-button>
          </template>
          <template v-if="tab === 'mine'">
            <el-button :icon="Edit" :disabled="busy" @click="manage(skill, 'intro')">编辑简介</el-button>
            <el-button :icon="Edit" :disabled="busy" @click="openContentEditor(skill)">编辑说明</el-button>
            <el-button :icon="Upload" :disabled="busy" @click="manage(skill, 'status')">{{ (skill as ManagedSkill).status === 'published' ? '撤下' : (skill as ManagedSkill).status === 'pending_review' ? '撤回审核' : auth.isAdmin ? '发布' : '提交审核' }}</el-button>
            <el-button :icon="Delete" type="danger" plain :disabled="busy" @click="manage(skill, 'delete')">删除</el-button>
          </template>
        </div>
      </article>
    </div>
    <el-dialog v-model="editOpen" title="编辑技能信息" width="min(520px, calc(100vw - 32px))" :close-on-click-modal="!busy">
      <el-form label-position="top" @submit.prevent="saveMetadata">
        <el-form-item label="简要说明"><el-input v-model="editForm.summary" type="textarea" :rows="3" maxlength="2000" /></el-form-item>
        <el-form-item label="分类"><el-select v-model="editForm.content_category_id" aria-label="技能分类" placeholder="请选择分类"><el-option v-for="category in categories" :key="category.id" :value="category.id" :label="category.name" /></el-select></el-form-item>
        <el-form-item label="标签"><el-input v-model="editForm.tags" aria-label="技能标签" placeholder="用逗号分隔，最多 12 个" /></el-form-item>
        <p class="result-meta">修改已发布技能的信息后，需重新审核。</p>
        <p v-if="editError" class="error" role="alert">{{ editError }}</p>
      </el-form>
      <template #footer><el-button :disabled="busy" @click="editOpen = false">取消</el-button><el-button type="primary" :loading="busy" @click="saveMetadata">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="contentOpen" title="编辑 Skill 说明正文" width="min(1000px, calc(100vw - 32px))" class="skill-content-dialog" destroy-on-close :close-on-click-modal="!busy">
      <MarkdownEditor v-if="contentOpen" v-model="contentForm.body_markdown" label="Skill 说明编辑器" height="min(62vh, 620px)" />
      <p v-if="editError" class="error" role="alert">{{ editError }}</p>
      <template #footer><el-button :disabled="busy" @click="contentOpen = false">取消</el-button><el-button type="primary" :loading="busy" @click="saveContent">保存正文</el-button></template>
    </el-dialog>
  </div>
</template>
<style scoped>
.page .skill-list { grid-template-columns: minmax(0, 1fr); gap: 10px; background: transparent; border: 0; }
.page .skill-card { position: relative; display: flex; flex-direction: column; min-height: 0; padding: 14px 16px; }
.page .skill-card h2 { margin: 0 0 6px; font-size: 16px; line-height: 1.6; overflow-wrap: anywhere; }
.skill-card-link::after { content: ''; position: absolute; inset: 0; border-radius: 6px; }
.skill-card:has(.skill-card-link:focus-visible) { outline: 2px solid var(--ui-control-focus); outline-offset: 3px; }
.skill-card:hover { border-color: var(--ui-control-focus); }
.skill-summary { margin: 0 0 12px; line-height: 1.65; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; }
.skill-labels { margin-bottom: 8px; }
.skill-category { font-weight: 600; }
.page .skill-tag { color: var(--ui-control-focus); font-size: 12px; overflow-wrap: anywhere; }
.skill-actions { position: relative; z-index: 1; align-self: flex-end; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; margin-top: auto; }
.skill-actions .el-button { margin: 0; height: auto; min-height: 28px; padding: 5px 8px; font-size: 11px; }
</style>
