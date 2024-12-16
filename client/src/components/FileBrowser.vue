<script setup lang="ts">
import { ref, Ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { getDirectoryInfo } from "../api/rest";
import { selectedDirectories } from "../store/directoryStore";
import { useRedactionPlan, updateTableData } from "../store/imageStore";
import { redactionStateFlags } from "../store/redactionStore";
import { DirectoryData, Path } from "../store/types";

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
  childrenYaml: [],
});

const loadingData = ref(false);

const updateDirectories = async (currentDirectory?: string) => {
  directoryData.value.children = [];
  directoryData.value.childrenImages = [];
  directoryData.value.childrenYaml = [];
  const timeout = setTimeout(() => {
    loadingData.value = true;
  }, 100);

  const data = await getDirectoryInfo(currentDirectory);
  clearTimeout(timeout);
  loadingData.value = false;
  directoryData.value = await {
    ...data,
    children: data.child_directories,
    childrenImages: data.child_images,
    childrenYaml: data.child_yaml_files,
  };
  loadingData.value = false;
  calculateVisibleItems();
};
updateDirectories();

const closeModal = () => {
  modal.value.close();
};

const updateSelectedDirectories = (path: string) => {
  selectedDirectories.value[props.modalId] = path;
  localStorage.setItem('inputDirectory', selectedDirectories.value.inputDirectory);
  localStorage.setItem('outputDirectory', selectedDirectories.value.outputDirectory);
  localStorage.setItem('rulesetDirectory', selectedDirectories.value.rulesetDirectory);
};

const visibleImages: Ref<Path[]> = ref([]);
const remainingImages = ref(0);

const calculateVisibleItems = () => {
  const menuTop = document.querySelector(".menu-top");
  const listContainer = document.querySelector(".list-container");
  // Determine and set the height of the list container
  listContainer?.setAttribute(
    "style",
    `height: calc(100% - (${menuTop?.clientHeight}px + 3.5rem))`,
  );

  nextTick(() => {
    const listItems = listContainer?.querySelectorAll("li");
    const containerHeight = listContainer?.clientHeight;
    const listHeight = ref(0);
    const visibleItems = ref(0);
    // Determine the height of each list item
    const listItemHeight = listItems && listItems[0] ? listItems[0].clientHeight : 0;

    directoryData.value.childrenImages.forEach(() => {
      listHeight.value += listItemHeight;
      if (containerHeight && listHeight.value < containerHeight) {
        visibleItems.value += 1;
      }
    });

    visibleImages.value = directoryData.value.childrenImages.slice(
      0,
      visibleItems.value,
    );
    remainingImages.value =
      directoryData.value.childrenImages.length - visibleItems.value;
  });
};
onMounted(() => {
  calculateVisibleItems();
  window.addEventListener("resize", calculateVisibleItems);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", calculateVisibleItems);
});
</script>

<template>
  <dialog :id="modalId" ref="modal" class="modal">
    <div class="w-full max-w-4xl h-4/5 rounded-xl overflow-hidden">
      <div class="modal-box w-full max-w-4xl h-4/5 overflow-auto pt-0">
        <div class="sticky top-0 pt-6 bg-white menu-top">
          <div class="flex justify-between">
            <h2 class="text-lg font-semibold">
              {{ title }}
            </h2>
            <button
              class="btn btn-primary float-right text-white uppercase"
              type="button"
              @click="
                $emit('update-image-list'),
                  closeModal(),
                  title !== 'Output Directory' ? updateTableData() : ''
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
        <div
          v-if="loadingData"
          class="text-center"
        >
          <span class="loading loading-spinner text-primary"></span>
          <span class="ml-2 italic font-light align-top"
            >Collecting Directory Data</span
          >
        </div>
        <div class="list-container">
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
          <div class="list-container">
            <ul class="pl-2">
              <template v-if="modalId !== 'rulesetDirectory'">
                <li
                  v-for="child_image in visibleImages"
                  :key="child_image.path"
                  class="py-0.5"
                >
                  <i class="ri-image-fill text-sky-800"></i>
                  {{ child_image.name }}
                </li>
                <li
                  v-if="directoryData.childrenImages.length > 10"
                  class="italic"
                >
                  {{ remainingImages }} More Images
                </li>
              </template>
              <template v-if="modalId === 'rulesetDirectory'">
                <li
                  v-for="ruleset in directoryData.childrenYaml"
                  :key="ruleset.path"
                  class="hover:bg-base-300 cursor-default py-0.5"
                  @click="updateSelectedDirectories(ruleset.path)"
                >
                  <i class="ri-file-text-line text-neutral"></i>
                  {{ ruleset.name }}
                </li>
              </template>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop w-screen h-screen absolute">
      <button>close</button>
    </form>
  </dialog>
</template>
