<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
import { BlockEditor, EditorProvider, exportDocumentToMarkdown, parseMarkdownDocument, type EditorAiOptions, type TiptapDocumentJson } from '@my-notebook/vue-block-editor/editor';
import { parseEditorContentJson, serializeEditorContent } from '@my-notebook/vue-block-editor/core';
import '@my-notebook/vue-block-editor/style.css';
import { api } from '@/services/api';
import { createAdminAiCompletion } from '@/services/ai';
const props = withDefaults(defineProps<{ modelValue: string; contentJson?: string; disabled?: boolean; height?: string | number; label?: string }>(), { label: '正文编辑器' });
const emit = defineEmits<{ 'update:modelValue': [value: string]; 'update:contentJson': [value: string] }>();
function parseContent() {
  if (props.contentJson) {
    try { return parseEditorContentJson(props.contentJson); } catch { /* Recover legacy Markdown. */ }
  }
  return parseMarkdownDocument(props.modelValue || '').content;
}
const content = ref<TiptapDocumentJson>(parseContent());
let lastMarkdown = props.modelValue || '';
let lastJson = props.contentJson || '';
let revision = 0;
const editorAi = shallowRef<EditorAiOptions>();
async function updateContent(value: TiptapDocumentJson) {
  const current = ++revision;
  content.value = value;
  lastJson = serializeEditorContent(value);
  emit('update:contentJson', lastJson);
  const markdown = await exportDocumentToMarkdown(value, { title: '', includeTitle: false });
  if (current !== revision) return;
  if (markdown !== lastMarkdown) { lastMarkdown = markdown; emit('update:modelValue', markdown); }
}
watch(() => [props.modelValue, props.contentJson], () => {
  if (props.modelValue === lastMarkdown && (props.contentJson || '') === lastJson) return;
  revision++;
  lastMarkdown = props.modelValue || '';
  lastJson = props.contentJson || '';
  content.value = parseContent();
});
onBeforeUnmount(() => { revision++; });
onMounted(async () => {
  try {
    const settings = (await api.get<{ ai_configured: boolean }>('/admin/oauth/settings')).data;
    if (settings.ai_configured) editorAi.value = { complete: createAdminAiCompletion() };
  } catch { /* Non-admin and public editors simply omit the AI widget. */ }
});
</script>
<template>
  <div class="course-block-editor" :style="{ height: typeof height === 'number' ? `${height}px` : height, minHeight: height ? undefined : '520px' }">
    <EditorProvider>
      <BlockEditor :model-value="content" :readonly="disabled === true" :ai="editorAi" :aria-label="label" @update:model-value="updateContent" />
    </EditorProvider>
  </div>
</template>
<style scoped>
.course-block-editor { min-width:0; width:100%; }
.course-block-editor :deep(.editor-shell) { height:100%; min-height:0; }
.course-block-editor :deep(.editor-shell__content) {
  width:100%;
  max-width:none;
  box-sizing:border-box;
  padding:36px clamp(24px, 4vw, 64px) 96px;
  line-height:1.72;
}
</style>
