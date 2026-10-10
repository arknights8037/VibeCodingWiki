<script setup lang="ts">
import { computed, ref } from "vue";
import { Connection, CopyDocument, Link } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const origin = computed(() => window.location.origin);
const knowledgeEndpoint = computed(() => `${origin.value}/api/v1`);
const wikiEndpoint = computed(() => `${knowledgeEndpoint.value}/wiki`);
const mcpEndpoint = computed(() => `${origin.value}/mcp`);
const copied = ref("");

async function copy(label: string, value: string) {
  try {
    await navigator.clipboard.writeText(value);
    copied.value = label;
    ElMessage.success(`${label}已复制`);
    window.setTimeout(() => {
      if (copied.value === label) copied.value = "";
    }, 1800);
  } catch {
    ElMessage.error("复制失败，请手动选择地址");
  }
}
</script>

<template>
  <div class="page tools-page">
    <header class="tools-heading">
      <p class="eyebrow">TOOLBOX</p>
      <h1>工具</h1>
      <p class="lede">把 VibeCodingWiki 的知识库连接到你的应用和智能体。选择一个工具，复制地址后即可开始使用。</p>
    </header>

    <section class="tools-grid" aria-label="工具列表">
      <article id="knowledge-endpoint" class="tool-card">
        <div class="tool-card-icon" aria-hidden="true"><Link /></div>
        <div class="tool-card-body">
          <div class="tool-card-kicker">DATA ENDPOINT</div>
          <h2>知识库数据端点 URL</h2>
          <p>返回当前站点公开数据的接口清单。客户端可以从这里发现知识库列表、词条详情和其他可用资源。</p>
          <div class="tool-url-row">
            <code :title="knowledgeEndpoint">{{ knowledgeEndpoint }}</code>
            <el-button :icon="CopyDocument" @click="copy('知识库端点 URL', knowledgeEndpoint)">{{ copied === '知识库端点 URL' ? '已复制' : '复制 URL' }}</el-button>
          </div>
          <div class="tool-card-actions">
            <el-button tag="a" :href="knowledgeEndpoint" target="_blank" rel="noopener noreferrer" :icon="Link">打开端点</el-button>
            <el-button tag="a" :href="wikiEndpoint" target="_blank" rel="noopener noreferrer" text>直接访问知识库数据</el-button>
          </div>
        </div>
      </article>

      <article id="mcp-operator" class="tool-card">
        <div class="tool-card-icon tool-card-icon-mcp" aria-hidden="true"><Connection /></div>
        <div class="tool-card-body">
          <div class="tool-card-kicker">MODEL CONTEXT PROTOCOL</div>
          <h2>MCP 操作器</h2>
          <p>通过 MCP 客户端访问已发布的知识库、课程、作品和技能。公开服务只读，适合连接支持 MCP 的 AI 应用。</p>
          <div class="tool-url-row">
            <code :title="mcpEndpoint">{{ mcpEndpoint }}</code>
            <el-button :icon="CopyDocument" @click="copy('MCP 地址', mcpEndpoint)">{{ copied === 'MCP 地址' ? '已复制' : '复制 URL' }}</el-button>
          </div>
          <div class="tool-card-actions">
            <el-button tag="a" :href="mcpEndpoint" target="_blank" rel="noopener noreferrer" :icon="Connection">打开 MCP</el-button>
            <span class="tool-readonly-note">公开只读</span>
          </div>
        </div>
      </article>
    </section>

    <section class="tool-usage" aria-labelledby="tool-usage-title">
      <h2 id="tool-usage-title">如何使用</h2>
      <div class="tool-usage-steps">
        <div><span>01</span><p>复制上面的端点地址。</p></div>
        <div><span>02</span><p>在你的 API 客户端或 MCP 客户端中粘贴地址。</p></div>
        <div><span>03</span><p>按客户端提示发现并调用公开资源。</p></div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tools-page { max-width: 980px; }
.tools-heading { max-width: 700px; margin-bottom: 34px; }
.tools-heading h1 { margin-bottom: 10px; }
.tools-heading .lede { margin-bottom: 0; }
.tools-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.tool-card { display: flex; gap: 16px; min-width: 0; padding: 20px; border: 1px solid var(--docs-border); border-radius: 8px; background: var(--docs-bg); transition: border-color .15s, box-shadow .15s; }
.tool-card:hover { border-color: #9ba997; box-shadow: 0 5px 18px #37352f0d; }
.tool-card-icon { display: grid; place-items: center; flex: 0 0 38px; width: 38px; height: 38px; color: #607f98; background: #eef2ee; border-radius: 8px; }
.tool-card-icon-mcp { color: #8b6f52; background: #f3eee7; }
.tool-card-icon :deep(svg) { width: 20px; height: 20px; }
.tool-card-body { min-width: 0; flex: 1; }
.tool-card-kicker { margin-bottom: 6px; color: var(--docs-muted); font-size: 10px; letter-spacing: 1.2px; }
.tool-card h2 { margin: 0 0 8px; font-size: 18px; }
.tool-card p { margin: 0 0 17px; color: var(--docs-muted); font-size: 13px; line-height: 1.8; }
.tool-url-row { display: flex; align-items: center; gap: 8px; min-width: 0; padding: 8px 9px; border: 1px solid var(--docs-border); border-radius: 5px; background: var(--docs-side); }
.tool-url-row code { min-width: 0; flex: 1; overflow: hidden; color: var(--docs-text); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.tool-url-row .el-button { flex-shrink: 0; margin: 0; padding: 5px 7px; font-size: 11px; }
.tool-card-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.tool-card-actions .el-button { margin: 0; min-height: 28px; height: auto; padding: 5px 8px; font-size: 11px; }
.tool-readonly-note { color: var(--docs-muted); font-size: 11px; }
.tool-usage { margin-top: 38px; padding-top: 24px; border-top: 1px solid var(--docs-border); }
.tool-usage h2 { margin: 0 0 18px; font-size: 17px; }
.tool-usage-steps { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.tool-usage-steps div { display: flex; gap: 10px; align-items: flex-start; }
.tool-usage-steps span { color: var(--docs-muted); font-size: 11px; letter-spacing: .8px; }
.tool-usage-steps p { margin: 0; color: var(--docs-muted); font-size: 12px; line-height: 1.75; }
.docs-shell[data-theme='dark'] .tool-card-icon { background: #303930; }
.docs-shell[data-theme='dark'] .tool-card-icon-mcp { background: #3a332b; }
.docs-shell[data-theme='dark'] .tool-card:hover { box-shadow: 0 5px 18px #0004; }
@media (max-width: 760px) {
  .tools-grid, .tool-usage-steps { grid-template-columns: 1fr; }
  .tool-card { padding: 16px; }
}
</style>
