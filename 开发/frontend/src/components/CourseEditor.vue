<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, reactive, ref } from 'vue';
import { onBeforeRouteLeave, onBeforeRouteUpdate } from 'vue-router';
import { Refresh, Search, Plus, FolderAdd, FolderOpened, EditPen, ArrowUp, ArrowDown, Delete, Back, DocumentChecked, Upload, Download } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import MarkdownEditor from './MarkdownEditor.vue';
import AdminListTable from './AdminListTable.vue';
import ContentEditorLayout from './ContentEditorLayout.vue';
import { confirmRemoval } from '@/services/removal';
import { api, apiError } from '@/services/api';
import type { Course, Lesson } from '@/types';
type Entry = Omit<Lesson, 'id'> & { id?: number; status: string };
type Draft = Omit<Course, 'id' | 'lessons'> & { id?: number; status: string; lessons: Entry[] };
const catalog = ref<Draft[]>([]);
const draft = ref<Draft>();
const active = ref(-1);
const categoryDialog = ref(false);
const categorySaving = ref(false);
const categoryError = ref('');
const categoryForm = reactive({ title: '', slug: '', summary: '', prerequisites: '无', status: 'draft', directory_collapsible: true, order_index: 0 });
const entryQuery = ref('');
const entryStatus = ref('all');
const categoryEntries = computed(() => (draft.value?.lessons || []).map((entry, index) => ({ entry, index })).filter(({ entry }) =>
  (!entryQuery.value.trim() || `${entry.title} ${entry.slug}`.toLowerCase().includes(entryQuery.value.trim().toLowerCase())) &&
  (entryStatus.value === 'all' || entry.status === entryStatus.value)));

const level = ref('beginner');
const levels = [{ label: '基础', value: 'beginner' }, { label: '进阶', value: 'intermediate' }, { label: '专业', value: 'advanced' }];
const levelName = computed(() => levels.find(item => item.value === level.value)?.label);
const visibleCatalog = computed(() => catalog.value.filter(item => item.difficulty === level.value));
type DirectoryRow = { key: string; title: string; status: string; courseId: number; index: number; root?: boolean; children?: DirectoryRow[] };
const directoryRows = computed<DirectoryRow[]>(() => visibleCatalog.value.map(course => ({
  key: `course-${course.id}`, title: course.title, status: course.status, courseId: course.id!, index: course.is_standalone ? 0 : -1, root: true,
  children: course.is_standalone ? undefined : course.lessons.map((item, index) => ({ key: `lesson-${item.id}`, title: item.title, status: item.status, courseId: course.id!, index })),
})));
const statusName = (status: string) => ({ draft: '草稿', published: '已发布', archived: '已归档' }[status] || status);
async function changeLevel(value: string | number | boolean | undefined) {
  if (!await canLeave()) return;
  level.value = String(value); draft.value = undefined; active.value = -1; saved.value = '';
}
async function backToList() {
  if (!await canLeave()) return;
  draft.value = undefined; active.value = -1; saved.value = '';
}
async function openRow(row: DirectoryRow, add = false) {
  if (!await select(row.courseId)) return;
  active.value = row.index;
  if (add) addLesson();
}

const loading = ref(false);
const saving = ref(false);
const error = ref('');
const saved = ref('');
const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== saved.value);
const lesson = computed(() => draft.value?.lessons[active.value]);

