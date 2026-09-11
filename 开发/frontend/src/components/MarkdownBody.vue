<script setup lang="ts">
import DOMPurify from "dompurify";
import { marked } from "marked";
import { computed } from "vue";

const props = defineProps<{ source: string }>();
const html = computed(() =>
  DOMPurify.sanitize(marked.parse(props.source) as string),
);
</script>

<template><article class="markdown-body" v-html="html" /></template>
