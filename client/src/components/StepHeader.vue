<script setup lang="ts">
defineProps<{
  stepNumber: number;
  title: string;
  helpText?: string;
}>();
</script>

<template>
  <div class="self-stretch px-4 py-3 bg-white justify-start items-center gap-2.5 inline-flex border-b border-neutral-100">
    <div class="w-6 h-6 bg-rose-200 rounded-[100px] justify-center items-center flex">
      <div class="w-6 h-6 text-red-400 text-sm font-semibold flex flex-wrap justify-center content-center">
        {{ stepNumber }}
      </div>
    </div>
    <div class="grow shrink basis-0">
      <div class="grow shrink basis-0 flex flex-col">
        <span class="text-purple-900 text-sm font-semibold uppercase tracking-widest">
          {{ title }}
        </span>
        <span v-if="helpText" class="text-gray-500 text-xs font-normal tracking-wide">
          {{ helpText }}
        </span>
      </div>
    </div>
  </div>
</template>