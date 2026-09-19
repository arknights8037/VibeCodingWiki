<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { Refresh, SwitchButton, Menu, Check, Close, Download, Star, Delete, Upload, Lock, UserFilled, ArrowDown, Edit } from "@element-plus/icons-vue";
import CourseEditor from "@/components/CourseEditor.vue";
import ContentDisclosure from "@/components/ContentDisclosure.vue";
import ChangePasswordDialog from "@/components/ChangePasswordDialog.vue";
import WikiEditor from "@/components/WikiEditor.vue";
import AdminListTable from "@/components/AdminListTable.vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { confirmRemoval } from "@/services/removal";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { Project, Role, User, Skill } from "@/types";

type Tab = "courses" | "reviews" | "users" | "wiki" | "skills" | "mcp" | "audit";
type Audit = {
  id: number;
  action: string;
  target_type: string;
  target_id: string;
  detail: Record<string, unknown>;
  actor_name: string;
  actor_email: string;
  target_name: string;
  created_at: string;
};
const allTabs: { id: Tab; label: string }[] = [
  { id: "courses", label: "课程编辑" },
  { id: "reviews", label: "审核" },
  { id: "users", label: "用户" },
  { id: "wiki", label: "Wiki 编辑" },
  { id: "skills", label: "Skills" },
  { id: "mcp", label: "MCP 管理" },
  { id: "audit", label: "审计" },
];
const auth = useAuthStore();
const tabs = computed(() => allTabs.filter(
  (item) => auth.user?.role === "admin" || item.id === "reviews",
));
const route = useRoute();
const router = useRouter();
const mobileMenu = ref(false);
const search = ref("");
const wikiEditor = ref<InstanceType<typeof WikiEditor>>();
const courseEditor = ref<InstanceType<typeof CourseEditor>>();

const tab = computed<Tab>(() => tabs.value.find(item => item.id === route.query.section)?.id || "reviews");
const currentTitle = computed(() => ({ courses: "课程编辑", reviews: "项目审核", users: "用户与权限", wiki: "知识库内容", skills: "Skills 资源", mcp: "MCP 管理", audit: "操作审计" })[tab.value]);
const count = computed(() => ({ courses: 0, reviews: pending.value.length, users: users.value.length, wiki: 0, skills: skills.value.length, mcp: mcpTools.value.length, audit: audits.value.length })[tab.value]);
const matches = (value: string) => value.toLowerCase().includes(search.value.trim().toLowerCase());
const filteredProjects = computed(() => pending.value.filter(x => matches(x.name + x.summary)));
const filteredUsers = computed(() => users.value.filter(x => matches(x.display_name + x.email)));
const filteredSkills = computed(() => skills.value.filter(x => matches(x.name + x.version + x.summary)));
const filteredAudits = computed(() => audits.value.filter(x => matches(x.action + x.target_type + x.target_id)));
const auditActionNames: Record<string, string> = { 'user.status.update':'账号状态修改', 'user.role.update':'角色修改', 'auth.password.change':'修改密码', 'wiki.create':'创建词条', 'wiki.update':'修改词条', 'wiki.move':'调整词条顺序', 'wiki.category.create':'创建分类', 'wiki.category.update':'修改分类', 'wiki.category.move':'调整分类顺序', 'wiki.category.delete':'删除分类', 'wiki.delete':'删除词条', 'skill.upload':'上传 Skill', 'skill.intro.update':'修改 Skill 发布简介', 'skill.status.update':'修改 Skill 状态', 'mcp.settings.update':'修改 MCP 鉴权设置', 'mcp.tool.update':'修改 MCP 工具', 'course.save':'保存课程', 'lesson.status.update':'修改课文状态', 'project.approve':'发布投稿', 'project.reject':'驳回投稿', 'project.unpublish':'撤下投稿', 'project.featured.update':'修改推荐状态' };
const auditTargetNames: Record<string, string> = { user:'用户', wiki:'词条', wiki_category:'知识库分类', skill:'Skill', course:'课程', lesson:'课文', project:'投稿项目', projects:'投稿项目' };
async function selectTab(id: Tab) {
  await router.push({ path: '/admin', query: { section: id } });
  mobileMenu.value = false;
}
async function logout() { if (tab.value === 'wiki' && !await wikiEditor.value?.canLeave()) return; await perform(async () => { await auth.logout(); await router.replace('/'); }); }
watch(tab, () => { search.value = ''; });

