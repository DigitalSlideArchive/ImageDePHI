<script setup lang="ts">
import { computed, ref } from "vue";
import { useRedactionPlan } from "../store/imageStore";
import { getRedactionPlan } from "../api/rest";
import ImageDataTable from "./ImageDataTable.vue";
import InfiniteScroller from "./InfiniteScroller.vue";


const limit = ref(50);
const offset = ref(1);

const loadImagePlan = async () => {
  if (
    useRedactionPlan.imageRedactionPlan.total <
    (offset.value + 1) * limit.value
  ) {
    return;
  }
  const newPlan = await getRedactionPlan(
    useRedactionPlan.currentDirectory,
    limit.value,
    offset.value,
    true,
  );
  useRedactionPlan.imageRedactionPlan.data = {
    ...useRedactionPlan.imageRedactionPlan.data,
    ...newPlan.data,
  };
  useRedactionPlan.getThumbnail(newPlan.data);
  ++offset.value;
};
const usedColumns = computed(() => useRedactionPlan.imageRedactionPlan.tags);

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
