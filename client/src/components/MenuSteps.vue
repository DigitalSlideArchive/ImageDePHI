<template>
  <div class="w-96 pt-2.5 bg-white flex-col justify-start items-start inline-flex">
    <div class="self-stretch px-4 py-3 bg-white justify-start items-center gap-2.5 inline-flex">
      <div class="w-6 h-6 bg-rose-100 rounded-[100px] justify-center items-center flex">
        <div class="w-6 h-6 text-red-400 text-sm font-semibold flex flex-wrap justify-center content-center">
          {{ stepNumber }}
        </div>
      </div>
      <div class="grow shrink basis-0">
        <div class="grow shrink basis-0 flex flex-col">
          <span class="text-purple-900 text-sm font-semibold uppercase tracking-widest">
            {{ stepTitle }}
          </span>
          <span class="text-gray-500 text-xs font-normal tracking-wide">
            {{ helpText }}
          </span>
        </div>
      </div>
        <button class="btn btn-ghost btn-square btn-sm" @click="openModal">
      <i class="ri-folder-open-fill text-secondary text-lg"></i>  </button>

    </div>
    <div class="self-stretch h-[74px] px-5 pb-10 bg-white border-b border-neutral-200 flex-col justify-start flex">
      <div v-if="stepTitle?.includes('Input') && selectedDirectories.inputDirectory" class="text-left text-gray-500 text-[14px] font-bold break-all pl-8">
        {{ selectedDirectories.inputDirectory }}
      </div>
      <div v-else-if="stepTitle?.includes('Output') && selectedDirectories.outputDirectory" class="text-left text-gray-500 text-[14px] font-bold break-all pl-8">
        {{ selectedDirectories.outputDirectory }}
       </div>
       <div v-else class="text-left text-gray-500 text-[14px] font-bold break-all pl-8">
        No directory selected
        </div>
    </div>

  </div>
</template>
<script setup lang="ts">
import { selectedDirectories } from '../store/directoryStore';
const props = defineProps({
  stepNumber: Number,
  stepTitle: String,
  helpText: String,
  inputModal: null,
  outputModal: null,
});

const openModal = () => {
    props.stepTitle == "Input Directory" ? props.inputModal.modal.showModal() : props.outputModal.modal.showModal();
};
</script>
