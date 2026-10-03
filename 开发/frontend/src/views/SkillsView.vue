<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import SkillPublisher from "@/components/SkillPublisher.vue";
import type { Skill } from "@/types";
type ManagedSkill = Skill & { id: number; status: string; review_note?: string | null };
const statusNames: Record<string, string> = { draft: "草稿", pending_review: "待审核", published: "已发布", rejected: "已驳回", archived: "已归档" };
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const skills = ref<Skill[]>([]);
const mine = ref<ManagedSkill[]>([]);
const tab = ref("public");
const showPublisher = ref(false);
watch(() => route.query.create, value => { showPublisher.value = value === "1" && auth.signedIn; }, { immediate: true });
const loading = ref(false);
const busy = ref(false);
const error = ref("");
const query = ref(String(route.query.q || ""));
watch(() => route.query.q, value => { query.value = String(value || ""); });
const filteredSkills = computed(() => (tab.value === "mine" ? mine.value : skills.value).filter(s =>
  `${s.name} ${s.summary} ${s.compatibility || ""}`.toLowerCase().includes(query.value.trim().toLowerCase())));
function installUrl(skill: Skill) { return `${location.origin}/skills/${skill.slug}/${skill.version}/download.zip`; }
async function copyUrl(skill: Skill) {
  try { await navigator.clipboard.writeText(installUrl(skill)); ElMessage.success("已复制公开安装 URL"); }
  catch { ElMessage.error("复制失败，请手动复制下方安装地址"); }
}
async function load() {
  loading.value = true; error.value = "";
  try {
    const [published, owned] = await Promise.all([api.get<Skill[]>("/skills"), auth.signedIn ? api.get<ManagedSkill[]>("/skills/mine") : Promise.resolve({ data: [] })]);
    skills.value = published.data; mine.value = owned.data;
  } catch (reason) { error.value = apiError(reason); }
  finally { loading.value = false; }
}
async function closePublisher() { showPublisher.value = false; await router.replace({ path: "/skills" }); }
async function saved() { await closePublisher(); tab.value = "mine"; await load(); }
async function manage(skill: Skill, action: "intro" | "status" | "delete") {
  const item = skill as ManagedSkill;
  if (busy.value) return;
  busy.value = true;
  try {
    if (action === "intro") {
      const answer = await ElMessageBox.prompt("用一两句话介绍用途。非管理员修改已发布说明后，需重新审核，期间暂停公开下载。", "编辑简要说明", {
        inputType: "textarea", inputValue: item.summary,
        confirmButtonText: "保存", cancelButtonText: "取消",
        inputValidator: (value: string) => !!value?.trim() && value.length <= 2000 || "请填写 1–2000 字的说明",
      });
      await api.patch(`/skills/${item.id}/intro`, { summary: answer.value });
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
onMounted(load);
</script>
<template>
  <div class="page">
    <section v-if="showPublisher && auth.signedIn" class="form-panel publisher-panel"><el-button text @click="closePublisher">收起编辑器</el-button><SkillPublisher @saved="saved" /></section>
    <el-tabs v-model="tab"><el-tab-pane label="公开 Skills" name="public" /><el-tab-pane v-if="auth.signedIn" :label="`我的 Skills (${mine.length})`" name="mine" /></el-tabs>
    <div class="content-toolbar"><span class="result-meta">{{ filteredSkills.length }} 个结果</span></div>
    <p v-if="error" class="error" role="alert">{{ error }} <el-button text @click="load">重试</el-button></p>
    <div v-loading="loading" class="skill-list content-list">
      <el-empty v-if="!loading && !error && !filteredSkills.length" :description="tab === 'mine' ? '还没有 Skill，上传文件或在线创建一个吧' : '没有匹配的 Skill'" />
      <article v-for="skill in filteredSkills" :key="`${skill.slug}-${skill.version}`" :id="`skill-${skill.slug}-${skill.version}`" class="skill-card">
        <div class="tag-row"><span v-if="skill.content_category" class="tag">{{ skill.content_category.name }}</span><span class="tag">v{{ skill.version }}</span><span class="tag">{{ skill.license_name || "未声明许可证" }}</span><span v-if="tab === 'mine'" class="tag">{{ statusNames[(skill as ManagedSkill).status] || (skill as ManagedSkill).status }}</span></div>
        <h2>{{ skill.name }}</h2><p>{{ skill.summary }}</p>
        <p v-if="tab === 'mine' && (skill as ManagedSkill).review_note" class="error">审核意见：{{ (skill as ManagedSkill).review_note }}</p>
        <p v-if="skill.compatibility"><strong>兼容性：</strong>{{ skill.compatibility }}</p>
        <template v-if="tab === 'public' || (skill as ManagedSkill).status === 'published'">
          <p class="install-url"><a :href="installUrl(skill)">{{ installUrl(skill) }}</a></p>
          <div class="form-actions"><a class="primary-button skill-action-button" :href="installUrl(skill)">下载 ZIP</a><el-button class="skill-action-button" @click="copyUrl(skill)">复制安装 URL</el-button><a :href="`/skills/${skill.slug}/${skill.version}/SKILL.md`" target="_blank" rel="noopener">查看 SKILL.md</a></div>
          <details class="checksum"><summary>SHA-256 校验值</summary><code>{{ skill.sha256 }}</code></details>
        </template>
        <p v-else class="result-meta">审核通过并发布后，才可通过公开 URL 安装。</p>
        <div v-if="tab === 'mine'" class="form-actions"><el-button :disabled="busy" @click="manage(skill, 'intro')">编辑说明</el-button><el-button :disabled="busy" @click="manage(skill, 'status')">{{ (skill as ManagedSkill).status === 'published' ? '撤下' : (skill as ManagedSkill).status === 'pending_review' ? '撤回审核' : auth.isAdmin ? '发布' : '提交审核' }}</el-button><el-button type="danger" plain :disabled="busy" @click="manage(skill, 'delete')">删除</el-button></div>
      </article>
    </div>
  </div>
</template>
<style scoped>
.publisher-panel { margin: 24px 0; }
.skill-list { grid-template-columns: minmax(0, 1fr); }
.form-actions { flex-wrap: wrap; }
.form-actions > a { white-space: nowrap; }
.skill-action-button { height: 42px; padding: 0 22px !important; display: inline-flex; align-items: center; justify-content: center; font-size: 16px !important; font-weight: 600 !important; line-height: 1; }
.install-url, .checksum code { overflow-wrap: anywhere; }
.install-url { font-size: 13px; }
.checksum { margin: 16px 0; font-size: 12px; }
</style>
