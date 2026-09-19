<script setup lang="ts">
defineOptions({ inheritAttrs: false });
withDefaults(defineProps<{ data: unknown[]; rowKey?: string; emptyText?: string }>(), { rowKey: 'id', emptyText: '暂无数据' });
</script>
<template>
  <el-table v-bind="$attrs" :data="data" :row-key="rowKey" :empty-text="emptyText" class="admin-list-table"><slot /></el-table>
</template>
<style scoped>
.admin-list-table { width:100%; margin-bottom:24px; font-size:13px; --el-table-border-color:#eeeeea; --el-table-header-bg-color:#fafaf8; --el-table-row-hover-bg-color:#fafaf8; }
.admin-list-table :deep(th.el-table__cell) { color:#77746b; font-weight:600; }
.admin-list-table :deep(.el-table__cell) { padding:10px 0; }
.admin-list-table :deep(.cell) { overflow-wrap:anywhere; }
.admin-list-table :deep(.el-button) { margin:0; height:30px; padding:0 10px; font-size:12px; }
.admin-list-table :deep(.admin-row-actions) { display:flex; flex-wrap:wrap; gap:6px; }
</style>
