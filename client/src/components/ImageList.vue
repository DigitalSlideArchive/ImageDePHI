<script setup lang="ts">
import { imageRedactionPlan } from '../store/imageStore';

</script>

<template>
  <div class="ml-4 my-4 w-full max-w-7xl">
    <div
      v-for="image,index in imageRedactionPlan.data"
      :key="index"
      class="collapse collapse-arrow bg-base-100 rounded-none border border-base-300 w-full"
    >
    <input type="checkbox" />
    <div class="collapse-title text-xl font-medium">
      {{index}}
      <div v-if="!image.missing_tags" class="tooltip tooltip-right z-50 w-min" data-tip="Ready to redact.">
          <i class="ri-checkbox-circle-fill text-green-600"></i>
      </div>
      <div v-else-if="image.missing_tags.length > 0" class="tooltip tooltip-right z-50 w-min" :data-tip="`${ image.missing_tags.length } tag(s) missing redaction rules.`">
        <i class="ri-error-warning-fill text-red-600"></i>
      </div>

    </div>
    <div class="collapse-content">
      <p>hello</p>
    </div>
  </div>
</div>

</template>
