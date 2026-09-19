<script setup lang="ts">
import { ref } from 'vue';
defineProps<{ title: string }>();
const expanded = ref<string[]>([]);
</script>

<template>
  <el-collapse v-model="expanded" class="content-disclosure">
    <el-collapse-item name="content" :title="title">
      <div v-if="expanded.includes('content')" class="disclosure-body"><slot /></div>
    </el-collapse-item>
  </el-collapse>
</template>
