<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { apiError } from "@/services/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();
const mode = ref<"login" | "register">("login");
const form = reactive({ display_name: "", email: "", password: "" });
const error = ref("");
const busy = ref(false);

async function submit() {
  busy.value = true;
  error.value = "";
  try {
    if (mode.value === "register")
      await auth.register(form.display_name, form.email, form.password);
    else await auth.login(form.email, form.password);
    await router.push("/");
  } catch (reason) {
    error.value = apiError(reason);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="page narrow">
    <div class="split">
      <div>
        <div class="eyebrow">Account</div>
        <h1>{{ mode === "login" ? "登录" : "创建账号" }}</h1>
        <p class="lede">登录后可以记录课程进度、提交开源项目并查看审核结果。</p>
      </div>
      <form class="form-grid form-panel" @submit.prevent="submit">
        <label v-if="mode === 'register'"
          >显示名称<input
            v-model="form.display_name"
            required
            minlength="2"
            maxlength="80"
        /></label>
        <label
          >邮箱<input
            v-model="form.email"
            type="email"
            required
            autocomplete="email"
        /></label>
        <label
          >密码<input
            v-model="form.password"
            type="password"
            required
            minlength="10"
            autocomplete="current-password"
        /></label>
        <div class="form-actions">
          <button type="submit" :disabled="busy">
            {{
              busy ? "处理中…" : mode === "login" ? "登录" : "注册并登录"
            }}</button
          ><button
            class="text-button"
            type="button"
            @click="mode = mode === 'login' ? 'register' : 'login'"
          >
            {{ mode === "login" ? "没有账号" : "已有账号" }}
          </button>
        </div>
        <p class="error">{{ error }}</p>
      </form>
    </div>
  </div>
</template>
