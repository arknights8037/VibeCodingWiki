<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";
import SkillPublisher from "@/components/SkillPublisher.vue";

const router = useRouter();

function back() {
  void router.push("/skills");
}

async function saved() {
  await router.push({ path: "/skills", query: { tab: "mine" } });
}
</script>

<template>
  <div class="page skill-create-page">
    <div class="skill-create-backbar">
      <el-button :icon="ArrowLeft" text @click="back">返回 Skills</el-button>
    </div>
    <header class="skill-create-heading">
      <p class="eyebrow">SKILL WORKSPACE</p>
      <h1>创建 Skill 资源</h1>
      <p>上传已有 Skill 包，或在线编写一个新的资源。保存后可在“我的 Skills”中继续管理。</p>
    </header>
    <section class="form-panel skill-create-panel" aria-label="创建 Skill 资源">
      <SkillPublisher @saved="saved" />
    </section>
  </div>
</template>

<style scoped>
.skill-create-page { max-width: 920px; margin: 0 auto; }
.skill-create-backbar { margin-bottom: 18px; }
.skill-create-heading { margin: 0 0 24px; }
.skill-create-heading h1 { margin: 4px 0 8px; font-size: 28px; line-height: 1.3; }
.skill-create-heading p:last-child { max-width: 620px; margin: 0; color: var(--docs-muted); line-height: 1.7; }
.skill-create-panel { padding: 24px; border: 1px solid var(--docs-border); border-radius: 10px; background: var(--docs-bg); }
@media (max-width: 600px) {
  .skill-create-heading h1 { font-size: 24px; }
  .skill-create-panel { padding: 16px; }
}
</style>
