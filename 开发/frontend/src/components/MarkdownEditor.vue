<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import { BlockEditor, exportDocumentToMarkdown, parseMarkdownDocument, type TiptapDocumentJson } from '@my-notebook/vue-block-editor/editor';
import { parseEditorContentJson, serializeEditorContent } from '@my-notebook/vue-block-editor/core';
import '@my-notebook/vue-block-editor/style.css';
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
</script>
<template><div class="course-block-editor" :style="{ height: typeof height === 'number' ? `${height}px` : height, minHeight: height ? undefined : '520px' }"><BlockEditor :model-value="content" :readonly="disabled" :aria-label="label" @update:model-value="updateContent" /></div></template>
<style scoped>
.course-block-editor { min-width:0; width:100%; border:1px solid var(--line,#e5e5e2); border-radius:8px; overflow:hidden; background:var(--paper,#fff); }
.course-block-editor :deep(.editor-shell) { height:100%; min-height:0; }
.course-block-editor :deep(.editor-shell__content) { padding:24px 28px; line-height:1.9; }
</style>