const pending = ref<Project[]>([]);
const users = ref<User[]>([]);
const audits = ref<Audit[]>([]);
const error = ref("");
const loading = ref(false);
const busy = ref(false);
const reviewStatus = ref("pending_review");
const skills = ref<(Skill & { id: number; status: string })[]>([]);
const mcpTools = ref<{ id: number; name: string; description: string; enabled: boolean }[]>([]);
const mcpSettings = ref({ enabled: true, auth_enabled: false, has_token: false });
const oauthSettings = ref({ github_client_id: '', github_configured: false, gitee_client_id: '', gitee_configured: false });
const oauthSecrets = ref({ github_client_secret: '', gitee_client_secret: '' });
const oauthCallbackBase = window.location.origin;

const skillPublish = ref(true);

async function perform(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try { await action(); }
  catch (reason) {
    if (reason !== "cancel" && reason !== "close") error.value = apiError(reason);
  } finally { busy.value = false; }
}
async function removeItem(resource: string, id: number, name: string) {
  const impacts: Record<string, string> = {
    users: '该账号的登录凭据、投稿及学习进度会同时移除。',
    wiki: '词条将从知识库和搜索结果中移除。',
    projects: '项目将从作品列表和投稿记录中移除。',
    skills: '该版本的内容及下载入口将移除，其他版本不受影响。',
  };
  if (!await confirmRemoval(name, impacts[resource] || '')) return;
  await perform(async () => {
    await api.delete(`/admin/${resource}/${id}`);
    await loadAll();
    ElMessage.success('已移除');
  });
}
async function toggleUser(user: User) {
  await api.patch(`/admin/users/${user.id}/status`, { is_active: !user.is_active });
  await loadAll();
}
async function toggleSkill(item: Skill & { id: number; status: string }) {
  await api.patch(`/admin/skills/${item.id}/status`, { status: item.status === "published" ? "draft" : "published" });
  await loadAll();
}
async function toggleFeatured(item: Project) {
  await api.patch(`/reviews/projects/${item.id}/featured`, { featured: !item.is_featured });
  await loadAll();
}
const skillFile = ref<File | null>(null);
const skillVersion = ref("1.0.0");
const passwordDialog = ref(false);
async function loadAll() {
  loading.value = true;
  error.value = "";
  try {
    const reviewResponse = await api.get<Project[]>("/reviews/projects", { params: { status: reviewStatus.value } });
    pending.value = reviewResponse.data;
    if (auth.user?.role === "admin") {
      const [userResponse, auditResponse, skillResponse, mcpResponse, mcpToolResponse, oauthResponse] = await Promise.all([
        api.get<User[]>("/admin/users"),
        api.get<Audit[]>("/admin/audit-logs"),
        api.get("/admin/skills"),
        api.get("/admin/mcp/settings"),
        api.get("/admin/mcp/tools"),
        api.get("/admin/oauth/settings"),
      ]);
      users.value = userResponse.data;
      audits.value = auditResponse.data;
      skills.value = skillResponse.data;
      mcpSettings.value = mcpResponse.data;
      mcpTools.value = mcpToolResponse.data;
      oauthSettings.value = oauthResponse.data;
    }
  } catch (reason) {
    error.value = apiError(reason);
  } finally { loading.value = false; }
}

