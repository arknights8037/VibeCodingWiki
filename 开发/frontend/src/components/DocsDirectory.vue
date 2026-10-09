<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue';
import { ElTree } from 'element-plus';
import { useRoute } from 'vue-router';
import { api } from '@/services/api';
import { usePreferencesStore } from '@/stores/preferences';
import type { Course, WikiArticle, WikiCategory, Project, Skill } from '@/types';

const route = useRoute();
const prefs = usePreferencesStore();
const t = prefs.text;
const section = computed(() => route.path.startsWith('/wiki') ? 'wiki' : route.path.startsWith('/projects') ? 'projects' : route.path.startsWith('/skills') ? 'skills' : route.path.startsWith('/tools') ? 'tools' : 'courses');
const titles = computed(() => ({ courses: t('课程目录','Courses'), wiki:t('知识库目录','Wiki directory'), projects:t('作品目录','Projects'), skills:t('技能目录','Skills'), tools:t('工具目录','Tools') }));
type Entry = { title: string; href: string; level?: string; prefix?: string; categoryId?: number };
type DirectoryNode = { id: string; label: string; fixed?: boolean; href?: string; children: DirectoryNode[] };
const entries = ref<Entry[]>([]);
const wikiCategories = ref<Pick<WikiCategory, 'id' | 'slug' | 'name' | 'parent_id' | 'order_index'>[]>([]);
const courses = ref<Course[]>([]);
const groups = computed(() => courses.value.filter(c => prefs.level === 'all' || c.difficulty === prefs.level));
const tree = ref<InstanceType<typeof ElTree>>();
const courseTreeData = computed(() => groups.value.map(course => ({
  id: `course-${course.id}`, label: course.title, fixed: course.directory_collapsible === false,
  href: course.is_standalone ? `/courses/${course.slug}` : undefined,
  children: course.is_standalone ? [] : course.lessons.length ? course.lessons.map(lesson => ({id: `lesson-${lesson.id}`, label: lesson.title, href: `/courses/${course.slug}/${lesson.slug}`, children: []})) : [{id: `overview-${course.id}`, label:t('课程概览','Course overview'), href:`/courses/${course.slug}`, children: []}],
})));
const wikiTreeData = computed<DirectoryNode[]>(() => {
  const nodes = new Map<number, DirectoryNode>();
  const roots: DirectoryNode[] = [];
  const categories = [...wikiCategories.value].sort((a, b) => a.order_index - b.order_index || a.id - b.id);
  for (const category of categories) nodes.set(category.id, { id: `wiki-category-${category.id}`, label: category.name, href: `/wiki?category=${encodeURIComponent(category.slug)}`, children: [] });
  for (const category of categories) {
    const node = nodes.get(category.id)!;
    const parent = category.parent_id ? nodes.get(category.parent_id) : undefined;
    (parent?.children || roots).push(node);
  }
  for (const entry of entries.value) {
    const node = { id: `wiki-article-${entry.href}`, label: entry.title, href: entry.href, children: [] };
    (nodes.get(entry.categoryId || 0)?.children || roots).push(node);
  }
  return roots;
});
const treeData = computed<DirectoryNode[]>(() => section.value === 'wiki' ? wikiTreeData.value : courseTreeData.value);
function flatten(nodes: DirectoryNode[]): DirectoryNode[] { return nodes.flatMap(node => [node, ...flatten(node.children)]); }
const expandedKeys = computed(() => flatten(treeData.value).filter(node => node.children.length && (node.fixed || prefs.directoryMode !== 'collapsed')).map(node => node.id));
const currentKey = computed(() => {
  const nodes = flatten(treeData.value);
  if (section.value === 'wiki') return nodes.find(node => node.href === (route.path === '/wiki' && route.query.category ? `/wiki?category=${encodeURIComponent(String(route.query.category))}` : route.path))?.id;
  const legacyLesson = route.hash.startsWith('#lesson-') ? route.hash.slice(8) : '';
  const path = legacyLesson ? `${route.path}/${legacyLesson}` : route.path;
  return (nodes.find(node => node.href === path) || nodes.find(node => node.href?.startsWith(`${route.path}/`)))?.id;
});
watch([currentKey, treeData, () => prefs.directoryMode], async () => {
  await nextTick();
  let parent = currentKey.value ? tree.value?.getNode(currentKey.value)?.parent : undefined;
  while (parent && parent.level > 0) { parent.expand(); parent = parent.parent; }
});
function keepExpanded(data: {id: string; fixed?: boolean}) { if (data.fixed || prefs.directoryMode === 'fixed') void nextTick(() => tree.value?.getNode(data.id)?.expand()); }
const error = ref('');
const loading = ref(false);
const page = ref(1);
const hasMore = ref(false);
let requestId = 0;
const toolEntries = computed<Entry[]>(() => [
  { title: t('知识库数据端点 URL', 'Knowledge base data endpoint URL'), href: '/tools#knowledge-endpoint', prefix: '↗' },
  { title: t('MCP 操作器', 'MCP operator'), href: '/tools#mcp-operator', prefix: '⌘' },
]);
const visible = computed(() => section.value === 'tools' ? toolEntries.value : entries.value.filter(item => section.value !== 'courses' || prefs.level === 'all' || item.level === prefs.level));
async function load(more = false) {
  const id = ++requestId;
  const current = section.value;
  const nextPage = more ? page.value + 1 : 1;
  loading.value = true; error.value = '';
  if (!more) { entries.value = []; hasMore.value = false; }
  try {
    let result: Entry[] = [];
    let remaining = false;
    if (current === 'courses') {
      const data = (await api.get<Course[]>('/courses')).data;
      if (id !== requestId) return;
      courses.value = data;
      result = data.map(c => ({title:c.title, href:`/courses/${c.slug}`, level:c.difficulty, prefix:String(c.order_index).padStart(2,'0')}));
    } else if (current === 'wiki') {
      const [response, categories] = await Promise.all([
        api.get<{items:WikiArticle[]; total:number}>('/wiki', {params:{page:nextPage,page_size:50,sort:'title_asc'}}),
        more ? Promise.resolve({data:wikiCategories.value}) : api.get<typeof wikiCategories.value>('/wiki/categories'),
      ]);
      if (id !== requestId) return;
      wikiCategories.value = categories.data;
      const data = response.data;
      result = data.items.map(a => ({title:a.title,href:`/wiki/${a.slug}`,prefix:'▤',categoryId:a.category.id}));
      remaining = nextPage * 50 < data.total;
    } else if (current === 'projects') {
      result = (await api.get<Project[]>('/projects')).data.map(p => ({title:p.name,href:`/projects/${p.slug}`,prefix:'◇'}));
    } else if (current === 'skills') {
      result = (await api.get<Skill[]>('/skills')).data.map(s => ({title:`${s.name} · ${s.version}`,href:`/skills/${s.slug}/${s.version}`,prefix:'⊞'}));
    }
    if (id !== requestId) return;
    entries.value = more ? [...entries.value, ...result] : result;
    page.value = nextPage; hasMore.value = remaining;
  } catch { if (id === requestId) error.value = t('目录加载失败，请重试。','Could not load the directory. Try again.'); }
  finally { if (id === requestId) loading.value = false; }
}
watch(section, () => { void load(); }, { immediate: true });
</script>
<template>
  <div class="sidebar-directory section-directory">
    <div class="docs-nav-caption">{{ titles[section] }} <span>{{ visible.length }}</span></div>
    <nav :aria-label="section === 'courses' ? '课程目录' : titles[section]" class="docs-course-nav">
      <template v-if="section === 'projects'"><RouterLink class="docs-nav-link" to="/projects">{{ t('全部作品','All projects') }}</RouterLink><RouterLink class="docs-nav-link" to="/projects/mine">{{ t('我的投稿','My submissions') }}</RouterLink></template>
      <RouterLink v-if="section === 'wiki'" class="docs-nav-link" to="/wiki">{{ t('搜索全部词条','Search all articles') }}</RouterLink>
      <el-tree v-if="section === 'courses' || section === 'wiki'" ref="tree" :key="`${section}-${prefs.directoryMode}-${prefs.level}`" :data="treeData" node-key="id" :props="{ class: (data: {fixed?: boolean}) => data.fixed ? 'fixed-category' : '' }" :indent="14" :default-expanded-keys="expandedKeys" :current-node-key="currentKey" :expand-on-click-node="prefs.directoryMode !== 'fixed'" highlight-current class="course-tree" :class="{ 'wiki-tree': section === 'wiki', 'is-fixed': prefs.directoryMode === 'fixed' }" @node-collapse="keepExpanded">
        <template #default="{data}"><RouterLink v-if="data.href" :to="data.href" :class="data.id.startsWith('wiki-category-') ? 'docs-category-link directory-category' : 'docs-course-link'" :aria-current="currentKey === data.id ? 'page' : undefined" @click.stop>{{ data.label }}</RouterLink><span v-else class="directory-category">{{ data.label }}</span></template>
      </el-tree>
      <RouterLink v-for="item in section === 'courses' || section === 'wiki' ? [] : visible" :key="item.href" :to="item.href" class="docs-course-link" :class="{selected: route.path + route.hash === item.href}" :aria-current="route.path + route.hash === item.href ? 'page' : undefined"><span aria-hidden="true">{{ item.prefix }}</span>{{ item.title }}</RouterLink>
    </nav>
    <p v-if="loading" role="status" class="directory-empty">{{ t('正在加载目录…','Loading directory…') }}</p>
    <p v-else-if="error" class="docs-catalog-error" role="alert">{{ error }} <el-button text @click="load()">{{ t('重试','Retry') }}</el-button></p>
    <p v-else-if="!visible.length" class="directory-empty">{{ section === 'courses' ? t('该等级暂无课程，可以切换到全部等级。','No courses at this level. Try all levels.') : t('暂无已发布内容。','No published content yet.') }}</p>
    <el-button v-if="hasMore" text :loading="loading" @click="load(true)">{{ t('加载更多词条','Load more articles') }}</el-button>


  </div>
