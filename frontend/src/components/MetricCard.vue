<template>
  <div
    class="bg-white dark:bg-slate-800/60 rounded-lg p-3 border border-slate-200/80 dark:border-slate-700/50"
  >
    <div class="flex items-start justify-between">
      <div>
        <p class="text-xs text-slate-500 dark:text-slate-400 uppercase tracking-wider">
          {{ label }}
        </p>
        <p class="text-lg font-semibold mt-0.5" :class="statusClass">
          {{ value }}
        </p>
        <p v-if="sublabel" class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
          {{ sublabel }}
        </p>
      </div>
      <div v-if="status" class="w-2 h-2 rounded-full mt-1" :class="dotClass"></div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed } from 'vue';

const props = defineProps<{
  label: string;
  value: string;
  sublabel?: string;
  status?: 'good' | 'warning' | 'bad';
}>();

const statusClass = computed(() => {
  switch (props.status) {
    case 'good':
      return 'text-emerald-600 dark:text-emerald-400';
    case 'warning':
      return 'text-amber-600 dark:text-amber-400';
    case 'bad':
      return 'text-red-600 dark:text-red-400';
    default:
      return 'text-slate-700 dark:text-slate-300';
  }
});

const dotClass = computed(() => {
  switch (props.status) {
    case 'good':
      return 'bg-emerald-500';
    case 'warning':
      return 'bg-amber-500';
    case 'bad':
      return 'bg-red-500';
    default:
      return 'bg-slate-400';
  }
});
</script>
