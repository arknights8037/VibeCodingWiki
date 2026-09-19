<template>
  <div class="content-edit-layout">
    <section class="content-writing-area" aria-label="正文编辑区"><slot /></section>
    <aside class="content-properties" aria-label="条目属性与操作">
      <div class="properties-actions"><slot name="actions" /></div>
      <el-scrollbar class="properties-scroll" max-height="calc(100dvh - 220px)"><div class="properties-form"><slot name="properties" /></div></el-scrollbar>
    </aside>
  </div>
</template>
<style scoped>
.content-edit-layout { display:grid; grid-template-columns:minmax(0,1fr) 300px; gap:20px; align-items:start; }
.content-writing-area { min-width:0; }
.content-writing-area :deep(.course-markdown-editor) { min-height:520px; border-radius:6px; overflow:hidden; }
.content-writing-area :deep(.vditor-reset) { padding:24px 28px !important; line-height:1.9; }
.content-properties { min-width:0; border:1px solid #e5e5e2; border-radius:6px; background:#fafaf8; position:sticky; top:82px; }
.properties-actions { display:flex; flex-wrap:wrap; gap:8px; padding:14px; border-bottom:1px solid #e5e5e2; }
.properties-actions :deep(.el-button) { margin:0; }
.properties-actions :deep([role=status]) { width:100%; font-size:12px; color:#827d70; }
.properties-form { padding:16px 14px; }
.properties-form :deep(.el-select) { width:100%; }
@media(max-width:900px) {
  .content-edit-layout { grid-template-columns:minmax(0,1fr); }
  .content-properties { position:static; }
  .properties-scroll :deep(.el-scrollbar__wrap) { max-height:none !important; }
  .content-writing-area :deep(.course-markdown-editor) { height:60dvh !important; min-height:380px; }
  .content-writing-area :deep(.vditor-reset) { padding:18px !important; }
}
</style>