</template>
<style scoped>
.section-directory .docs-course-link.router-link-active { background:transparent; font-weight:400; color:var(--docs-muted); }
.section-directory .docs-course-link.selected { background:var(--docs-border); color:var(--docs-text); font-weight:600; }
.section-directory .docs-nav-caption { padding-top:16px; padding-bottom:6px; }
.section-directory .docs-course-nav { gap:2px; }
.course-tree { background:transparent; color:var(--docs-text); --el-tree-node-hover-bg-color:var(--ui-control-hover); --el-tree-text-color:var(--ui-control-text); --el-tree-expand-icon-color:var(--ui-control-muted); }
.course-tree :deep(.el-tree-node__content) { height:auto; min-height:30px; border-radius:var(--ui-control-radius); padding-top:2px; padding-bottom:2px; }
.course-tree :deep(.el-tree-node__expand-icon) { padding:4px; }
.course-tree :deep(.el-tree-node.is-current > .el-tree-node__content) { background:var(--docs-border); }
.course-tree :deep(.el-tree-node__label) { white-space:normal; min-width:0; }
.course-tree .docs-course-link { padding:3px 5px; line-height:1.6; white-space:normal; flex:1; }
.directory-category { font-size:12px; font-weight:600; line-height:1.6; white-space:normal; padding:3px 5px; }
.docs-category-link { color:var(--docs-text); flex:1; overflow-wrap:anywhere; }
.course-tree :deep(.fixed-category > .el-tree-node__content > .el-tree-node__expand-icon),
.course-tree.is-fixed :deep(.el-tree-node__expand-icon:not(.is-leaf)) { visibility:hidden; pointer-events:none; }
</style>
