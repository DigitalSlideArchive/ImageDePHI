<script setup lang="ts">
import { ref } from "vue";

import { redactImages } from "./api/rest";
import { selectedDirectories } from "./store/directoryStore";
import { useRedactionPlan } from "./store/imageStore";

import MenuSteps from "./components/MenuSteps.vue";
import FileBrowser from "./components/FileBrowser.vue";
import ImageDataDisplay from "./components/ImageDataDisplay.vue";

const inputModal = ref(null);
const outputModal = ref(null);
const rulesetModal = ref(null);
const redactionModal = ref();
const redacting = ref(false);
const redactionComplete = ref(false);
const showImageTable = ref(false);
const redactionSnackbar = ref(false);

const progress = ref({
  count: 0,
  max: useRedactionPlan.imageRedactionPlan.total,
  redact_dir: "",
});

const wsBase = import.meta.env.VITE_APP_API_URL
  ? new URL(import.meta.env.VITE_APP_API_URL)
  : new URL(import.meta.url);

const ws = new WebSocket("ws:" + wsBase.host + "/ws");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  progress.value = {
    count: data.count || progress.value.count, // don't update if not present
    max: useRedactionPlan.imageRedactionPlan.total,
    redact_dir: data.redact_dir || progress.value.redact_dir, // don't update if not present
  };
};
// Periodically ping the websocket

setInterval(() => {
  if (ws.readyState === ws.OPEN) {
  ws.send("ping");
}
}, 5000);

const redact_images = async () => {
  if (!selectedDirectories.value.inputDirectory || !selectedDirectories.value.outputDirectory) {
    return;
  }
  redacting.value = true;
  // Reset progress count
  progress.value.count = 0;
  redactionModal.value.showModal();
  const response = await redactImages(
    selectedDirectories.value.inputDirectory,
    selectedDirectories.value.outputDirectory,
    selectedDirectories.value.rulesetDirectory
  );
  if (response.status === 200) {
    useRedactionPlan.updateImageData({
      directory:`${selectedDirectories.value.outputDirectory}/${progress.value.redact_dir}`,
      rules:selectedDirectories.value.rulesetDirectory,
      limit: 50,
      offset: 0,
      update: false,}
    );
    redacting.value = false;
    redactionModal.value.close();
    redactionComplete.value = !!useRedactionPlan.imageRedactionPlan.total;
    redactionSnackbar.value = true;
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
          <MenuSteps
            :step-number="3"
            step-title="Rulesets"
            help-text="Custom ruleset to be used for redaction in addition to the baserules."
            :ruleset-modal="rulesetModal || undefined"
          />
          <FileBrowser
            ref="inputModal"
            :modal-id="'inputDirectory'"
            :title="'Input Directory'"
            @update-image-list="showImageTable = true, redactionComplete = false"
          />
          <FileBrowser
            ref="outputModal"
            :modal-id="'outputDirectory'"
            :title="'Output Directory'"
          />
          <FileBrowser
            ref="rulesetModal"
            :modal-id="'rulesetDirectory'"
            :title="'Ruleset Directory'"
            />
          <div class="p-4 w-full">
            <button
              type="submit"
              :class="`${!selectedDirectories.inputDirectory || !selectedDirectories.outputDirectory ? 'btn btn-block bg-accent text-white uppercase rounded-lg tooltip' : 'btn btn-block btn-accent text-white uppercase rounded-lg'}`"
              data-tip="Please select input and output directories"
              @click="redact_images()"
            >
              De-phi Images
            </button>
          </div>
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
    <ImageDataDisplay
      v-if="useRedactionPlan.imageRedactionPlan.total && showImageTable"
    />
    <div v-if="redactionComplete">
      <ImageDataDisplay />
    </div>
    <div v-if="redactionSnackbar" class="toast">
      <div class="alert alert-success">
        <span class="font-semibold">Redaction Complete</span>
        <div>
          Redacted images now in {{ selectedDirectories.outputDirectory }}/{{
            progress.redact_dir
          }}
          <button
            class="btn btn-xs btn-ghost"
            @click="redactionSnackbar = false"
          >
            <i class="ri-close-line"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
