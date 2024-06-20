<script setup lang="ts">
import { computed, ref } from "vue";
import { rules, fetchRulesData } from "../store/rulesStore";
import { imageRedactionPlan } from "../store/imageStore";
import { getImages, getRedactionPlan } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";
import ImageDataTable from "./ImageDataTable.vue";
import InfiniteScroller from "./InfiniteScroller.vue";


const limit = ref(50);
const offset = ref(1);
const columnsComputed = ref(false);

const loadImagePlan = async () => {
  const newPlan = await getRedactionPlan(
    selectedDirectories.value.inputDirectory,
    limit.value,
    offset.value,
    false,
  );
  console.log('more images')
  imageRedactionPlan.value.data = {...imageRedactionPlan.value.data, ...newPlan.data};
  console.log(imageRedactionPlan.value.data);
  ++offset.value;
};



fetchRulesData();
const ruleList = computed(() => new Set(rules.value));

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const toggleEmptyColumns = (imageList: Array<any>) => {
  const usedColumns = new Set();
  for (const image of imageList) {
    for (const tag of ruleList.value) {
      if (Object.keys(image).includes('missing_tags')) {
        usedColumns.add('Missing Tags');
      }
      if (Object.keys(image).includes(tag)) {
        usedColumns.add(tag);
      }
    }
  }
  columnsComputed.value = true;
  return usedColumns;
};
const usedColumns = computed(() =>
  toggleEmptyColumns(Object.values(imageRedactionPlan.value.data)),
);


const getThumbnail = async () => {
  Object.keys(imageRedactionPlan.value.data).forEach(async (image) => {
    const response = await getImages(selectedDirectories.value.inputDirectory + '/' + image, "thumbnail");
    if (response.status == 404) {
      imageRedactionPlan.value.data[image].thumbnail = "/thumbnailPlaceholder.svg";
      return;
    }
    const reader = response.body.getReader();
    const chunks = [];
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    const blob = new Blob(chunks);
    const url = URL.createObjectURL(blob);
    imageRedactionPlan.value.data[image].thumbnail = url;
  });

};
getThumbnail();

</script>

<template>
  <div class="card m-4 pb-4 rounded" >
    <InfiniteScroller @infinite-scroll="loadImagePlan">
      <ImageDataTable :columns-computed="columnsComputed" :used-columns="usedColumns" :image-redaction-plan="imageRedactionPlan" />
    </InfiniteScroller>
  </div>
</template>
