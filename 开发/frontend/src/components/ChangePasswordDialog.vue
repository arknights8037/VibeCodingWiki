<script setup lang="ts">
import { reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { api, apiError } from '@/services/api';
const open = defineModel<boolean>({ default:false });
const busy = ref(false);
const error = ref('');
const form = reactive({ current_password:'', new_password:'', confirm_password:'' });
function reset() { Object.assign(form, { current_password:'', new_password:'', confirm_password:'' }); error.value = ''; }
async function save() {
  if (busy.value) return;
  error.value = '';
  if (!form.current_password) { error.value = '请输入当前密码'; return; }
  if (form.new_password.length < 10 || form.new_password.length > 128 || !/[a-zA-Z]/.test(form.new_password) || !/\d/.test(form.new_password)) { error.value = '新密码需为 10–128 个字符，包含字母和数字'; return; }
  if (form.new_password !== form.confirm_password) { error.value = '两次输入的新密码不一致'; return; }
  busy.value = true;
  try { await api.post('/auth/password', { current_password:form.current_password, new_password:form.new_password }); open.value = false; ElMessage.success('密码已修改'); }
  catch (reason) { error.value = apiError(reason); }
  finally { busy.value = false; }
}
</script>
<template>
  <el-dialog v-model="open" title="修改密码" width="min(420px, calc(100vw - 32px))" :close-on-click-modal="!busy" :close-on-press-escape="!busy" :show-close="!busy" @closed="reset">
    <el-alert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <el-form label-position="top" :disabled="busy" @submit.prevent="save">
      <el-form-item label="当前密码"><el-input v-model="form.current_password" aria-label="当前密码" type="password" show-password autocomplete="current-password" /></el-form-item>
      <el-form-item label="新密码"><el-input v-model="form.new_password" aria-label="新密码" type="password" show-password autocomplete="new-password" /></el-form-item>
      <p>10–128 个字符，包含字母和数字。</p>
      <el-form-item label="确认新密码"><el-input v-model="form.confirm_password" aria-label="确认新密码" type="password" show-password autocomplete="new-password" /></el-form-item>
      <el-button :disabled="busy" @click="open = false">取消</el-button><el-button type="primary" native-type="submit" :loading="busy">保存密码</el-button>
    </el-form>
  </el-dialog>
</template>
