<script setup lang="ts">
import { ref } from "vue";

import { redactImages } from "./api/rest";
import { selectedDirectories } from "./store/directoryStore";
import { imageRedactionPlan } from "./store/imageStore";

import MenuSteps from "./components/MenuSteps.vue";
import FileBrowser from "./components/FileBrowser.vue";
import ImageList from "./components/ImageList.vue";

const inputModal = ref(null);
const outputModal = ref(null);
const redactionModal = ref();
const redacting = ref(false);
const progress = ref({
  count: 0,
  max: imageRedactionPlan.value.total,
});

const wsBase = import.meta.env.VITE_APP_API_URL
  ? new URL(import.meta.env.VITE_APP_API_URL)
  : new URL(import.meta.url);

const ws = new WebSocket("ws:" + wsBase.host + "/ws");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  progress.value = {
    count: data.count || 0,
    max: data.max || imageRedactionPlan.value.total,
  };
};

const redact_images = async () => {
  redacting.value = true;
  redactionModal.value.showModal();
  const response = await redactImages(
    selectedDirectories.value.inputDirectory,
    selectedDirectories.value.outputDirectory,
  );
  if (response.status === 200) {
    redacting.value = false;
  }
};
</script>

<template>
  <div class="flex">
    <input id="side-drawer" type="checkbox" class="drawer-toggle" />
    <div class="flex max-w-md">
      <div :class="`pl-4 py-4 ${redacting ? 'opacity-50' : ''}`">
        <div class="bg-base-100 drop-shadow-xl rounded flex flex-col">
          <div class="flex justify-between content-center p-4 border-b">
            <div class="max-h6 w-auto self-center">
              <img src="/logo.png" />
            </div>
            <div class="flex items-center space-y-0.5">
              <a class="btn btn-ghost btn-square btn-sm">
                <i class="ri-side-bar-line text-lg text-neutral"></i>
              </a>
            </div>
          </div>
          <MenuSteps
            :step-number="1"
            step-title="Input Directory"
            help-text="Location of the images you’d like to process."
            :input-modal="inputModal || undefined"
          />
          <MenuSteps
            :step-number="2"
            step-title="Output Directory"
            help-text="Location of the images after they are processed."
            :output-modal="outputModal || undefined"
          />
          <FileBrowser
            ref="inputModal"
            :modal-id="'inputDirectory'"
            :title="'Input Directory'"
          />
          <FileBrowser
            ref="outputModal"
            :modal-id="'outputDirectory'"
            :title="'Output Directory'"
          />
          <button
            type="submit"
            class="btn btn-wide bg-accent m-auto text-white"
            :disabled="redacting"
            @click="redact_images()"
          >
            De-phi Images
          </button>
        </div>
      </div>
    </div>
    <dialog id="redactionModal" ref="redactionModal" class="modal">
      <div class="modal-box w-96">
        <div class="card">
          <div class="card-body">
            <h2 class="card-title">Redaction in progress:</h2>
            <p>
              Redacting images
              <span class="float-right"
                >{{ progress.count }}/{{ progress.max }}</span
              >
            </p>
            <progress
              v-if="redacting"
              class="progress progress-primary"
              :value="progress.count"
              :max="progress.max"
            ></progress>
          </div>
        </div>
      </div>
    </dialog>
    <ImageList v-if="imageRedactionPlan.total > 0" />
  </div>
</template>
$