async function canLeave() {
  if (saving.value) return false;
  if (!dirty.value) return true;
  try { await ElMessageBox.confirm('当前修改尚未保存，是否放弃修改？', '离开课程编辑', { confirmButtonText: '放弃修改', cancelButtonText: '继续编辑' }); return true; } catch { return false; }
}
onBeforeRouteLeave(canLeave);
onBeforeRouteUpdate((to, from) => to.query.section !== from.query.section ? canLeave() : true);
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value) { event.preventDefault(); event.returnValue = ''; } }
onMounted(() => { window.addEventListener('beforeunload', beforeUnload); void load(); });
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));
async function load() {
  loading.value = true; error.value = '';
  try { catalog.value = (await api.get<Draft[]>('/admin/courses')).data; }
  catch (reason) { error.value = apiError(reason); }
  finally { loading.value = false; }
}
async function refresh() {
  if (!await canLeave()) return;
  const id = draft.value?.id;
  await load();
  if (error.value) return;
  draft.value = id ? JSON.parse(JSON.stringify(catalog.value.find(item => item.id === id) || null)) : undefined;
  active.value = draft.value?.is_standalone ? 0 : -1; saved.value = JSON.stringify(draft.value);
}
defineExpose({ refresh });
async function select(id: number) {
  if (!await canLeave()) return false;
  entryQuery.value = ''; entryStatus.value = 'all';
  draft.value = JSON.parse(JSON.stringify(catalog.value.find(item => item.id === id)));
  active.value = draft.value?.is_standalone ? 0 : -1; saved.value = JSON.stringify(draft.value);
  return true;
}
async function create(standalone = false) {
  if (!await canLeave()) return;
  entryQuery.value = ''; entryStatus.value = 'all';
  draft.value = { title: '', slug: '', summary: '', prerequisites: '无', difficulty: level.value, order_index: Math.max(-1, ...visibleCatalog.value.map(item => item.order_index)) + 1, is_standalone: standalone, directory_collapsible: true, status: 'draft', lessons: [] };
  active.value = -1; saved.value = '';
  if (standalone) addLesson();
}
function openCategoryDialog() {
  categoryError.value = '';
  Object.assign(categoryForm, { title: '', slug: '', summary: '', prerequisites: '无', status: 'draft', directory_collapsible: true, order_index: Math.max(-1, ...visibleCatalog.value.map(item => item.order_index)) + 1 });
  categoryDialog.value = true;
}
async function saveCategory() {
  categoryError.value = '';
  const slug = categoryForm.slug.trim() ? normalizeSlug(categoryForm.slug) : undefined;
  if (!categoryForm.title.trim()) { categoryError.value = '请填写分类名称'; return; }
  if (slug && slugError(slug)) { categoryError.value = slugError(slug); return; }
  categorySaving.value = true;
  try {
    await api.post('/admin/courses', { ...categoryForm, title: categoryForm.title.trim(), slug, difficulty: level.value, lessons: [] });
    categoryDialog.value = false;
    await load();
    ElMessage.success('分类已创建');
  } catch (reason) { categoryError.value = apiError(reason); }
  finally { categorySaving.value = false; }
}
function addLesson() {
  draft.value!.lessons.push({ title: '', slug: '', objective: '', body_markdown: '', practice: '', completion_criteria: '', estimated_minutes: 30, order_index: draft.value!.lessons.length, status: 'draft' });
  active.value = draft.value!.lessons.length - 1;
}
function move(offset: number) {
  const items = draft.value!.lessons;
  const target = active.value + offset;
  if (target < 0 || target >= items.length) return;
  [items[active.value], items[target]] = [items[target]!, items[active.value]!];
  active.value = target;
}
function canMoveRow(row: DirectoryRow, offset: number) {
  const course = catalog.value.find(item => item.id === row.courseId);
  const index = row.root ? visibleCatalog.value.findIndex(item => item.id === row.courseId) : row.index;
  const length = row.root ? visibleCatalog.value.length : course?.lessons.length || 0;
  return !saving.value && index + offset >= 0 && index + offset < length;
}
async function moveRow(row: DirectoryRow, offset: number) {
  if (!canMoveRow(row, offset)) return;
  const course = catalog.value.find(item => item.id === row.courseId)!;
  const resource = row.root ? 'courses' : 'lessons';
  const id = row.root ? course.id : course.lessons[row.index]!.id;
  saving.value = true; error.value = '';
  try { await api.post(`/admin/${resource}/${id}/move`, { offset }); await load(); ElMessage.success('顺序已保存'); }
  catch (reason) { error.value = apiError(reason); }
  finally { saving.value = false; }
}
function moveDraftEntry(index: number, offset: number) {
  const selected = active.value;
  active.value = index; move(offset);
  if (selected === -1) active.value = -1;
}
async function removeEntry(course: Draft, index: number) {
  if (course.is_standalone) index = -1;
  if (saving.value) return;
  const item = index < 0 ? course : course.lessons[index];
  if (!item) return;
  const impact = index < 0 && !course.is_standalone ? `该分类下的 ${course.lessons.length} 个条目及其学习进度将同时移除。` : '该条目的正文和学习进度将同时移除。';
  if (!await confirmRemoval(item.title || '未命名内容', impact)) return;
  saving.value = true; error.value = '';
  try {
    if (item.id) await api.delete(`/admin/${index < 0 ? 'courses' : 'lessons'}/${item.id}`);
    if (draft.value === course || (course.id && draft.value?.id === course.id)) {
      if (index < 0) { draft.value = undefined; saved.value = ''; active.value = -1; }
      else {
        draft.value!.lessons.splice(index, 1);
        active.value = -1;
        if (item.id && saved.value) {
          const baseline = JSON.parse(saved.value) as Draft;
          baseline.lessons = baseline.lessons.filter(entry => entry.id !== item.id);
          saved.value = JSON.stringify(baseline);
        }
      }
    }
    if (item.id) await load();
    ElMessage.success('已移除');
  } catch (reason) { error.value = apiError(reason); }
  finally { saving.value = false; }
}
function removeRow(row: DirectoryRow) {
  const course = catalog.value.find(item => item.id === row.courseId);
  if (course) void removeEntry(course, row.index);
}
async function togglePublication(course: Draft, index: number) {
  if (saving.value) return;
  const entry = course.lessons[index];
  if (!entry) return;
  const status = entry.status === 'published' ? 'draft' : 'published';
  if (!entry.id) {
    entry.status = status;
    ElMessage.info('状态已修改，保存课程后生效');
    return;
  }
  saving.value = true; error.value = '';
  try {
    await api.patch(`/admin/lessons/${entry.id}/status`, { status });
    entry.status = status;
    if (course.is_standalone) course.status = status;
    if (draft.value?.id === course.id && saved.value) {
      const baseline = JSON.parse(saved.value) as Draft;
      const original = baseline.lessons.find(item => item.id === entry.id);
      if (original) original.status = status;
      if (course.is_standalone) baseline.status = status;
      saved.value = JSON.stringify(baseline);
    }
    await load();
    ElMessage.success(status === 'published' ? '条目已发布' : '条目已设为未发表');
    if (status === 'published' && !course.is_standalone && course.status !== 'published') {
      ElMessage.info('所属分类尚未发布，条目暂不在前台展示');
    }
  } catch (reason) { error.value = apiError(reason); }
  finally { saving.value = false; }
}
function toggleRowPublication(row: DirectoryRow) {
  const course = catalog.value.find(item => item.id === row.courseId);
  if (course) void togglePublication(course, row.index);
}
async function publishCategory(course: Draft) {
  if (saving.value || course.is_standalone || !course.id) return;
  if (!course.title.trim() || !course.slug || course.lessons.some(item => !item.title.trim() || !item.slug)) {
    ElMessage.warning('请先补全分类和所有条目的标题、英文标识');
    return;
  }
  const invalidIndex = course.lessons.findIndex(item => slugError(item.slug));
  if (invalidIndex >= 0) {
    ElMessage.warning(`条目“${course.lessons[invalidIndex]!.title}”：${slugError(course.lessons[invalidIndex]!.slug)}`);
    return;
  }
  if (slugError(course.slug)) {
    ElMessage.warning(`分类标识：${slugError(course.slug)}`);
    return;
  }
  try {
    await ElMessageBox.confirm(
      `将发布“${course.title}”及其 ${course.lessons.length} 个条目，发布后会立即显示在前台课程目录。`,
      '发布整个分类',
      { confirmButtonText: '发布整个分类', cancelButtonText: '暂不发布', type: 'info' },
    );
  } catch { return; }
  saving.value = true; error.value = '';
  const payload = JSON.parse(JSON.stringify(course)) as Draft;
  payload.status = 'published';
  payload.lessons.forEach((item, index) => { item.status = 'published'; item.order_index = index; });
  try {
    const response = await api.put<Draft>(`/admin/courses/${payload.id}`, payload);
    if (draft.value?.id === payload.id) {
      draft.value = response.data;
      saved.value = JSON.stringify(response.data);
    }
    await load();
    ElMessage.success('分类及其全部条目已发布');
  } catch (reason) { error.value = apiError(reason); }
  finally { saving.value = false; }
}
function toggleRowCategoryPublication(row: DirectoryRow) {
  const course = catalog.value.find(item => item.id === row.courseId);
  if (course && course.status !== 'published') void publishCategory(course);
}
function normalizeSlug(value: string) {
  return value.trim().toLowerCase().replace(/[\s_]+/g, '-');
}
function slugError(value: string) {
  if (!value) return '';
  return value.length <= 100 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(normalizeSlug(value))
    ? '' : '标识只能使用英文字母、数字和单个短横线，例如 first-project；不能含中文，最多 100 个字符。';
}
async function save(publish = false) {
  if (!draft.value || saving.value) return;
  draft.value.slug = normalizeSlug(draft.value.slug);
  draft.value.lessons.forEach(item => item.slug = normalizeSlug(item.slug));
  if (draft.value.is_standalone && draft.value.lessons[0]) {
    draft.value.title = draft.value.lessons[0].title;
    draft.value.slug = draft.value.lessons[0].slug;
    draft.value.status = draft.value.lessons[0].status;
  }
  if (!draft.value.title.trim() || !draft.value.slug || draft.value.lessons.some(item => !item.title.trim() || !item.slug)) { ElMessage.warning('请填写分类和所有条目的标题、英文标识'); return; }
  const invalidIndex = draft.value.lessons.findIndex(item => slugError(item.slug));
  if (invalidIndex >= 0) {
    active.value = invalidIndex;
    ElMessage.warning(`条目“${draft.value.lessons[invalidIndex]!.title}”：${slugError(draft.value.lessons[invalidIndex]!.slug)}`);
    return;
  }
  if (slugError(draft.value.slug)) {
    active.value = -1;
    ElMessage.warning(`分类标识：${slugError(draft.value.slug)}`);
    return;
  }
  saving.value = true; error.value = '';
  const payload = JSON.parse(JSON.stringify(draft.value)) as Draft;
  if (publish) {
    payload.status = 'published';
    payload.lessons.forEach(item => item.status = 'published');
  }
  payload.lessons.forEach((item, index) => item.order_index = index);
  try {
    const response = payload.id ? await api.put<Draft>(`/admin/courses/${payload.id}`, payload) : await api.post<Draft>('/admin/courses', payload);
    draft.value = response.data; saved.value = JSON.stringify(response.data);
    await load(); ElMessage.success(publish && !payload.is_standalone ? '分类及其全部条目已发布' : publish ? '课程已保存并发布' : '课程已保存');
  } catch (reason) { error.value = apiError(reason); }
  finally { saving.value = false; }
}
</script>
<template>
  <div class="course-editor" v-loading="loading">
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <div v-if="!draft" class="course-level-bar">
      <el-radio-group :model-value="level" aria-label="学习等级" :disabled="saving" @update:model-value="changeLevel">
        <el-radio-button v-for="item in levels" :key="item.value" :value="item.value">{{ item.label }}</el-radio-button>
      </el-radio-group>
      <div v-if="!draft"><el-button :icon="FolderAdd" :disabled="loading || saving" @click="openCategoryDialog">新增分类</el-button><el-button :icon="Plus" :disabled="loading || saving" @click="create(true)">新增无分类条目</el-button></div>
    </div>
    <template v-if="!draft">
      <AdminListTable :data="directoryRows" row-key="key" default-expand-all class="course-directory-table" empty-text="该等级暂无分类，点击新增分类开始创建">
        <el-table-column prop="title" label="分类与条目" min-width="240">
          <template #default="{ row }"><span :class="{ 'category-title': row.index === -1 }">{{ row.title }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="80"><template #default="{ row }">{{ row.index === -1 ? '分类' : '条目' }}</template></el-table-column>
        <el-table-column label="状态" width="90"><template #default="{ row }"><el-tag size="small" :type="row.status === 'published' ? 'success' : 'info'">{{ statusName(row.status) }}</el-tag></template></el-table-column>
        <el-table-column label="操作" min-width="470">
          <template #default="{ row }"><div class="directory-row-actions" :class="{ 'category-row-actions': row.index === -1 }">
            <el-button :icon="FolderOpened" v-if="row.index === -1" @click="openRow(row)">管理分类</el-button>
            <el-button :icon="Plus" class="action-add" v-if="row.index === -1" @click="openRow(row, true)">新增条目</el-button>
            <el-button v-if="row.index === -1 && row.status !== 'published'" class="action-category-publish" :icon="Upload" type="success" plain :disabled="saving" @click="toggleRowCategoryPublication(row)">发布整个分类</el-button>
            <el-button :icon="EditPen" class="action-edit" v-if="row.index >= 0" @click="openRow(row)">编辑内容</el-button>
            <el-button v-if="row.index >= 0" class="action-publish" :icon="row.status === 'published' ? Download : Upload" :type="row.status === 'published' ? 'warning' : 'success'" plain :disabled="saving" @click="toggleRowPublication(row)">{{ row.status === 'published' ? '设为未发表' : '发布' }}</el-button>
            <el-button :icon="ArrowUp" class="action-up" :disabled="!canMoveRow(row, -1)" @click="moveRow(row, -1)">上移</el-button><el-button :icon="ArrowDown" :disabled="!canMoveRow(row, 1)" @click="moveRow(row, 1)">下移</el-button>
            <el-button :icon="Delete" type="danger" plain :disabled="saving" @click="removeRow(row)">移除</el-button>
          </div></template>
        </el-table-column>
      </AdminListTable>
    </template>
    <div v-else class="course-editor-detail">
      <div v-if="active === -1" class="content-edit-layout category-management-layout">
        <section class="category-entries" aria-label="分类条目管理">
          <div class="category-list-header">
            <div><h2>{{ draft.title || '新分类' }}</h2><span>{{ draft.lessons.length }} 个条目</span><p class="category-list-helper">发布整个分类会同时发布这里的全部条目</p></div>
            <div class="category-header-actions">
              <el-button v-if="draft.status !== 'published'" :icon="Upload" type="success" plain :disabled="saving" @click="save(true)">发布整个分类</el-button>
              <el-button :icon="Plus" type="primary" plain :disabled="saving" @click="addLesson">新增条目</el-button>
            </div>
          </div>
          <div class="category-list-filters">
            <el-input v-model="entryQuery" :prefix-icon="Search" clearable aria-label="查找分类条目" placeholder="查找标题或英文标识" />
            <el-select v-model="entryStatus" aria-label="筛选条目状态"><el-option label="全部状态" value="all" /><el-option label="草稿" value="draft" /><el-option label="已发布" value="published" /><el-option label="已归档" value="archived" /></el-select>
          </div>
          <AdminListTable :data="categoryEntries" class="category-entry-table">
            <el-table-column label="条目" min-width="190"><template #default="{ row }"><div class="entry-title">{{ row.entry.title || '未命名条目' }}</div><span class="entry-slug">{{ row.entry.slug || '尚未设置标识' }}</span></template></el-table-column>
            <el-table-column label="状态" width="85"><template #default="{ row }"><el-tag size="small" :type="row.entry.status === 'published' ? 'success' : 'info'">{{ statusName(row.entry.status) }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="440"><template #default="{ row }"><div class="entry-row-actions">
              <el-button :icon="EditPen" :disabled="saving" @click="active = row.index">编辑内容</el-button>
              <el-button :icon="row.entry.status === 'published' ? Download : Upload" :type="row.entry.status === 'published' ? 'warning' : 'success'" plain :disabled="saving" @click="togglePublication(draft, row.index)">{{ row.entry.status === 'published' ? '设为未发表' : '发布' }}</el-button>
              <el-button :icon="ArrowUp" :disabled="saving || row.index === 0" @click="moveDraftEntry(row.index, -1)">上移</el-button>
              <el-button :icon="ArrowDown" :disabled="saving || row.index === draft.lessons.length - 1" @click="moveDraftEntry(row.index, 1)">下移</el-button>
              <el-button :icon="Delete" type="danger" plain :disabled="saving" @click="removeEntry(draft, row.index)">移除</el-button>
            </div></template></el-table-column>
            <template #empty><el-empty :description="draft.lessons.length ? '没有匹配的条目' : '还没有条目，从第一篇内容开始'" :image-size="64"><el-button v-if="draft.lessons.length" :icon="Refresh" @click="entryQuery = ''; entryStatus = 'all'">清除筛选</el-button><el-button v-else :icon="Plus" :disabled="saving" @click="addLesson">添加第一个条目</el-button></el-empty></template>
          </AdminListTable>
        </section>
        <aside class="content-properties" aria-label="分类属性与操作">
          <div class="properties-actions">
            <el-button :icon="Back" :disabled="saving" @click="backToList">返回列表</el-button>
            <el-button :icon="DocumentChecked" type="primary" :loading="saving" @click="save()">保存课程</el-button>
            <el-button v-if="draft.status !== 'published'" class="publish-category-button" :icon="Upload" type="success" :loading="saving" @click="save(true)">发布整个分类</el-button>
            <span class="properties-save-state" role="status">{{ dirty ? '有未保存的修改（含条目排序）' : '已保存' }}</span>
          </div>
          <el-scrollbar class="properties-scroll" max-height="calc(100dvh - 220px)">
            <el-form label-position="top" :disabled="saving" class="properties-form" @submit.prevent>
              <el-breadcrumb separator="/"><el-breadcrumb-item>{{ levelName }}</el-breadcrumb-item><el-breadcrumb-item>分类设置</el-breadcrumb-item></el-breadcrumb>
              <el-form-item label="分类名称"><el-input v-model="draft.title" aria-label="分类名称" maxlength="160" /></el-form-item>
              <el-form-item label="分类英文标识" :error="slugError(draft.slug)"><el-input v-model="draft.slug" aria-label="分类英文标识" placeholder="例如 first-project（不支持中文）" @blur="draft.slug = normalizeSlug(draft.slug)" /></el-form-item>
              <el-form-item label="分类状态"><el-select v-model="draft.status" aria-label="分类状态"><el-option label="草稿" value="draft" /><el-option label="发布" value="published" /><el-option label="归档" value="archived" /></el-select></el-form-item>
              <el-form-item label="目录折叠"><el-switch v-model="draft.directory_collapsible" active-text="允许折叠" inactive-text="始终展开" aria-label="允许折叠" /></el-form-item>
              <el-form-item label="分类排序"><el-input-number v-model="draft.order_index" :min="0" aria-label="分类排序" /></el-form-item>
              <el-form-item label="课程摘要"><el-input v-model="draft.summary" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" /></el-form-item>
              <el-form-item label="开始前准备"><el-input v-model="draft.prerequisites" type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" /></el-form-item>
              <el-button :icon="Delete" type="danger" plain @click="removeEntry(draft, -1)">移除分类</el-button>
            </el-form>
          </el-scrollbar>
        </aside>
      </div>

      <ContentEditorLayout v-if="lesson && active >= 0">
        <MarkdownEditor :key="`${draft!.id}-${active}`" v-model="lesson!.body_markdown" v-model:content-json="lesson!.content_json" :disabled="saving" height="calc(100dvh - 112px)" />
        <template #actions>
            <el-button :icon="Back" :disabled="saving" @click="backToList">返回列表</el-button>
            <el-button :icon="DocumentChecked" type="primary" :loading="saving" @click="save()">保存课程</el-button>
            <el-button v-if="draft.is_standalone && lesson.status !== 'published'" :icon="DocumentChecked" :loading="saving" @click="save(true)">保存并发布</el-button>
            <span class="properties-save-state" role="status">{{ dirty ? '有未保存的修改' : '已保存' }}</span>
            <span class="properties-save-state" role="status">{{ lesson.status === 'draft' ? '草稿不在前台目录展示，发布后即可看到。' : lesson.status === 'archived' ? '已归档条目不在前台目录展示。' : !draft.is_standalone && draft.status !== 'published' ? '所属分类尚未发布，条目暂不在前台目录展示。' : '保存后，此条目将显示在前台目录。' }}</span>
        </template>
        <template #properties>
            <el-form label-position="top" :disabled="saving" @submit.prevent>
              <el-breadcrumb separator="/"><el-breadcrumb-item>{{ levelName }}</el-breadcrumb-item><el-breadcrumb-item>{{ draft.is_standalone ? '无分类条目' : draft.title || '新分类' }}</el-breadcrumb-item></el-breadcrumb>
              <el-form-item label="条目标题"><el-input v-model="lesson.title" aria-label="条目标题" maxlength="180" /></el-form-item>
              <el-form-item label="条目英文标识" :error="slugError(lesson.slug)"><el-input v-model="lesson.slug" aria-label="条目英文标识" placeholder="例如 first-project（不支持中文）" @blur="lesson.slug = normalizeSlug(lesson.slug)" /></el-form-item>
              <el-form-item label="条目状态"><el-select v-model="lesson.status" aria-label="条目状态"><el-option label="草稿" value="draft" /><el-option label="发布" value="published" /><el-option label="归档" value="archived" /></el-select></el-form-item>
              <div v-if="!draft.is_standalone" class="properties-directory-actions">
                <el-button :icon="FolderOpened" @click="active = -1">管理所属分类</el-button>
                <div class="properties-order-actions"><el-button :icon="ArrowUp" :disabled="active === 0" @click="move(-1)">上移条目</el-button><el-button :icon="ArrowDown" :disabled="active === draft.lessons.length - 1" @click="move(1)">下移条目</el-button></div>
              </div>
              <el-button :icon="Delete" type="danger" plain @click="removeEntry(draft, active)">移除条目</el-button>
            </el-form>
        </template>
      </ContentEditorLayout>
    </div>
    <el-dialog v-model="categoryDialog" title="新增课程分类" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="!categorySaving">
      <el-form label-position="top" :disabled="categorySaving" @submit.prevent="saveCategory">
        <el-form-item label="分类名称"><el-input v-model="categoryForm.title" aria-label="分类名称" maxlength="160" autofocus placeholder="例如：前端基础" /></el-form-item>
        <el-form-item label="分类英文标识（可选）"><el-input v-model="categoryForm.slug" aria-label="分类英文标识" placeholder="可留空，系统会自动生成" @blur="categoryForm.slug = normalizeSlug(categoryForm.slug)" /></el-form-item>
        <div class="course-form-row"><el-form-item label="分类状态"><el-select v-model="categoryForm.status" aria-label="分类状态"><el-option label="草稿" value="draft" /><el-option label="发布" value="published" /><el-option label="归档" value="archived" /></el-select></el-form-item><el-form-item label="目录折叠"><el-switch v-model="categoryForm.directory_collapsible" aria-label="允许折叠" active-text="允许折叠" inactive-text="始终展开" /></el-form-item></div>
        <el-form-item label="课程摘要"><el-input v-model="categoryForm.summary" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></el-form-item>
        <el-form-item label="开始前准备"><el-input v-model="categoryForm.prerequisites" type="textarea" :autosize="{ minRows: 2, maxRows: 4 }" /></el-form-item>
        <p v-if="categoryError" class="error" role="alert">{{ categoryError }}</p>
      </el-form>
      <template #footer><el-button :disabled="categorySaving" @click="categoryDialog = false">取消</el-button><el-button type="primary" :loading="categorySaving" @click="saveCategory">创建分类</el-button></template>
    </el-dialog>
  </div>
