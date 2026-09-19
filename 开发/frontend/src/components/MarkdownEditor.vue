<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, watch } from 'vue';
import Vditor from 'vditor';
import { renderEditorCards } from '@/services/markdown';
import 'vditor/dist/index.css';
const props = withDefaults(defineProps<{ modelValue: string; disabled?: boolean; height?: string | number; label?: string }>(), { label: '课文正文编辑器' });
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const host = ref<HTMLElement>();
let editor: Vditor | undefined;
let ready = false;
let disposed = false;
function destroyEditor() { ready = false; editor?.destroy(); editor = undefined; }
onMounted(() => {
  editor = new Vditor(host.value!, {
    cdn: '/vendor/vditor', lang: 'zh_CN', mode: 'wysiwyg', height: props.height || 460,
    cache: { enable: false }, value: props.modelValue,
    toolbar: ['headings', 'bold', 'italic', 'strike', '|', 'list', 'ordered-list', 'check', 'quote', 'code', 'inline-code', 'link', 'table', { name: 'insert-card', tip: '插入卡片', icon: '<svg><use xlink:href="#vditor-icon-code"></use></svg>', click: () => { if (ready) editor?.insertValue('\n\n```card\n## 卡片标题\n\n在这里写说明、列表或提示。\n```\n\n'); } }, '|', 'undo', 'redo', 'edit-mode'],
    customRenders: [{ language: 'card', render: renderEditorCards }],
    preview: { hljs: { enable: false }, markdown: { sanitize: true } },
    input: value => { if (!disposed) emit('update:modelValue', value); },
    after: () => {
      ready = true;
      if (disposed) { queueMicrotask(destroyEditor); return; }
      editor?.setValue(props.modelValue);
      if (props.disabled) editor?.disabled();
    },
    blur: () => { if (ready && !disposed) emit('update:modelValue', editor!.getValue()); },
  });
});
watch(() => props.modelValue, value => { if (ready && editor?.getValue() !== value) editor?.setValue(value); });
watch(() => props.disabled, disabled => { if (ready) { if (disabled) editor?.disabled(); else editor?.enable(); } });
onBeforeUnmount(() => { disposed = true; if (ready) destroyEditor(); });
</script>
<template><div ref="host" class="course-markdown-editor" :aria-label="label" /></template>
<style>
.course-markdown-editor { min-width:0; width:100%; }
.course-markdown-editor .vditor-reset { font-size:14px; }
.course-markdown-editor .vditor-toolbar { padding:4px 8px !important; }
</style>
