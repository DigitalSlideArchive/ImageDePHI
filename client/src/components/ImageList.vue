<script setup lang="ts">
import { ref, computed } from "vue";
import { getRedactionPlan } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";
import { imageRedactionPlan } from "../store/imageStore";
import ImageDataTable from "./ImageDataTable.vue";

const page = ref(1);
const rows = ref(10);
const totalPages = computed(() =>
  Math.ceil(imageRedactionPlan.value.total / rows.value),
);

const updateImageList = async () => {
  const limit = rows.value;
  const offset = (page.value - 1) * limit;
  imageRedactionPlan.value = await getRedactionPlan(
    selectedDirectories.value.inputDirectory,
    rows.value,
    offset,
    false,
  );
};
</script>

<template>
  <div class="container ml-4 my-4 flex flex-col w-full">
    <div class="w-full max-w-7xl">
      <div
        v-if="!imageRedactionPlan.total"
        class="m-auto h-full flex justify-center"
      >
        Loading.. <span class="loading loading-bars loading-md"></span>
      </div>
      <div
        v-for="(image, index) in imageRedactionPlan.data"
        :key="index"
        class="collapse collapse-arrow bg-base-100 rounded-none border border-base-300 w-full"
      >
        <input type="checkbox" />
        <div class="collapse-title text-xl font-medium">
          {{ index }}
          <div
            v-if="!image.missing_tags"
            class="tooltip tooltip-right z-50 w-min"
            data-tip="Ready to redact."
          >
            <i class="ri-checkbox-circle-fill text-green-600"></i>
          </div>
          <div
            v-else-if="image.missing_tags.length > 0"
            class="tooltip tooltip-right z-50 w-min"
            :data-tip="`${image.missing_tags.length} tag(s) missing redaction rules.`"
          >
            <i class="ri-error-warning-fill text-red-600"></i>
          </div>
        </div>
        <div class="collapse-content overflow-x-auto">
          <ImageDataTable :image-data="image" />
        </div>
      </div>
    </div>
    <div v-if="totalPages && totalPages > 1" class="join flex justify-center">
      <button
        class="join-item btn btn-base-100 btn-xs"
        :disabled="page === 1"
        @click="page--, updateImageList()"
      >
        <i class="ri-arrow-left-s-line"></i>
      </button>
      <input
        v-model="page"
        class="join-item px-0 input input-bordered input-xs w-10 text-center"
        @input="updateImageList()"
      />
      /
      {{ totalPages }}
      <button
        class="join-item btn btn-base-100 btn-xs"
        :disabled="page === totalPages"
        @click="page++, updateImageList()"
      >
        <i class="ri-arrow-right-s-line"></i>
      </button>
    </div>
  </div>
</template>
