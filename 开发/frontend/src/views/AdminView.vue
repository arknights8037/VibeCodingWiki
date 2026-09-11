<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api, apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";
import type { Project, Role, User } from "@/types";

type Tab = "reviews" | "users" | "wiki" | "skills" | "audit";
type Audit = {
  id: number;
  action: string;
  target_type: string;
  target_id: string;
  created_at: string;
};
const allTabs: { id: Tab; label: string }[] = [
  { id: "reviews", label: "审核" },
  { id: "users", label: "用户" },
  { id: "wiki", label: "Wiki 编辑" },
  { id: "skills", label: "Skills" },
  { id: "audit", label: "审计" },
];
const auth = useAuthStore();
const tabs = allTabs.filter(
  (item) => auth.user?.role === "admin" || item.id === "reviews",
);
const tab = ref<Tab>("reviews");
const pending = ref<Project[]>([]);
const users = ref<User[]>([]);
const audits = ref<Audit[]>([]);
const error = ref("");
const wikiForm = reactive({
  slug: "",
  title: "",
  summary: "",
  body_markdown: "",
  difficulty: "beginner",
  category: "AI Coding",
  tags: "",
  status: "draft",
});
const skillFile = ref<File | null>(null);
const skillVersion = ref("1.0.0");

async function loadAll() {
  try {
    const reviewResponse = await api.get<Project[]>("/reviews/projects");
    pending.value = reviewResponse.data;
    if (auth.user?.role === "admin") {
      const [userResponse, auditResponse] = await Promise.all([
        api.get<User[]>("/admin/users"),
        api.get<Audit[]>("/admin/audit-logs"),
      ]);
      users.value = userResponse.data;
      audits.value = auditResponse.data;
    }
  } catch (reason) {
    error.value = apiError(reason);
  }
}

async function review(project: Project, action: "approve" | "reject") {
  let comment: string | undefined;
  if (action === "reject") {
    const answer = await ElMessageBox.prompt(
      "请说明需要修改的内容",
      "驳回投稿",
      { inputType: "textarea" },
    );
    comment = answer.value;
  }
  await api.post(`/reviews/projects/${project.id}`, {
    action,
    comment,
    featured: false,
  });
  ElMessage.success(action === "approve" ? "已发布" : "已驳回");
  await loadAll();
}

async function updateRole(user: User, event: Event) {
  const role = (event.target as HTMLSelectElement).value as Role;
  try {
    await api.patch(`/admin/users/${user.id}/role`, { role });
    await loadAll();
  } catch (reason) {
    ElMessage.error(apiError(reason));
  }
}

async function createWiki() {
  try {
    await api.post("/admin/wiki", {
      ...wikiForm,
      tags: wikiForm.tags
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    });
    ElMessage.success("词条已保存");
    Object.assign(wikiForm, {
      slug: "",
      title: "",
      summary: "",
      body_markdown: "",
      tags: "",
    });
  } catch (reason) {
    ElMessage.error(apiError(reason));
  }
}

function pickSkill(event: Event) {
  skillFile.value = (event.target as HTMLInputElement).files?.[0] || null;
}

async function uploadSkill() {
  if (!skillFile.value) return;
  const data = new FormData();
  data.append("archive", skillFile.value);
  data.append("version", skillVersion.value);
  data.append("publish", "true");
  try {
    await api.post("/admin/skills/upload", data);
    ElMessage.success("Skill 已上传");
  } catch (reason) {
    ElMessage.error(apiError(reason));
  }
}

onMounted(loadAll);
</script>

<template>
  <div class="page">
    <div class="eyebrow">Administration</div>
    <h1>后台管理</h1>
    <p v-if="error" class="error">{{ error }}</p>
    <div class="admin-tabs">
      <button
        v-for="item in tabs"
        :key="item.id"
        :class="{ active: tab === item.id }"
        @click="tab = item.id"
      >
        {{ item.label }}
      </button>
    </div>
    <section v-if="tab === 'reviews'">
      <table class="data-table">
        <thead>
          <tr>
            <th>项目</th>
            <th>仓库</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in pending" :key="item.id">
            <td>
              <strong>{{ item.name }}</strong
              ><br />{{ item.summary }}
            </td>
            <td><a :href="item.repository_url" target="_blank">检查仓库</a></td>
            <td>
              <button @click="review(item, 'approve')">通过</button>
              <button @click="review(item, 'reject')">驳回</button>
            </td>
          </tr>
          <tr v-if="!pending.length">
            <td colspan="3">暂无待审核投稿</td>
          </tr>
        </tbody>
      </table>
    </section>
    <section v-else-if="tab === 'users'">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户</th>
            <th>邮箱</th>
            <th>角色</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.display_name }}</td>
            <td>{{ user.email }}</td>
            <td>
              <select :value="user.role" @change="updateRole(user, $event)">
                <option value="user">user</option>
                <option value="reviewer">reviewer</option>
                <option value="admin">admin</option>
              </select>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
    <section v-else-if="tab === 'wiki'">
      <form class="form-grid form-panel" @submit.prevent="createWiki">
        <div class="split">
          <label>英文标识<input v-model="wikiForm.slug" required /></label
          ><label>标题<input v-model="wikiForm.title" required /></label>
        </div>
        <label>摘要<textarea v-model="wikiForm.summary" required /></label
        ><label
          >正文 Markdown<textarea v-model="wikiForm.body_markdown" required />
        </label>
        <div class="split">
          <label>分类<input v-model="wikiForm.category" /></label
          ><label
            >标签<input v-model="wikiForm.tags" placeholder="ai,workflow"
          /></label>
        </div>
        <div class="split">
          <label
            >难度<select v-model="wikiForm.difficulty">
              <option value="beginner">入门</option>
              <option value="intermediate">进阶</option>
              <option value="advanced">高级</option>
            </select></label
          ><label
            >状态<select v-model="wikiForm.status">
              <option value="draft">草稿</option>
              <option value="published">发布</option>
            </select></label
          >
        </div>
        <div class="form-actions"><button>保存词条</button></div>
      </form>
    </section>
    <section v-else-if="tab === 'skills'" class="form-panel">
      <h2>上传 Agent Skill</h2>
      <div class="form-grid">
        <label>版本<input v-model="skillVersion" /></label
        ><label
          >ZIP 文件<input type="file" accept=".zip" @change="pickSkill"
        /></label>
        <div class="form-actions">
          <button @click="uploadSkill">校验并发布</button>
        </div>
      </div>
    </section>
    <section v-else>
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>动作</th>
            <th>目标</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in audits" :key="item.id">
            <td>{{ new Date(item.created_at).toLocaleString() }}</td>
            <td>{{ item.action }}</td>
            <td>{{ item.target_type }} #{{ item.target_id }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>