async function review(project: Project, action: "approve" | "reject" | "unpublish") {
  let comment: string | undefined;
  if (action === "reject") {
    const answer = await ElMessageBox.prompt(
      "请说明需要修改的内容",
      "驳回投稿",
      { inputType: "textarea", inputValidator: (value: string) => Boolean(value?.trim()) || "请填写驳回原因" },
    );
    comment = answer.value;
  }
  if (action === "unpublish") await ElMessageBox.confirm("撤下后该项目将不再公开展示。", "取消发布");
  await api.post(`/reviews/projects/${project.id}`, {
    action,
    comment,
    featured: false,
  });
  ElMessage.success(action === "approve" ? "已发布" : action === "reject" ? "已驳回" : "已撤下");
  await loadAll();
}

async function updateRole(user: User, role: Role) {
  try {
    await api.patch(`/admin/users/${user.id}/role`, { role });
    await loadAll();
  } catch (reason) {
    ElMessage.error(apiError(reason));
  }
}

async function editSkillIntro(item: Skill & { id: number; status: string }) {
  const answer = await ElMessageBox.prompt("简介会同步显示在前台 Skills 列表中", "编辑发布简介", {
    inputType: "textarea", inputValue: item.summary || "", inputPlaceholder: "用一两句话介绍这个 Skill 的用途",
    inputValidator: (value: string) => Boolean(value?.trim()) || "请填写简介",
  });
  await api.patch(`/admin/skills/${item.id}/intro`, { summary: answer.value.trim() });
  ElMessage.success("Skill 简介已更新");
  await loadAll();
}
async function toggleMcpSetting(key: "enabled" | "auth_enabled", value: boolean) {
  const response = await api.patch("/admin/mcp/settings", { [key]: value });
  mcpSettings.value = response.data;
  ElMessage.success("MCP 设置已保存");
}
async function rotateMcpToken() {
  const token = `${crypto.randomUUID().replaceAll("-", "")} ${crypto.randomUUID().replaceAll("-", "")}`;
  await api.patch("/admin/mcp/settings", { token: token.replace(" ", "") });
  mcpSettings.value = { ...mcpSettings.value, has_token: true };
  ElMessage.success(`新令牌：${token.replace(" ", "")}`);
}
async function saveOAuthSettings() {
  const response = await api.patch('/admin/oauth/settings', { ...oauthSettings.value, ...oauthSecrets.value });
  oauthSettings.value = response.data; oauthSecrets.value = { github_client_secret: '', gitee_client_secret: '' };
  ElMessage.success('GitHub / Gitee OAuth 配置已保存');
}
async function toggleMcpTool(tool: { id: number; enabled: boolean }) {
  const response = await api.patch(`/admin/mcp/tools/${tool.id}`, { enabled: !tool.enabled });
  tool.enabled = response.data.enabled;
}
function updateRoleValue(user: User, value: string | number | boolean | undefined) {
  void perform(() => updateRole(user, value as Role));
}

function pickSkill(event: Event) {
  skillFile.value = (event.target as HTMLInputElement).files?.[0] || null;
}

