<script setup lang="ts">
import { renderMarkdown } from "@/services/markdown";
import { computed } from "vue";

const props = defineProps<{ source: string }>();
const html = computed(() =>
  renderMarkdown(props.source),
);
</script>

<template><article class="markdown-body" v-html="html" /></template>
