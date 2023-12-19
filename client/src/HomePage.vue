<template>
<div class="flex">
    <input type="checkbox" class="drawer-toggle" id="side-drawer" />
    <div class="flex max-w-md">
        <div class="pl-4 py-4 {{ 'opacity-50' if redacted==True  }}">
            <div class="bg-base-100 drop-shadow-xl rounded flex flex-col">
              <div class="flex justify-between content-center p-4 border-b">
                <div class="max-h6 w-auto self-center">

                  <img src="src/assets/logo.png" />
                </div>
                <div class="flex items-center space-y-0.5">
                  <a class="btn btn-ghost btn-square btn-sm">
                    <i class="ri-side-bar-line text-lg text-neutral"></i>
                  </a>
                </div>
              </div>
              <MenuSteps
              :step-number=1
              step-title="Input Directory"
              help-text="Location of the images you’d like to process."
              :inputModal="inputModal"
              />
              <MenuSteps
              :step-number=2
              step-title="Output Directory"
              help-text="Location of the images after they are processed."
              :outputModal="outputModal"
              />
                <FileBrowser  :modalId="'inputDirectory'" :title="'Input Directory'" ref="inputModal"/>

                <FileBrowser :modalId="'outputDirectory'" :title="'Output Directory'" ref='outputModal'/>
           <!-- TODO disable on redact -->
              <button type="submit" class="btn btn-wide bg-accent m-auto" id="dephi">De-phi
                images
              </button>
            </div>
          </div>
    </div>

</div>
</template>
<script setup lang="ts">
import MenuSteps from './components/MenuSteps.vue';
import FileBrowser from './components/FileBrowser.vue';
import { ref } from 'vue';
const inputModal = ref(null);
const outputModal = ref(null);

</script>
