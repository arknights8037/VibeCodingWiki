<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import type { WikiTerm } from '@/services/wikiTerms';

defineProps<{ term: WikiTerm }>();
const emit = defineEmits<{ close: [] }>();
const panel = ref<HTMLElement>();
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); }
}
onMounted(async () => {
  window.addEventListener('keydown', onKeydown);
  await nextTick();
  panel.value?.focus();
});
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown));
</script>

<template>
  <Teleport to="body">
    <aside ref="panel" class="wiki-term-popover" role="dialog" aria-modal="false" aria-labelledby="wiki-term-title" aria-describedby="wiki-term-summary" tabindex="-1">
      <div class="wiki-term-popover-heading">
        <span>知识库 · 术语释义</span>
        <button type="button" aria-label="关闭术语释义" @click="emit('close')">×</button>
      </div>
      <h2 id="wiki-term-title">{{ term.title }}</h2>
      <p id="wiki-term-summary">{{ term.summary || '暂无释义，可前往知识库阅读完整词条。' }}</p>
      <RouterLink class="wiki-term-open" :to="`/wiki/${encodeURIComponent(term.slug)}`">前往知识库 →</RouterLink>
    </aside>
  </Teleport>
</template>

<style scoped>
.wiki-term-popover {
  position: fixed; right: max(24px, env(safe-area-inset-right));
  bottom: max(24px, env(safe-area-inset-bottom)); z-index: 1100;
  width: min(380px, calc(100vw - 32px)); max-height: min(480px, 75dvh);
  overflow: auto; padding: 22px; border: 1px solid var(--line, #d8dee9);
  border-radius: 16px; background: var(--paper, white); color: var(--ink, #101828);
  box-shadow: 0 12px 48px #10182826; overflow-wrap: anywhere;
}
.wiki-term-popover-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; color: var(--muted); font-size: 13px; }
.wiki-term-popover-heading button { background: transparent; color: inherit; border: 0; cursor: pointer; font-size: 24px; width: 32px; height: 32px; }
h2 { margin: 12px 0 8px; font-size: 20px; }
p { margin: 0 0 20px; line-height: 1.75; white-space: pre-wrap; }
.wiki-term-open { display: inline-block; background: var(--blue, #1649ff); color: white; border-radius: 8px; padding: 9px 14px; }
@media (max-width: 480px) { .wiki-term-popover { right: 16px; bottom: max(16px, env(safe-area-inset-bottom)); } }
</style>
