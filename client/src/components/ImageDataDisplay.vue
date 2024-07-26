<script setup lang="ts">
import { computed, ref } from "vue";
import { useRedactionPlan } from "../store/imageStore";
import { getImages, getRedactionPlan } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";
import ImageDataTable from "./ImageDataTable.vue";
import InfiniteScroller from "./InfiniteScroller.vue";

const limit = ref(50);
const offset = ref(1);


const loadImagePlan = async () => {
  const newPlan = await getRedactionPlan(
    selectedDirectories.value.inputDirectory,
    limit.value,
    offset.value,
    false,
  );
  useRedactionPlan.imageRedactionPlan.data = {
    ...useRedactionPlan.imageRedactionPlan.data,
    ...newPlan.data,
  };
  getThumbnail(newPlan.data);
  ++offset.value;
};
const usedColumns = computed(() => useRedactionPlan.imageRedactionPlan.tags);
const getThumbnail = async (
  imagedict: Record<string, Record<string, string>>,
) => {
  Object.keys(imagedict).forEach(async (image) => {
    const response = await getImages(
      selectedDirectories.value.inputDirectory + "/" + image,
      "thumbnail",
    );
    if (response.status >= 400) {
      useRedactionPlan.imageRedactionPlan.data[image].thumbnail =
        "/thumbnailPlaceholder.svg";
      return;
    }
    if (response.body) {
      const reader = response.body.getReader();
      const chunks = [];
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }
      const blob = new Blob(chunks);
      const url = URL.createObjectURL(blob);
      useRedactionPlan.imageRedactionPlan.data[image].thumbnail = url;
    }
  });
};
getThumbnail(useRedactionPlan.imageRedactionPlan.data);
</script>

<template>
  <div class="card m-4 pb-4 rounded">
    <InfiniteScroller @infinite-scroll="loadImagePlan">
      <ImageDataTable
        :used-columns="usedColumns"
        :image-redaction-plan="useRedactionPlan.imageRedactionPlan"
      />
    </InfiniteScroller>
  </div>
</template>