async function uploadSkill() {
  if (!skillFile.value) return;
  const data = new FormData();
  data.append("archive", skillFile.value);
  data.append("version", skillVersion.value);
  data.append("publish", String(skillPublish.value));
  try {
    await api.post("/admin/skills/upload", data);
    ElMessage.success("Skill 已上传");
    await loadAll();
  } catch (reason) {
    ElMessage.error(apiError(reason));
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="admin-workspace min-h-screen bg-white text-stone-700">
    <aside class="workspace-sidebar" :class="{ 'is-open': mobileMenu }" aria-label="后台目录">
      <div class="workspace-brand"><span class="workspace-logo">W</span><div><strong>VibeCoding Wiki</strong><small>内容管理工作区</small></div></div>
      <div class="sidebar-caption">工作空间</div>
      <nav class="flex flex-col gap-1" aria-label="管理模块">
        <button v-for="item in tabs" :key="item.id" :aria-label="item.label" :aria-current="tab === item.id ? 'page' : undefined" class="sidebar-link" :class="{ selected: tab === item.id }" @click="selectTab(item.id)">
          <span aria-hidden="true" class="nav-symbol">{{ { courses: '▤', reviews: '☷', users: '♙', wiki: '▤', skills: '◇', mcp: '⌘', audit: '◷' }[item.id] }}</span>
          {{ { courses: '课程编辑', reviews: '项目审核', users: '用户与权限', wiki: '知识库内容', skills: 'Skills 资源', mcp: 'MCP 管理', audit: '操作审计' }[item.id] }}
        </button>
        <button v-if="auth.isAdmin" class="sidebar-link" aria-label="修改密码" @click="passwordDialog = true"><el-icon class="nav-symbol"><Lock /></el-icon>修改密码</button>
      </nav>
      <div class="sidebar-caption mt-8">快捷访问</div>
      <RouterLink class="sidebar-link" to="/wiki"><span aria-hidden="true">↗</span> 浏览知识库</RouterLink>
      <RouterLink class="sidebar-link" to="/"><span aria-hidden="true">⌂</span> 返回网站</RouterLink>
      <div class="sidebar-account"><el-avatar :size="30">{{ auth.user?.display_name?.slice(0, 1) }}</el-avatar><div class="min-w-0 flex-1"><strong>{{ auth.user?.display_name }}</strong><small>{{ auth.isAdmin ? '管理员' : '审核员' }}</small></div><el-button :icon="SwitchButton" @click="logout">退出</el-button></div>
    </aside>
    <button v-if="mobileMenu" class="sidebar-scrim" aria-label="关闭目录" @click="mobileMenu = false"></button>
    <div class="workspace-main min-w-0">
      <header class="workspace-topbar flex items-center justify-between gap-4">
        <div class="flex items-center gap-3"><el-button :icon="Menu" class="menu-toggle" aria-label="打开目录" @click="mobileMenu = !mobileMenu"></el-button><span class="text-stone-400">工作空间</span><span class="text-stone-300">/</span><span>{{ currentTitle }}</span></div>
        <div class="topbar-actions"><el-button :icon="Refresh" :loading="loading" @click="tab === 'courses' ? courseEditor?.refresh() : tab === 'wiki' ? wikiEditor?.refresh() : loadAll()">刷新数据</el-button><el-dropdown trigger="click" @command="() => logout()"><span class="user-menu"><el-icon><UserFilled /></el-icon>{{ auth.user?.display_name }}<el-icon><ArrowDown /></el-icon></span><template #dropdown><el-dropdown-menu><el-dropdown-item command="logout"><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item></el-dropdown-menu></template></el-dropdown></div>
      </header>
      <div class="document-layout" :class="{ 'course-management': tab === 'courses' }">
      <main class="workspace-document min-w-0">
        <h1 class="sr-only">后台管理</h1>
        <el-alert v-if="error" :title="error" type="error" show-icon :closable="false"><el-button :icon="Refresh" @click="loadAll">重试加载</el-button></el-alert>
        <p v-if="loading" role="status">正在加载后台数据…</p>
        <CourseEditor v-if="tab === 'courses'" ref="courseEditor" />
        <div v-if="tab !== 'courses' && tab !== 'wiki'" id="records" class="records-toolbar flex items-center justify-between gap-4"><div class="document-meta"><span>{{ count }} 条记录</span></div><el-input v-model="search" aria-label="搜索当前列表" placeholder="搜索当前列表…" clearable class="record-search" /></div>
        <fieldset v-if="tab !== 'courses'" :disabled="busy || loading" class="admin-controls">
    <section v-if="tab === 'reviews'">
      <label>投稿状态 <select v-model="reviewStatus" @change="loadAll">
        <option value="pending_review">待审核</option><option value="published">已发布</option>
        <option value="rejected">已驳回</option><option value="draft">草稿</option><option value="archived">归档</option>
      </select></label>
      <AdminListTable :data="filteredProjects" empty-text="该状态下暂无投稿"><el-table-column label="项目" min-width="280"><template #default="{ row }">
            <strong>{{ row.name }}</strong><br />{{ row.summary }}<ContentDisclosure title="查看完整说明"><p class="disclosure-plain-text">{{ row.description_markdown }}</p><p>许可证：{{ row.license_name }} · {{ row.tech_stack.join(", ") }}</p></ContentDisclosure>
          </template></el-table-column><el-table-column label="仓库" min-width="120"><template #default="{ row }"><a :href="row.repository_url" target="_blank" rel="noreferrer">检查仓库</a></template></el-table-column><el-table-column label="操作" min-width="260"><template #default="{ row }"><div class="admin-row-actions">
              <template v-if="row.status === 'pending_review'"><el-button :icon="Check" @click="perform(() => review(row, 'approve'))">通过</el-button><el-button :icon="Close" @click="perform(() => review(row, 'reject'))">驳回</el-button>
              </template>
              <template v-if="row.status === 'published'"><el-button :icon="Download" @click="perform(() => review(row, 'unpublish'))">取消发布</el-button><el-button :icon="Star" @click="perform(() => toggleFeatured(row))">{{ row.is_featured ? '取消推荐' : '设为推荐' }}</el-button>
              </template>
              <el-button :icon="Delete" v-if="auth.isAdmin" type="danger" plain @click="removeItem('projects', row.id, row.name)">移除</el-button></div></template></el-table-column></AdminListTable>
    </section>
    <section v-else-if="tab === 'users'">
      <AdminListTable :data="filteredUsers" empty-text="没有匹配的用户"><el-table-column label="用户" min-width="180"><template #default="{ row }"><span class="member-avatar">{{ row.display_name.slice(0, 1) }}</span>{{ row.display_name }}</template></el-table-column><el-table-column prop="email" label="邮箱" min-width="220" /><el-table-column label="角色" width="140"><template #default="{ row }"><el-select :aria-label="`${row.display_name}的角色`" :model-value="row.role" :disabled="row.id === auth.user?.id" @change="updateRoleValue(row, $event)"><el-option value="user" label="普通用户" /><el-option value="reviewer" label="审核员" /><el-option value="admin" label="管理员" /></el-select></template></el-table-column><el-table-column label="账号状态" min-width="240"><template #default="{ row }"><div class="admin-row-actions"><span class="account-state">{{ row.is_active ? '正常' : '已停用' }}</span><el-button :icon="SwitchButton" :disabled="row.id === auth.user?.id" @click="perform(() => toggleUser(row))">{{ row.is_active ? '停用' : '启用' }}</el-button><el-button :icon="Delete" type="danger" plain :disabled="row.id === auth.user?.id" @click="removeItem('users', row.id, row.display_name)">移除</el-button></div></template></el-table-column></AdminListTable>
    </section>
    <WikiEditor v-else-if="tab === 'wiki'" ref="wikiEditor" />
    <section v-else-if="tab === 'skills'" class="form-panel">
      <div class="section-actions skill-upload-top"><label>版本<input v-model="skillVersion" class="skill-version-input" /></label><label><input v-model="skillPublish" type="checkbox" />上传后发布</label><input id="skill-zip-top" class="sr-only" type="file" accept=".zip" @change="pickSkill" /><label for="skill-zip-top" class="el-button"><el-icon><Upload /></el-icon>选择 ZIP</label><el-button type="success" :disabled="!skillFile || !skillVersion.trim()" @click="perform(uploadSkill)">上传 Skill</el-button><span v-if="skillFile" class="muted">{{ skillFile.name }}</span></div>
      <AdminListTable :data="filteredSkills" empty-text="暂无 Skills"><el-table-column label="Skill / 版本" min-width="260"><template #default="{ row }"><strong>{{ row.name }} / {{ row.version }}</strong><small class="audit-raw">{{ row.summary || '尚未填写发布简介' }}</small></template></el-table-column><el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small" effect="light">{{ row.status === 'published' ? '已发布' : '草稿' }}</el-tag></template></el-table-column><el-table-column label="操作" min-width="280"><template #default="{ row }"><div class="admin-row-actions"><el-button :icon="Edit" @click="perform(() => editSkillIntro(row))">编辑简介</el-button><el-button :icon="Upload" @click="perform(() => toggleSkill(row))">{{ row.status === 'published' ? '下架' : '发布' }}</el-button><el-button :icon="Delete" type="danger" plain @click="removeItem('skills', row.id, `${row.name} / ${row.version}`)">移除</el-button></div></template></el-table-column></AdminListTable>
    </section>
    <section v-else-if="tab === 'mcp'" class="form-panel mcp-panel">
      <div class="section-actions"><h2>MCP 服务</h2><span class="muted">管理服务开关、工具暴露范围和访问鉴权</span></div>
      <div class="mcp-settings"><label><input type="checkbox" :checked="mcpSettings.enabled" @change="toggleMcpSetting('enabled', ($event.target as HTMLInputElement).checked)" />启用 MCP 服务</label><label><input type="checkbox" :checked="mcpSettings.auth_enabled" @change="toggleMcpSetting('auth_enabled', ($event.target as HTMLInputElement).checked)" />开启令牌鉴权</label><el-button @click="perform(rotateMcpToken)">{{ mcpSettings.has_token ? '轮换鉴权令牌' : '生成鉴权令牌' }}</el-button></div>
      <div class="oauth-config"><div class="section-actions"><h2>第三方账号绑定</h2><span class="muted">配置官方 OAuth 应用后，用户可从个人页自动绑定 GitHub / Gitee</span></div><div class="oauth-admin-grid"><label>GitHub Client ID<input v-model="oauthSettings.github_client_id" placeholder="Client ID" /></label><label>GitHub Client Secret<input v-model="oauthSecrets.github_client_secret" type="password" placeholder="留空则保持不变" /></label><label>Gitee Client ID<input v-model="oauthSettings.gitee_client_id" placeholder="Client ID" /></label><label>Gitee Client Secret<input v-model="oauthSecrets.gitee_client_secret" type="password" placeholder="留空则保持不变" /></label></div><p class="muted">回调地址：{{ `${oauthCallbackBase}/api/v1/auth/oauth/github/callback` }} 和 {{ `${oauthCallbackBase}/api/v1/auth/oauth/gitee/callback` }}</p><el-button type="primary" @click="perform(saveOAuthSettings)">保存 OAuth 配置</el-button></div>
      <h2>MCP 工具管理</h2><AdminListTable :data="mcpTools" empty-text="暂无 MCP 工具"><el-table-column prop="name" label="工具" min-width="180" /><el-table-column prop="description" label="说明" min-width="300" /><el-table-column label="暴露状态" width="160"><template #default="{ row }"><el-switch v-model="row.enabled" @change="toggleMcpTool(row)" /><span class="ml-2">{{ row.enabled ? '已启用' : '已停用' }}</span></template></el-table-column></AdminListTable>
    </section>
    <section v-else>
      <AdminListTable :data="filteredAudits" empty-text="暂无匹配的操作记录"><el-table-column label="时间" min-width="180"><template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template></el-table-column><el-table-column label="操作者" min-width="160"><template #default="{ row }">{{ row.actor_name }}<small v-if="row.actor_email"> · {{ row.actor_email }}</small></template></el-table-column><el-table-column label="动作" min-width="180"><template #default="{ row }"><strong>{{ auditActionNames[row.action] || row.action }}</strong><small class="audit-raw">{{ row.action }}</small></template></el-table-column><el-table-column label="目标" min-width="220"><template #default="{ row }"><strong>{{ row.target_name || '未命名目标' }}</strong><small class="audit-raw">{{ auditTargetNames[row.target_type] || row.target_type }} #{{ row.target_id }}</small></template></el-table-column><el-table-column label="详细记录" min-width="300"><template #default="{ row }"><code>{{ JSON.stringify(row.detail) }}</code></template></el-table-column></AdminListTable>
    </section>
    </fieldset>
    </main>
    </div></div>
  </div>
  <ChangePasswordDialog v-model="passwordDialog" />
</template>
<style scoped src="./admin-workspace.css"></style>
