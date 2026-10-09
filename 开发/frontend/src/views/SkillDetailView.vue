<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ArrowLeft, CopyDocument, Document, Download } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { api, apiError } from '@/services/api';
import { useAuthStore } from '@/stores/auth';
import MarkdownBody from '@/components/MarkdownBody.vue';
import type { Skill } from '@/types';

type ManagedSkill = Skill & { id: number; status: string; review_note?: string | null };
const route = useRoute();
const auth = useAuthStore();
const skill = ref<Skill | ManagedSkill>();
const source = ref('');
const loading = ref(true);
const error = ref('');
const lifecycle = new AbortController();
const isMine = computed(() => route.query.tab === 'mine');
const published = computed(() => skill.value && (!('status' in skill.value) || skill.value.status === 'published'));
const managed = computed(() => skill.value && 'status' in skill.value ? skill.value : undefined);
const statusNames: Record<string, string> = { draft: '草稿', pending_review: '待审核', published: '已发布', rejected: '已驳回', archived: '已归档' };
const resourcePath = computed(() => `/skills/${route.params.slug}/${route.params.version}`);
const installUrl = computed(() => `${location.origin}${resourcePath.value}/download.zip`);
const backLocation = computed(() => ({ path: '/skills', query: { ...(route.query.q ? { q: String(route.query.q) } : {}), ...(isMine.value ? { tab: 'mine' } : {}) }, hash: `#skill-${route.params.slug}-${route.params.version}` }));
// Front matter is package metadata; the rendered article starts with its instructions.
const body = computed(() => source.value.replace(/^\uFEFF?---\r?\n[\s\S]*?\r?\n---(?:\r?\n|$)/, ''));
async function copyUrl() {
  try { await navigator.clipboard.writeText(installUrl.value); ElMessage.success('已复制公开安装 URL'); }
  catch { ElMessage.error('复制失败，请手动复制安装地址'); }
}
async function load() {
  loading.value = true; error.value = ''; source.value = ''; skill.value = undefined;
  try {
    const catalog = (await api.get<(Skill | ManagedSkill)[]>(isMine.value ? '/skills/mine' : '/skills', { signal: lifecycle.signal })).data;
    skill.value = catalog.find(item => item.slug === route.params.slug && item.version === route.params.version);
    if (!skill.value) throw new Error('该技能不存在或尚未发布。');
    if (isMine.value && managed.value) {
      source.value = (await api.get<string>(`/skills/${managed.value.id}/content`, { responseType: 'text', signal: lifecycle.signal })).data;
    } else {
      const response = await fetch(`${resourcePath.value}/SKILL.md`, { signal: lifecycle.signal });
      if (!response.ok) throw new Error('技能正文加载失败，请重试。');
      source.value = await response.text();
    }
  } catch (reason) { if (!lifecycle.signal.aborted) error.value = apiError(reason); }
  finally { loading.value = false; }
}
onMounted(() => {
  if (isMine.value && !auth.signedIn) { loading.value = false; error.value = '请先登录后查看自己的技能。'; }
  else void load();
});
onBeforeUnmount(() => lifecycle.abort());
</script>

<template>
  <div class="page skill-detail">
    <RouterLink :to="backLocation" custom v-slot="{ href, navigate }"><el-button class="skill-back" tag="a" :href="href" :icon="ArrowLeft" @click="navigate">返回技能列表</el-button></RouterLink>
    <p v-if="loading" role="status">正在加载技能…</p>
    <p v-if="error" class="error" role="alert">{{ error }} <el-button text @click="load">重试</el-button></p>
    <template v-if="skill">
      <header class="article-head">
        <h1>{{ skill.name }}</h1>
        <p class="lede">{{ skill.summary }}</p>
        <div class="tag-row"><span class="tag">v{{ skill.version }}</span><span v-if="skill.content_category" class="tag">{{ skill.content_category.name }}</span><span v-if="skill.license_name" class="tag">{{ skill.license_name }}</span><span v-if="managed" class="tag">{{ statusNames[managed.status] || managed.status }}</span></div>
        <div v-if="skill.tags?.length" class="tag-row skill-tags"><span v-for="tag in skill.tags" :key="tag" class="tag">{{ tag }}</span></div>
        <p v-if="managed?.review_note" class="error">审核意见：{{ managed.review_note }}</p>
        <p v-if="skill.compatibility" class="result-meta">兼容性：{{ skill.compatibility }}</p>
      </header>
      <MarkdownBody v-if="source" :source="body" :title-to-omit="skill.name" />
      <template v-if="published">
        <div class="skill-actions"><el-button tag="a" :href="installUrl" :icon="Download">下载 ZIP</el-button><el-button :icon="CopyDocument" @click="copyUrl">复制安装 URL</el-button><el-button tag="a" :href="`${resourcePath}/SKILL.md`" target="_blank" rel="noopener noreferrer" :icon="Document">查看 SKILL.md</el-button></div>
        <p class="install-url"><a :href="installUrl">{{ installUrl }}</a></p>
        <details class="checksum"><summary>SHA-256 校验值</summary><code>{{ skill.sha256 }}</code></details>
      </template>
    </template>
  </div>
</template>

<style scoped>
.skill-back { margin-bottom: 20px; }
.skill-tags { margin-top: 8px; }
.skill-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; margin-top: 24px; }
.skill-actions .el-button { margin: 0; min-height: 28px; height: auto; padding: 5px 8px; font-size: 11px; }
.install-url, .checksum code { overflow-wrap: anywhere; font-size: 12px; }
.checksum { margin: 16px 0; font-size: 12px; }
</style>
