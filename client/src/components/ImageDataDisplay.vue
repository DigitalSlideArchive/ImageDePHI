<script setup lang="ts">
import { computed, ref } from "vue";
import { imageRedactionPlan } from "../store/imageStore";
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
  imageRedactionPlan.value.data = {
    ...imageRedactionPlan.value.data,
    ...newPlan.data,
  };
  getThumbnail(newPlan.data);
  ++offset.value;
};

const usedColumns = computed(() => imageRedactionPlan.value.tags);

const getThumbnail = async (
  imagedict: Record<string, Record<string, string>>,
) => {
  Object.keys(imagedict).forEach(async (image) => {
    const response = await getImages(
      selectedDirectories.value.inputDirectory + "/" + image,
      "thumbnail",
    );
    if (response.status == 404) {
      imageRedactionPlan.value.data[image].thumbnail =
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
      imageRedactionPlan.value.data[image].thumbnail = url;
    }
  });
};
getThumbnail(imageRedactionPlan.value.data);
</script>

<template>
  <div class="card m-4 pb-4 rounded">
    <InfiniteScroller @infinite-scroll="loadImagePlan">
      <ImageDataTable
        :used-columns="usedColumns"
        :image-redaction-plan="imageRedactionPlan"
      />
    </InfiniteScroller>
  </div>
</template>
