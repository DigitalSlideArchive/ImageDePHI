<script setup lang="ts">
defineProps({
  imageRedactionPlan: {
    type: Object,
    required: true,
  },
  usedColumns: {
    type: Array<string>,
    required: true,
  },
});
</script>
<template>
  <div v-if="!usedColumns" class="m-auto flex justify-center">
    Loading.. <span class="loading loading-bars loading-md"></span>
  </div>
  <table v-if="usedColumns" class="table table-auto text-center bg-base-100">
    <thead>
      <tr class="text-base">
        <th class="bg-neutral text-white py-5 px-6">Image File Name</th>
        <th class="bg-gray-600 text-white py-5 px-10">Image</th>
        <th class="bg-gray-600 text-white">Redaction Status</th>
        <th
          v-if="Object.keys(imageRedactionPlan.data).includes('missing_tags')"
          class="bg-gray-600 text-white p-4"
        >
          Missing Tags
        </th>
        <th
          v-for="tag in usedColumns"
          :key="tag"
          class="bg-gray-600 text-white py-5 px-6"
        >
          {{ tag }}
        </th>
      </tr>
    </thead>
    <tbody class="text-base bg-base-100">
      <tr
        v-for="(image, index) in imageRedactionPlan.data"
        :key="index"
        class="h-[125px]"
      >
        <th>{{ index }}</th>
        <td>
          <img :src="image.thumbnail" class="w-20 h-20" />
        </td>
        <td>
          <div
            v-if="image.missing_tags"
            class="tooltip tooltip-right"
            :data-tip="`${image.missing_tags.length} tag(s) missing redaction rules.`"
          >
            <i class="ri-error-warning-fill text-red-600 text-xl"></i>
            <div v-for="(obj, pos) in image.missing_tags" :key="pos">
              <span v-for="(value, key) in obj" :key="key">
                {{ key }}: {{ value }}
              </span>
            </div>
          </div>

          <div
            v-else
            class="tooltip tooltip-right"
            :data-tip="`No missing redaction rules.`"
          >
            <i class="ri-checkbox-circle-fill text-green-600 text-xl"></i>
          </div>
        </td>
        <template v-for="tag in usedColumns" :key="tag">
          <td class="text-ellipsis overflow-hidden max-w-[300px]">
            <span
              v-if="image[tag]"
              :class="
                image[tag].action === 'delete'
                  ? 'line-through text-accent font-bold decoration-2'
                  : ''
              "
            >
              <span v-if="image[tag].binary">
                {{ image[tag].binary.bytes }} bytes
                <span>
                  {{ image[tag].binary.value.slice(0, 32) }}
                </span>
              </span>
              <span v-else>
                {{
                  typeof image[tag].value === "object"
                    ? image[tag].value.join(", ")
                    : image[tag].value
                }}
              </span>
            </span>
          </td>
        </template>
      </tr>
    </tbody>
  </table>
</template>
<style scoped>
thead th:first-child {
  position: sticky;
  left: 0;
  z-index: 2;
  background-color: #201c35;
}
thead th {
  position: sticky;
  top: 0;
  z-index: 1;
}

tbody th {
  position: relative;
}
tbody th:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
  background-color: #ffffff;
}
</style>
