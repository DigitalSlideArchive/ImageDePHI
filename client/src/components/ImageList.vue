<script setup lang="ts">
import { imageRedactionPlan } from '../store/imageStore';

Object.keys(imageRedactionPlan.value).filter((key) => {
  if (!imageRedactionPlan.value[key].missing_tags) {
    console.log(imageRedactionPlan.value[key]);
  }
});
</script>

<template>
  <div class="ml-4 my-4 w-full max-w-7xl">
  <div
  v-for="image,index in imageRedactionPlan"
  :key="index"
  class="collapse collapse-arrow bg-base-100 rounded-none border border-base-300 w-full"
  >
  <input type="checkbox" />
  <div class="collapse-title text-xl font-medium">
    {{index}}
    <i v-if="!image.missing_tags" class="ri-checkbox-circle-fill text-green-600"></i>
    <i v-else-if="image.missing_tags.length > 0" class="ri-error-warning-fill text-red-600"></i>

  </div>
  <div class="collapse-content">
    <p>hello</p>
  </div>
</div>
<!-- <div class="collapse collapse-arrow bg-base-100 rounded-none border border-base-300">
  <input type="checkbox" />
  <div class="collapse-title text-xl font-medium">
    Click to open this one and close others
  </div>
  <div class="collapse-content">
    <p>hello</p>
  </div>
</div>
<div class="collapse collapse-arrow bg-base-100 rounded-none border border-base-300">
  <input type="checkbox" />
  <div class="collapse-title text-xl font-medium">
    Click to open this one and close others
  </div>
  <div class="collapse-content">
    <p>hello</p>
  </div>
</div> -->
</div>
  <!-- <div class="overflow-x-auto">
    <table class="table">

      <thead>
        <tr>
          <th></th>
          <th>Name</th>
          <th>Job</th>
          <th>Favorite Color</th>
        </tr>
      </thead>
      <tbody>

        <tr>
          <th>1</th>
          <td>Cy Ganderton</td>
          <td>Quality Control Specialist</td>
          <td>Blue</td>
        </tr>

        <tr>
          <th>2</th>
          <td>Hart Hagerty</td>
          <td>Desktop Support Technician</td>
          <td>Purple</td>
        </tr>

        <tr>
          <th>3</th>
          <td>Brice Swyre</td>
          <td>Tax Accountant</td>
          <td>Red</td>
        </tr>
      </tbody>
    </table>
  </div> -->
</template>