</template>
<style scoped>
.category-entries { min-width:0; }
.category-management-layout { grid-template-columns:minmax(0,1fr) 340px; gap:24px; align-items:start; }
.category-list-header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:18px; }
.category-list-header > div { min-width:0; }
.category-header-actions { display:flex; align-items:center; justify-content:flex-end; gap:8px; flex-shrink:0; }
.category-list-helper { margin:4px 0 0; color:#9a968b; font-size:11px; }
.category-list-header h2 { margin:0 0 4px; font-size:18px; line-height:1.5; overflow-wrap:anywhere; }
.category-list-header span, .entry-slug { font-size:11px; color:#8a877e; }
.category-list-filters { display:flex; align-items:center; gap:10px; margin-bottom:16px; }
.category-list-filters .el-input { flex:1; min-width:0; }
.category-list-filters .el-select { width:120px; flex-shrink:0; }
.entry-title { font-weight:500; line-height:1.6; }
.category-entry-table { border-top:1px solid #ecece7; }
.category-entry-table :deep(.el-table__empty-text) { line-height:normal; }
@media(max-width:600px) { .category-list-header { align-items:flex-start; } .category-list-filters { flex-wrap:wrap; } .category-list-filters .el-input { flex-basis:100%; } }


.content-writing-area { min-width:0; }
.content-writing-area :deep(.course-block-editor) { min-height:520px; }
.content-properties { min-width:0; border:1px solid #e5e5e2; border-radius:6px; background:#fafaf8; position:sticky; top:82px; }
.properties-actions { display:grid; grid-template-columns:1fr 1fr; gap:8px; padding:14px; border-bottom:1px solid #e5e5e2; }
.properties-actions .el-button { margin:0; padding:8px; }
.properties-actions .publish-category-button { grid-column:1 / -1; font-weight:600; }
.properties-save-state { grid-column:1 / -1; font-size:11px; color:#827d70; }
.properties-form { padding:16px 14px; }
.category-management-layout .properties-form { padding-top:18px; }
.category-management-layout .properties-form::before { content:'分类设置'; display:block; margin-bottom:14px; color:#56534b; font-size:14px; font-weight:600; }
.category-management-layout .properties-form .el-breadcrumb { margin-bottom:18px; }
.properties-form .el-breadcrumb { margin-bottom:20px; font-size:12px; line-height:1.6; }
.properties-form .el-form-item { margin-bottom:16px; }
.properties-form .el-input-number, .properties-form .el-select { width:100%; }
.properties-directory-actions { display:grid; gap:8px; margin:4px 0 16px; }
.properties-order-actions { display:flex; gap:8px; }
.properties-order-actions .el-button { flex:1; margin:0; padding:8px; }
@media(max-width:1100px) {  }
@media(max-width:900px) {
  
  .content-properties { position:static; }
  .properties-scroll :deep(.el-scrollbar__wrap) { max-height:none !important; }
  .content-writing-area :deep(.course-block-editor) { height:60dvh !important; min-height:380px; }
  .content-writing-area :deep(.editor-shell__content) { padding:24px 18px 72px !important; }
  .category-management-layout { grid-template-columns:minmax(0,1fr); }
}

.directory-row-actions { display:grid; grid-template-columns:100px 100px 70px 70px 70px; gap:6px; align-items:center; }
.category-row-actions { display:flex; flex-wrap:wrap; }
.category-row-actions .action-category-publish { font-weight:600; }
.directory-row-actions .action-publish { grid-column:2; grid-row:1; }
.directory-row-actions .action-add { grid-column:2; grid-row:1; }
.directory-row-actions .action-edit { grid-column:1; grid-row:1; }
.directory-row-actions .action-up { grid-column:3; }
.entry-row-actions { display:flex; gap:6px; align-items:center; }
.directory-row-actions .el-button, .entry-row-actions .el-button { margin:0; height:30px; padding:0 8px; font-size:12px; }
.course-editor-actions { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:18px; }
.course-editor-actions .el-select { width:240px; }
.course-editor-actions .el-button + .el-button { margin-left:0; }
.course-level-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:20px; }
.course-editor-detail { min-width:0; }
.course-directory-table { width:100%; }
.category-title { font-weight:600; }
.course-editor-actions .el-breadcrumb { flex:1; line-height:1.6; }
.course-edit-form { min-width:0; }
.course-form-row { display:flex; gap:16px; flex-wrap:wrap; }
.course-form-row .el-form-item { flex:1; min-width:140px; }
.course-dirty { color:#8a7954; font-size:12px; }
@media(max-width:600px) { .course-editor-actions .el-breadcrumb { flex-basis:100%; order:-1; } .category-list-header { flex-wrap:wrap; } .category-header-actions { width:100%; justify-content:flex-start; } }
</style>
