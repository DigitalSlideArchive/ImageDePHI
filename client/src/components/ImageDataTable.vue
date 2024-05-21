<script setup lang="ts">
import { computed } from "vue";
import { rules, fetchRulesData } from "../store/rulesStore";
import { imageRedactionPlan } from "../store/imageStore";
import { getImages } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";


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

  return usedColumns;
};
const usedColumns = computed(() =>
  toggleEmptyColumns(Object.values(imageRedactionPlan.value.data)),
);


const getThumbnail = async () => {
  Object.keys(imageRedactionPlan.value.data).forEach(async (image) => {
    const response = await getImages(selectedDirectories.value.inputDirectory + '/' + image, "thumbnail");
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
  <div class="card w-full m-4 overflow-auto rounded">
    <div
      v-if="!imageRedactionPlan.total"
      class="m-auto h-full flex justify-center"
    >
      Loading.. <span class="loading loading-bars loading-md"></span>
    </div>
    <table class="table table-auto table-xs w-full table-pin-rows table-pin-cols">
    <thead>
      <tr>
        <th class="bg-neutral text-white">Image</th>
        <th v-if="Object.keys(imageRedactionPlan.data).includes('missing_tags')" class="bg-gray-600 text-white">Missing Tags</th>
        <th v-for="tag in usedColumns" :key="tag" class="bg-gray-600 text-white">
          {{ tag }}
        </th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(image, index) in imageRedactionPlan.data" :key="index">
        <td>
          <img :src="image.thumbnail" class="w-20 h-20" />
        </td>
        <td v-if="Object.keys(image).includes('missing_tags')">
          <div
            v-if="!image.missing_tags"
            class="tooltip tooltip-right z-50 w-min"
            data-tip="Ready to redact."
          >
            <i class="ri-checkbox-circle-fill text-green-600"></i>
          </div>
          <div
            v-else-if="image.missing_tags.length > 0"
            class="tooltip tooltip-right z-50"
            :data-tip="`${image.missing_tags.length} tag(s) missing redaction rules.`"
          >
            <i class="ri-error-warning-fill text-red-600 text-base"></i>
            <td v-for="(obj, index) in image.missing_tags" :key="index">
            <span v-for="(value, key) in obj" :key="key">
              {{ key }}: {{ value }}
              </span>
            </td>
          </div>
        </td>
        <td v-for="tag in usedColumns" :key="tag">
          {{ image[tag] }}
        </td>
        </tr>

    </tbody>
  </table>

  </div>
</template>
