<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { annotateWikiTermElements, type WikiTerm } from '@/services/wikiTerms';
import { renderMarkdown } from '@/services/markdown';
const props = defineProps<{ source: string; contentJson?: string; terms?: WikiTerm[] }>();
const emit = defineEmits<{ termSelect: [term: WikiTerm, trigger: HTMLElement] }>();
const host = ref<HTMLElement>();
const html = computed(() => renderMarkdown(props.source || ''));
function selectTerm(event: MouseEvent) { const button = (event.target as Element).closest<HTMLElement>('button.wiki-term'); const term = props.terms?.find(item => item.slug === button?.dataset.wikiTerm); if (term && button) emit('termSelect', term, button); }
function annotateTerms() {
  if (host.value) annotateWikiTermElements(host.value, props.terms || []);
}
watch(() => props.source, () => void nextTick(annotateTerms)); watch(() => props.terms, () => void nextTick(annotateTerms), { deep:true });
onMounted(() => void nextTick(annotateTerms));
</script>
<template><div ref="host" class="block-renderer-host markdown-body" @click="selectTerm"><article v-html="html" /></div></template>
<style scoped>
.block-renderer-host :deep(.editor-shell__content) { padding:0; line-height:1.9; }
.block-renderer-host :deep(.editor-shell) { height:auto; overflow:visible; }
.block-renderer-host :deep(button.wiki-term) { display:inline; padding:0; border:0; background:transparent; color:var(--blue,#1649ff); font:inherit; cursor:pointer; text-decoration:underline dotted; text-underline-offset:3px; }
.block-renderer-host :deep(button.wiki-term:hover) { text-decoration-style:solid; }
</style>
