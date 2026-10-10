<script setup lang="ts">
import ShellLayout from "@/layouts/ShellLayout.vue";
import { useRoute } from "vue-router";
const route = useRoute();
</script>

<template><RouterView v-if="route.meta.review || route.meta.standalone" :key="route.path" /><ShellLayout v-else /></template>
