<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, EditPen, FolderOpened, ArrowUp, ArrowDown, Delete, Back, DocumentChecked, FolderAdd } from '@element-plus/icons-vue';
import AdminListTable from './AdminListTable.vue';
import ContentEditorLayout from './ContentEditorLayout.vue';
import MarkdownEditor from './MarkdownEditor.vue';
import { api, apiError } from '@/services/api';
import { confirmRemoval } from '@/services/removal';
import type { WikiArticle, WikiCategory } from '@/types';
type Article = WikiArticle & { status: string; order_index?: number };
type Row = { key: string; title: string; category?: WikiCategory; article?: Article; children?: Row[] };
const articles = ref<Article[]>([]);
const categories = ref<WikiCategory[]>([]);
const mode = ref<'list' | 'article' | 'category'>('list');
const busy = ref(false);
const error = ref('');
const id = ref<number>();
const baseline = ref('');
const form = reactive({ title:'', slug:'', summary:'', body_markdown:'', content_json:'', category_id:null as number | null, category:'AI Coding', tags:'', difficulty:'beginner', status:'draft', order_index:0 });
const categoryForm = reactive({ name:'', slug:'', parent_id:null as number | null, order_index:0 });
const snapshot = () => JSON.stringify(mode.value === 'article' ? form : categoryForm);
const dirty = computed(() => mode.value !== 'list' && snapshot() !== baseline.value);
function flatten(items: WikiCategory[], depth = 0): Array<WikiCategory & { depth: number }> { return items.flatMap(item => [{ ...item, depth }, ...flatten(item.children || [], depth + 1)]); }
const flat = computed(() => flatten(categories.value));
function tree(items: WikiCategory[]): Row[] { return items.map(category => ({ key:`category-${category.id}`, title:category.name, category, children:[...tree(category.children || []), ...articles.value.filter(a => a.category.id === category.id).map(article => ({ key:`article-${article.id}`, title:article.title, article }))] })); }
const rows = computed(() => tree(categories.value));
async function canLeave() {
  if (busy.value) return false;
  if (!dirty.value) return true;
  try { await ElMessageBox.confirm('当前修改尚未保存，是否放弃修改？', '离开知识库编辑', { confirmButtonText:'放弃修改', cancelButtonText:'继续编辑' }); return true; } catch { return false; }
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => to.query.section !== from.query.section ? canLeave() : true);
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value) { event.preventDefault(); event.returnValue = ''; } }
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); void refresh(); });
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
async function load() { const [a,c] = await Promise.all([api.get<Article[]>('/admin/wiki'), api.get<WikiCategory[]>('/admin/wiki/categories')]); articles.value = a.data; categories.value = c.data; }
async function run(action: () => Promise<void>) { if (busy.value) return; busy.value = true; error.value = ''; try { await action(); } catch (reason) { error.value = apiError(reason); } finally { busy.value = false; } }
async function refresh() { if (!await canLeave()) return; await run(async () => { await load(); mode.value = 'list'; }); }
defineExpose({ refresh, canLeave });
async function back() { if (await canLeave()) mode.value = 'list'; }
async function editArticle(article?: Article, categoryId?: number) {
  if (!await canLeave()) return;
  id.value = article?.id; mode.value = 'article'; error.value = '';
  Object.assign(form, { title:article?.title || '', slug:article?.slug || '', summary:article?.summary || '', body_markdown:article?.body_markdown || '', content_json:article?.content_json || '', category_id:article?.category.id ?? categoryId ?? null, category:article?.category.name || 'AI Coding', tags:article?.tags.map(t => t.name).join(', ') || '', difficulty:article?.difficulty || 'beginner', status:article?.status || 'draft', order_index:article?.order_index || 0 });
  baseline.value = snapshot();
}
async function editCategory(category?: WikiCategory) {
  if (!await canLeave()) return;
  id.value = category?.id; mode.value = 'category'; error.value = '';
  Object.assign(categoryForm, { name:category?.name || '', slug:category?.slug || '', parent_id:category?.parent_id ?? null, order_index:category?.order_index || 0 }); baseline.value = snapshot();
}
const invalidParents = computed(() => { const item = flat.value.find(c => c.id === id.value); return new Set(item ? flatten([item]).map(c => c.id) : []); });
async function save() {
  if (mode.value === 'article' && !form.category_id) { error.value = '请选择分类'; return; }
  await run(async () => {
    const resource = mode.value === 'article' ? '/admin/wiki' : '/admin/wiki/categories';
    const payload = mode.value === 'article' ? { ...form, category:flat.value.find(c => c.id === form.category_id)?.name || form.category, tags:form.tags.split(',').map(t => t.trim()).filter(Boolean) } : { ...categoryForm };
    const response = id.value ? await api.put(resource + '/' + id.value, payload) : await api.post(resource, payload);
    id.value = response.data.id; baseline.value = snapshot(); await load(); ElMessage.success(mode.value === 'article' ? '词条已保存' : '分类已保存');
  });
}
function siblings(row: Row) { return row.article ? articles.value.filter(a => a.category.id === row.article!.category.id) : flat.value.filter(c => c.parent_id === row.category!.parent_id); }
function canMove(row: Row, offset: number) { const items = siblings(row); const index = items.findIndex(i => i.id === (row.article || row.category)!.id); return index + offset >= 0 && index + offset < items.length; }
async function move(row: Row, offset: number) { if (!canMove(row, offset)) return; await run(async () => { await api.post(`/admin/wiki/${row.article ? row.article.id : 'categories/' + row.category!.id}/move`, { offset }); await load(); }); }
async function remove(row: Row) {
  const descendants = row.category ? countCategoryContents(row.category) : { categories:0, articles:0 };
  const impact = row.article ? '词条将从知识库和搜索结果中移除。' : `将同时删除 ${descendants.categories} 个子分类和 ${descendants.articles} 篇词条。分类、词条与搜索索引都会被移除。`;
  if (!await confirmRemoval(row.title, impact)) return;
  await run(async () => { await api.delete(`/admin/wiki/${row.article ? row.article.id : 'categories/' + row.category!.id}`); await load(); mode.value = 'list'; ElMessage.success('已移除'); });
}
function countCategoryContents(category: WikiCategory): { categories: number; articles: number } {
  const children = category.children || [];
  return children.reduce<{ categories: number; articles: number }>((total, child) => { const nested: { categories: number; articles: number } = countCategoryContents(child); return { categories: total.categories + 1 + nested.categories, articles: total.articles + (child.article_count || 0) + nested.articles }; }, { categories:0, articles:category.article_count || 0 });
}
</script>
<template>
  <div class="wiki-editor" v-loading="busy">
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <template v-if="mode === 'list'">
      <div class="list-toolbar"><span>知识库目录 · {{ articles.length }} 篇词条</span><div><el-button :icon="FolderAdd" @click="editCategory()">新增分类</el-button><el-button :icon="Plus" @click="editArticle()">新建词条</el-button></div></div>
      <AdminListTable :data="rows" row-key="key" default-expand-all empty-text="暂无分类，请先新增分类">
        <el-table-column label="分类与词条" min-width="240"><template #default="{ row }"><button class="title-button" @click="row.article ? editArticle(row.article) : editCategory(row.category)">{{ row.title }}</button></template></el-table-column>
        <el-table-column label="类型" width="80"><template #default="{ row }">{{ row.article ? '词条' : '分类' }}</template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag v-if="row.article" size="small" :type="row.article.status === 'published' ? 'success' : 'info'">{{ row.article.status === 'published' ? '已发布' : '草稿' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" min-width="440"><template #default="{ row }"><div class="admin-row-actions"><el-button :icon="row.article ? EditPen : FolderOpened" @click="row.article ? editArticle(row.article) : editCategory(row.category)">{{ row.article ? '编辑内容' : '管理分类' }}</el-button><el-button v-if="row.category" :icon="Plus" @click="editArticle(undefined, row.category.id)">新增词条</el-button><el-button :icon="ArrowUp" :disabled="!canMove(row, -1)" @click="move(row, -1)">上移</el-button><el-button :icon="ArrowDown" :disabled="!canMove(row, 1)" @click="move(row, 1)">下移</el-button><el-button :icon="Delete" type="danger" plain @click="remove(row)">移除</el-button></div></template></el-table-column>
      </AdminListTable>
    </template>
    <ContentEditorLayout v-else-if="mode === 'article'">
      <MarkdownEditor :key="id || 'new'" v-model="form.body_markdown" v-model:content-json="form.content_json" :disabled="busy" label="词条正文编辑器" height="calc(100dvh - 112px)" />
      <template #actions><el-button :icon="Back" :disabled="busy" @click="back">返回列表</el-button><el-button :icon="DocumentChecked" type="primary" :loading="busy" @click="save">保存词条</el-button><span role="status">{{ dirty ? '有未保存的修改' : '暂无未保存修改' }}</span></template>
      <template #properties><el-form label-position="top" :disabled="busy" @submit.prevent="save">
        <el-form-item label="标题"><el-input v-model="form.title" aria-label="标题" maxlength="180" /></el-form-item>
        <el-form-item label="英文标识"><el-input v-model="form.slug" aria-label="英文标识" placeholder="例如 ai-coding" /></el-form-item>
        <el-form-item label="摘要"><el-input v-model="form.summary" aria-label="摘要" type="textarea" :autosize="{ minRows:2, maxRows:5 }" maxlength="500" /></el-form-item>
        <el-form-item label="分类"><el-select v-model="form.category_id" aria-label="分类"><el-option v-for="c in flat" :key="c.id" :value="c.id" :label="'　'.repeat(c.depth) + c.name" /></el-select></el-form-item>
        <el-form-item label="词条状态"><el-select v-model="form.status" aria-label="词条状态"><el-option value="draft" label="草稿" /><el-option value="published" label="已发布" /></el-select></el-form-item>
        <el-form-item label="难度"><el-select v-model="form.difficulty" aria-label="难度"><el-option value="beginner" label="基础" /><el-option value="intermediate" label="进阶" /><el-option value="advanced" label="专业" /></el-select></el-form-item>
        <el-form-item label="标签"><el-input v-model="form.tags" aria-label="标签" placeholder="用英文逗号分隔" /></el-form-item>
        <el-button v-if="id" :icon="Delete" type="danger" plain @click="remove({ key:'', title:form.title, article:articles.find(a => a.id === id)! })">移除词条</el-button>
      </el-form></template>
    </ContentEditorLayout>
    <el-form v-else class="category-form" label-position="top" :disabled="busy" @submit.prevent="save">
      <el-button :icon="Back" @click="back">返回列表</el-button>
      <el-form-item label="分类名称"><el-input v-model="categoryForm.name" aria-label="分类名称" /></el-form-item>
      <el-form-item label="分类英文标识"><el-input v-model="categoryForm.slug" aria-label="分类英文标识" /></el-form-item>
      <el-form-item label="父级分类"><el-select v-model="categoryForm.parent_id" aria-label="父级分类"><el-option :value="null" label="顶级分类" /><el-option v-for="c in flat" :key="c.id" :value="c.id" :label="'　'.repeat(c.depth) + c.name" :disabled="invalidParents.has(c.id)" /></el-select></el-form-item>
      <el-button :icon="DocumentChecked" native-type="submit" type="primary" :loading="busy">保存分类</el-button>
    </el-form>
  </div>
</template>
<style scoped>
.list-toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
.title-button { border:0; background:none; color:inherit; cursor:pointer; text-align:left; padding:0; }
.title-button:hover { color:var(--el-color-primary); }
.category-form { max-width:620px; }
.category-form > .el-button:first-child { margin-bottom:20px; }
.el-alert { margin-bottom:16px; }
</style>
