<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { api, apiError } from "@/services/api";
const auth = useAuthStore(); const route = useRoute(); const router = useRouter();
const section = computed(() => String(route.params.section || "info"));
const displayName = ref(auth.user?.display_name || ""); const realName = ref(auth.user?.real_name || ""); const github = ref(auth.user?.github_username || ""); const gitee = ref(auth.user?.gitee_username || "");
const currentPassword = ref(""); const newPassword = ref(""); const confirmPassword = ref(""); const mcpToken = ref(""); const saving = ref(false); const message = ref(""); const error = ref("");
const menu = [{key:"info",label:"个人信息",hint:"姓名、头像和开发者账号"},{key:"security",label:"账号安全",hint:"密码和 MCP 凭据"},{key:"projects",label:"我的项目",hint:"查看提交和审核状态"},{key:"notifications",label:"通知",hint:"审核与系统消息"}];
const avatarSrc = computed(() => auth.user?.avatar_url || undefined);
const roleLabel = computed(() => ({admin:"管理员",reviewer:"审核员",user:"普通用户"}[auth.user?.role || "user"]));
const notifications = ref<{id:string; title:string; message:string; created_at:string}[]>([]);
async function loadNotifications(){ if(section.value !== "notifications") return; try { notifications.value=(await api.get("/auth/notifications")).data; } catch(e){ error.value=apiError(e); } }
function go(key:string){ void router.push(key === "info" ? "/profile" : `/profile/${key}`); }
function resetStatus(){ message.value=""; error.value=""; }
async function saveProfile(){ saving.value=true; resetStatus(); try { const profile=(await api.patch("/auth/profile",{display_name:displayName.value,real_name:realName.value||null})).data; const social=(await api.patch("/auth/social-accounts",{github_username:github.value||null,gitee_username:gitee.value||null})).data; auth.user={...profile,...social}; message.value="个人信息已保存"; } catch(e){error.value=apiError(e)} finally{saving.value=false} }
async function uploadAvatar(event:Event){ const file=(event.target as HTMLInputElement).files?.[0]; if(!file)return; resetStatus(); if(file.size>2*1024*1024){error.value="头像文件不能超过 2MB";return;} const data=new FormData(); data.append("file",file); try{auth.user=(await api.post("/auth/avatar",data)).data;message.value="头像已更新"}catch(e){error.value=apiError(e)} }
async function changePassword(){resetStatus();if(!currentPassword.value){error.value="请输入当前密码";return}if(newPassword.value!==confirmPassword.value){error.value="两次输入的新密码不一致";return}try{await api.post("/auth/password",{current_password:currentPassword.value,new_password:newPassword.value});message.value="密码已修改";currentPassword.value="";newPassword.value="";confirmPassword.value=""}catch(e){error.value=apiError(e)}}
async function createToken(){resetStatus();try{mcpToken.value=(await api.post("/auth/mcp-token")).data.message;message.value="新凭据已生成，请立即复制保存"}catch(e){error.value=apiError(e)}}
function bind(provider:string){ window.location.href=`/api/v1/auth/oauth/${provider}/start`; }
loadNotifications();
</script>
<template>
  <div class="account-page">
    <section class="account-heading" aria-labelledby="account-title">
      <div class="account-identity">
        <el-avatar :size="72" :src="avatarSrc">{{auth.user?.display_name?.slice(0,1)}}</el-avatar>
        <div><div class="eyebrow">ACCOUNT CENTER</div><h1 id="account-title">账户中心</h1><p class="lede">管理个人资料、安全设置与社区动态。</p></div>
      </div>
      <div class="account-summary"><strong>{{auth.user?.display_name}}</strong><span>{{auth.user?.email}}</span><small>{{roleLabel}}</small></div>
    </section>
    <div class="account-layout"><nav class="account-menu" aria-label="账户设置"><div class="account-menu-title">账户设置</div><button v-for="item in menu" :key="item.key" type="button" :class="{active:section===item.key}" :aria-current="section===item.key ? 'page' : undefined" @click="go(item.key)"><strong>{{item.label}}</strong><span>{{item.hint}}</span></button></nav><div class="account-content">
      <section v-if="section==='info'" class="account-panel"><div class="panel-heading"><div><h2>个人信息</h2><p>这些信息会用于你的社区身份展示。</p></div><el-button type="primary" :loading="saving" @click="saveProfile">保存更改</el-button></div><el-form label-position="top"><div class="account-form-grid"><el-form-item label="用户名"><el-input v-model="displayName" maxlength="80"/></el-form-item><el-form-item label="真名"><el-input v-model="realName" maxlength="80" placeholder="可选"/></el-form-item></div><el-form-item label="头像"><div class="avatar-editor"><el-avatar :size="74" :src="avatarSrc">{{displayName.slice(0,1)}}</el-avatar><div><input id="avatar-file" class="avatar-file" type="file" accept="image/png,image/jpeg,image/webp,image/gif" @change="uploadAvatar"><label for="avatar-file" class="upload-button">上传头像</label><p>支持 JPG、PNG、WEBP、GIF，最大 2MB。</p></div></div></el-form-item><div class="oauth-account-grid" aria-label="第三方账号绑定"><article class="oauth-account-card"><div><strong>GitHub</strong><span :class="github ? 'oauth-bound' : 'oauth-unbound'">{{github ? '已绑定' : '未绑定'}}</span></div><p>{{ github || '绑定后可从 GitHub 快速关联身份。' }}</p><el-button @click="bind('github')">{{github ? '修改绑定' : '绑定 GitHub'}}</el-button></article><article class="oauth-account-card"><div><strong>Gitee</strong><span :class="gitee ? 'oauth-bound' : 'oauth-unbound'">{{gitee ? '已绑定' : '未绑定'}}</span></div><p>{{ gitee || '绑定后可从 Gitee 快速关联身份。' }}</p><el-button @click="bind('gitee')">{{gitee ? '修改绑定' : '绑定 Gitee'}}</el-button></article></div></el-form></section>
      <section v-else-if="section==='security'" class="account-panel"><div class="panel-heading"><div><h2>账号安全</h2><p>更新密码并管理外部工具访问凭据。</p></div></div><h3>修改密码</h3><el-form class="security-fields" @submit.prevent="changePassword"><el-input v-model="currentPassword" type="password" show-password autocomplete="current-password" placeholder="当前密码"/><el-input v-model="newPassword" type="password" show-password autocomplete="new-password" placeholder="新密码（至少 8 位，含字母和数字）"/><el-input v-model="confirmPassword" type="password" show-password autocomplete="new-password" placeholder="确认新密码"/><el-button native-type="submit">修改密码</el-button></el-form><el-divider/><h3>MCP 凭据</h3><p class="result-meta">生成后只会完整显示一次，请复制到安全的位置保存。</p><div class="token-row"><el-button @click="createToken">生成新凭据</el-button><el-input v-if="mcpToken" v-model="mcpToken" readonly/></div></section>
      <section v-else-if="section==='projects'" class="account-panel"><div class="panel-heading"><div><h2>我的项目</h2><p>管理你提交的项目和审核进度。</p></div><RouterLink class="account-link-button" to="/projects/submit">提交项目</RouterLink></div><div class="empty-account"><span>◫</span><h3>进入项目管理</h3><p>查看已提交项目、审核意见和发布状态。</p><RouterLink to="/projects/mine">查看我的项目 →</RouterLink></div></section>
      <section v-else class="account-panel"><div class="panel-heading"><div><h2>通知</h2><p>项目审核、系统更新和社区动态会显示在这里。</p></div></div><div v-if="notifications.length" class="notification-list"><article v-for="item in notifications" :key="item.id"><div><h3>{{item.title}}</h3><p>{{item.message}}</p></div><time>{{new Date(item.created_at).toLocaleDateString()}}</time></article></div><div v-else class="empty-account"><span>♡</span><h3>暂无新通知</h3><p>有新的审核结果或系统消息时，我们会在这里提醒你。</p></div></section>
      <p v-if="message" class="success" role="status">{{message}}</p><p v-if="error" class="error" role="alert">{{error}}</p>
    </div></div>
  </div>
</template>
