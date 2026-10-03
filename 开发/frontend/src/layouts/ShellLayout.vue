<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePreferencesStore } from "@/stores/preferences";
import { useAuthStore } from "@/stores/auth";
import { apiError } from "@/services/api";
import DocsDirectory from "@/components/DocsDirectory.vue";
import "./docs-shell.css";
import "./docs-header.css";
const auth = useAuthStore();
const prefs = usePreferencesStore();
const t = prefs.text;
const settingsOpen = ref(false);
const systemDark = ref(window.matchMedia('(prefers-color-scheme: dark)').matches);
const resolvedTheme = computed(() => prefs.theme === 'system' ? (systemDark.value ? 'dark' : 'light') : prefs.theme);
const controlPopperClass = computed(() => `wiki-control-popper${resolvedTheme.value === 'dark' ? ' wiki-dark-surface' : ''}`);
const systemMedia = window.matchMedia('(prefers-color-scheme: dark)');
const syncSystemTheme = (event: MediaQueryListEvent) => { systemDark.value = event.matches; };
const levels = computed(() => [ {value:'all', label:t('全部等级','All levels')}, {value:'beginner', label:t('基础','Beginner')}, {value:'intermediate', label:t('进阶','Intermediate')}, {value:'advanced', label:t('专业','Advanced')} ]);
const pages = computed(() => [{ path:'/', zh:'课程', en:'Courses' }, {path:'/wiki', zh:'知识库', en:'Wiki'}, {path:'/projects', zh:'作品', en:'Projects'}, {path:'/skills', zh:'工具', en:'Tools'}]);
function isPageActive(path: string) { return path === '/' ? route.path === '/' || route.path.startsWith('/courses') : route.path.startsWith(path); }
const route = useRoute();
const router = useRouter();
const menuOpen = ref(false);
const query = ref(String(route.query.q || ""));
const logoutError = ref("");
const content = ref<HTMLElement>();
const headings = ref<{id: string; text: string; nested: boolean}[]>([]);
const activeHeading = ref("");
let observer: MutationObserver | undefined;
let scrollObserver: IntersectionObserver | undefined;
function updateOutline() {
  const elements = [...(content.value?.querySelectorAll<HTMLElement>('h2, h3, .markdown-body h1') || [])].filter(el => !el.closest('details:not([open])'));
  headings.value = elements.map((el, index) => { el.id ||= `doc-section-${index}`; return { id: el.id, text: el.textContent?.trim() || '', nested: el.tagName === 'H3' }; });
  scrollObserver?.disconnect();
  scrollObserver = new IntersectionObserver(entries => {
    const visible = entries.find(e => e.isIntersecting);
    if (visible) activeHeading.value = visible.target.id;
  }, { rootMargin: '-65px 0px -65% 0px' });
  elements.forEach(el => scrollObserver?.observe(el));
  if (route.hash) document.getElementById(decodeURIComponent(route.hash.slice(1)))?.scrollIntoView();
}
async function logout() {
  try { await auth.logout(); await router.replace('/'); }
  catch (error) { logoutError.value = apiError(error); }
}
function search() { const path = route.path.startsWith('/wiki') ? '/wiki' : route.path.startsWith('/projects') ? '/projects' : route.path.startsWith('/skills') ? '/skills' : '/'; void router.push({ path, query: query.value ? { q: query.value } : {} }); menuOpen.value = false; }
watch(() => [route.path, route.query.q], () => { query.value = String(route.query.q || ''); });
watch(() => route.fullPath, () => { menuOpen.value = false; });
watch(() => route.path, async () => { activeHeading.value = ''; if (!route.hash) window.scrollTo(0, 0); await nextTick(); updateOutline(); });
watch(() => route.hash, async () => { await nextTick(); updateOutline(); });
onMounted(async () => {
  systemMedia.addEventListener("change", syncSystemTheme);
  observer = new MutationObserver(updateOutline);
  if (content.value) observer.observe(content.value, { childList: true, subtree: true });
  updateOutline();
});
onBeforeUnmount(() => { systemMedia.removeEventListener("change", syncSystemTheme); observer?.disconnect(); scrollObserver?.disconnect(); });
</script>
<template>
  <div class="docs-shell min-h-screen" :class="{'account-route': route.meta.account}" :data-theme="resolvedTheme" :data-font="prefs.fontSize">
    <a class="docs-skip" href="#docs-content">{{ t('跳到正文', 'Skip to content') }}</a>
    <header class="docs-global-header">
      <div class="header-brand-group"><el-button text class="docs-menu-toggle" aria-label="打开学习目录" @click="menuOpen = !menuOpen">☰</el-button><RouterLink class="docs-brand" to="/"><span class="docs-logo">W</span><strong>VibeCoding Wiki</strong></RouterLink></div>
      <nav class="header-page-nav" aria-label="页面切换"><RouterLink v-for="page in pages" :key="page.path" :to="page.path" :class="{ selected: isPageActive(page.path) }" :aria-current="isPageActive(page.path) ? 'page' : undefined">{{ t(page.zh, page.en) }}</RouterLink></nav>
      <div class="header-tools">
        <a class="header-github" href="https://github.com/arknights8037/VibeCodingWiki" target="_blank" rel="noopener noreferrer" aria-label="GitHub 项目仓库"><svg viewBox="0 0 24 24" width="17" height="17" fill="currentColor" aria-hidden="true"><path d="M12 .8a11.3 11.3 0 0 0-3.57 22c.56.1.77-.24.77-.54v-2.1c-3.15.69-3.82-1.33-3.82-1.33-.52-1.3-1.27-1.65-1.27-1.65-1.03-.7.08-.69.08-.69 1.14.08 1.73 1.16 1.73 1.16 1.02 1.73 2.67 1.23 3.32.94.1-.73.4-1.23.73-1.51-2.51-.29-5.15-1.26-5.15-5.59 0-1.24.44-2.25 1.16-3.04-.12-.29-.5-1.44.11-3 0 0 .95-.3 3.1 1.16a10.8 10.8 0 0 1 5.64 0c2.16-1.46 3.1-1.16 3.1-1.16.62 1.56.24 2.71.12 3 .72.79 1.16 1.8 1.16 3.04 0 4.34-2.64 5.3-5.16 5.58.41.36.77 1.05.77 2.1v3.1c0 .3.2.65.78.54A11.3 11.3 0 0 0 12 .8Z"/></svg><span>GitHub</span></a>
        <el-dropdown :popper-class="controlPopperClass" trigger="click" @command="prefs.language = $event"><el-button text aria-label="语言 / Language">{{ prefs.english ? 'EN' : '中文' }}⌄</el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="zh">简体中文</el-dropdown-item><el-dropdown-item command="en">English UI</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
        <el-dropdown :popper-class="controlPopperClass" trigger="click" @command="prefs.theme = $event"><el-button text aria-label="皮肤 / Theme">{{ resolvedTheme === 'dark' ? '☾' : '☼' }}</el-button><template #dropdown><el-dropdown-menu><el-dropdown-item command="light">{{ t('浅色', 'Light') }}</el-dropdown-item><el-dropdown-item command="dark">{{ t('深色', 'Dark') }}</el-dropdown-item><el-dropdown-item command="system">{{ t('跟随系统', 'System') }}</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
        <RouterLink class="header-avatar" :to="auth.user ? '/profile' : {path:'/login', query:{returnTo:route.fullPath}}" :aria-label="auth.user ? auth.user.display_name : t('访客账号','Guest account')"><el-avatar :size="27" :src="auth.user?.avatar_url || undefined">{{ auth.user?.display_name?.slice(0,1) || '○' }}</el-avatar></RouterLink>
        <div class="header-session"><template v-if="auth.user"><span class="session-status">{{ t('已登录','Signed in') }}</span><el-button text @click="logout">{{ t('退出','Sign out') }}</el-button></template><template v-else><span class="session-status">{{ t('未登录','Guest') }}</span><RouterLink :to="{path:'/login', query:{returnTo:route.fullPath}}">{{ t('登录','Sign in') }}</RouterLink></template></div>
      </div>
    </header>
    <aside class="docs-sidebar" :class="{ open: menuOpen }" aria-label="学习目录">
      <div class="sidebar-controls"><label v-if="route.path === '/' || route.path.startsWith('/courses')" class="level-label" for="course-level">{{ t('学习等级', 'Learning level') }}</label><el-select :popper-class="controlPopperClass" class="level-select" v-if="route.path === '/' || route.path.startsWith('/courses')" id="course-level" v-model="prefs.level" aria-label="学习等级"><el-option v-for="level in levels" :key="level.value" :value="level.value" :label="level.label" /></el-select>
      <div v-if="auth.signedIn && (route.path === '/projects' || route.path === '/skills')" class="sidebar-submit-links"><RouterLink v-if="route.path === '/projects'" to="/projects/submit">＋ 新建作品投稿</RouterLink><RouterLink v-else :to="{ path: '/skills', query: { create: '1' } }">＋ 新建工具投稿</RouterLink></div><form class="docs-search" @submit.prevent="search"><el-input v-model="query" :aria-label="route.path.startsWith('/wiki') ? '搜索知识库' : route.path.startsWith('/projects') ? '搜索作品' : route.path.startsWith('/skills') ? '搜索工具' : '搜索课程'" :placeholder="route.path.startsWith('/wiki') ? '搜索知识库…' : route.path.startsWith('/projects') ? '搜索作品…' : route.path.startsWith('/skills') ? '搜索工具…' : '搜索课程…'" /><el-button native-type="submit" aria-label="搜索当前页面">⌕</el-button></form></div>
      <DocsDirectory />
      <div v-if="auth.canReview" class="sidebar-workspace"><RouterLink to="/admin" custom v-slot="{ navigate, href }"><el-button tag="a" :href="href" text @click="navigate">⚙ {{ t('后台管理','Administration') }}</el-button></RouterLink></div>
      <div class="sidebar-settings"><el-button text @click="settingsOpen = true">⚙ {{ t('设置','Settings') }}</el-button><span>VibeCoding Wiki</span></div>
    </aside>
    <button v-if="menuOpen" class="docs-scrim" aria-label="关闭学习目录" @click="menuOpen = false"></button>
    <div class="docs-main min-w-0"><div class="docs-columns">
      <main id="docs-content" ref="content" class="min-w-0" tabindex="-1"><p v-if="logoutError" class="error" role="alert">{{ logoutError }}</p><RouterView :key="route.path" /><footer class="docs-footer">VibeCoding Wiki <span>{{ t('让想法成为可以使用的作品。','Turn ideas into working projects.') }}</span></footer></main>
      <aside class="docs-outline" aria-label="本页目录"><p>{{ t('本页目录','On this page') }}</p><a v-for="heading in headings" :key="heading.id" :href="`#${heading.id}`" :class="{nested: heading.nested, active: activeHeading === heading.id}" :aria-current="activeHeading === heading.id ? 'location' : undefined">{{ heading.text }}</a><span v-if="!headings.length" class="docs-outline-empty">{{ t('当前页面','Current page') }}</span><div class="docs-outline-note">{{ t('遇到不熟悉的概念？','Need an explanation?') }}<RouterLink to="/wiki">{{ t('到知识库找一找 ↗','Explore the wiki ↗') }}</RouterLink></div></aside>
    </div></div>
    <el-dialog v-model="settingsOpen" :title="t('阅读设置','Reading settings')" width="min(460px, calc(100vw - 32px))" class="docs-settings-dialog wiki-reading-dialog" :class="{'wiki-dark-surface': resolvedTheme === 'dark'}">
      <el-form class="settings-fields" label-position="top"><el-form-item :label="t('课程目录','Course directory')"><el-select :popper-class="controlPopperClass" v-model="prefs.directoryMode" aria-label="目录折叠方式"><el-option value="expanded" :label="t('默认展开，可折叠','Expanded, collapsible')" /><el-option value="collapsed" :label="t('默认折叠','Collapsed by default')" /><el-option value="fixed" :label="t('始终展开，不折叠','Always expanded')" /></el-select></el-form-item><el-form-item :label="t('界面语言','Interface language')"><el-select :popper-class="controlPopperClass" v-model="prefs.language" aria-label="界面语言"><el-option value="zh" label="简体中文" /><el-option value="en" label="English UI" /></el-select></el-form-item><p>{{ t('语言设置用于导航与课程列表，文章保留原文。','Language applies to navigation and the course list. Articles keep their original language.') }}</p>
      <el-form-item :label="t('皮肤','Theme')"><el-select :popper-class="controlPopperClass" v-model="prefs.theme" aria-label="皮肤"><el-option value="light" :label="t('浅色','Light')" /><el-option value="dark" :label="t('深色','Dark')" /><el-option value="system" :label="t('跟随系统','System')" /></el-select></el-form-item>
      <el-form-item :label="t('正文字号','Article text size')"><el-select :popper-class="controlPopperClass" v-model="prefs.fontSize" aria-label="正文字号"><el-option value="normal" :label="t('标准','Standard')" /><el-option value="large" :label="t('大号','Large')" /></el-select></el-form-item><p>{{ t('设置自动保存在当前浏览器。','Preferences are saved in this browser.') }}</p></el-form>
      <template #footer><el-button @click="prefs.reset">{{ t('恢复默认','Reset defaults') }}</el-button><el-button type="primary" @click="settingsOpen = false">{{ t('完成','Done') }}</el-button></template>
    </el-dialog>
  </div>
</template>
