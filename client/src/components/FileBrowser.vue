<script setup lang="ts">
import { ref, Ref } from "vue";
import { getDirectoryInfo } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";
import { useRedactionPlan } from "../store/imageStore";
import { DirectoryData } from "../store/types";

const props = defineProps({
  modalId: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
});

const modal = ref();
defineExpose({ modal });
defineEmits(["update-image-list"]);

const directoryData: Ref<DirectoryData> = ref({
  directory: "",
  ancestors: [],
  children: [],
  childrenImages: [],
});

const updateDirectories = async (currentDirectory?: string) => {
  const data = await getDirectoryInfo(currentDirectory);
  directoryData.value = await {
    ...data,
    children: data.child_directories,
    childrenImages: data.child_images,
  };
};
updateDirectories();

const closeModal = () => {
  modal.value.close();
};

const updateSelectedDirectories = (path: string) => {
  selectedDirectories.value[props.modalId] = path;
};
</script>

<template>
  <dialog :id="modalId" ref="modal" class="modal">
    <div class="w-full max-w-4xl h-4/5 rounded-xl overflow-hidden">
      <div class="modal-box w-full max-w-4xl h-full overflow-auto pt-0">
        <div class="sticky top-0 pt-6 bg-white">
          <div class="flex justify-between">
            <h2 class="text-lg font-semibold">
              {{ title }}
            </h2>
            <button
              class="btn bg-primary float-right text-white uppercase"
              type="button"
              @click="
                $emit('update-image-list'),
                  closeModal(),
                  title === 'Input Directory'
                    ? useRedactionPlan.updateImageData(
                        selectedDirectories['inputDirectory'],
                        50,
                        0,
                        false,
                      )
                    : ''
              "
            >
              Select
            </button>
          </div>
          <div class="text-sm breadcrumbs mb-4 border-b-2">
            <ul class="flex flex-wrap">
              <li
                v-for="(ancestor, index) in directoryData.ancestors"
                :key="index"
                class="mr-1 text-base"
              >
                <span
                  v-if="index === directoryData.ancestors.length - 1"
                  class="font-black"
                  >{{ ancestor.name ? ancestor.name : "/" }}</span
                >
                <a
                  v-else
                  class="text-blue-700"
                  @click="
                    updateDirectories(ancestor.path),
                      updateSelectedDirectories(ancestor.path)
                  "
                >
                  {{ ancestor.name ? ancestor.name : "/" }}
                </a>
              </li>
            </ul>
          </div>
        </div>
        <ul class="text-blue-700">
          <li
            v-for="child in directoryData.children.sort((a, b) => {
              const folder1 = a.name.toLowerCase();
              const folder2 = b.name.toLowerCase();
              if (folder1 < folder2) {
                return -1;
              }
              if (folder1 > folder2) {
                return 1;
              }
              return 0;
            })"
            :key="child.path"
            class="hover:bg-base-300 cursor-default py-0.5"
            @click="
              updateDirectories(child.path),
                updateSelectedDirectories(child.path)
            "
          >
            <i class="ri-folder-3-fill text-neutral"></i>
            {{ child.name }}
          </li>
        </ul>
        <ul class="pl-2">
          <li
            v-for="child_image in directoryData.childrenImages.slice(0, 10)"
            :key="child_image.path"
            class="py-0.5"
          >
            <i class="ri-image-fill text-sky-800"></i>
            {{ child_image.name }}
          </li>
          <li v-if="directoryData.childrenImages.length > 10" class="italic">
            {{ directoryData.childrenImages.length - 10 }} More Images
          </li>
        </ul>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop w-screen h-screen absolute">
      <button>close</button>
    </form>
  </dialog>
</template>
