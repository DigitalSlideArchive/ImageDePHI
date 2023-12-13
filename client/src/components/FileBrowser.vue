<script setup lang="ts">
import { ref, Ref, watch} from 'vue';
import { getDirectoryInfo } from '../api/rest';
import { selectedDirectories } from '../store/directoryStore';
import { DirectoryData } from '../store/types';

defineProps({
  modalId: String,
  title: String,
});

const directoryData: Ref<DirectoryData> = ref({
  directory: '',
  ancestors: [],
  children: [],
  childrenImages: []
});


const updateDirectories = async (currentDirectory?:string) => {
  const data = await getDirectoryInfo(currentDirectory);
  directoryData.value = await {...data, children: data.child_directories, childrenImages: data.child_images};

};
updateDirectories();



</script>

<template>
  <dialog
    class="modal"
    :id="modalId"
  >
    <div class="w-full max-w-4xl h-4/5 rounded-xl overflow-hidden">
      <div class="modal-box w-full max-w-4xl h-full overflow-auto pt-0">
        <div class="sticky top-0 pt-6 bg-white">
          <div class="flex justify-between">
            <h2 class="text-lg font-semibold">
              {{ title }}
            </h2>
              <button class="btn bg-primary float-right" type="button">Select</button>
          </div>
          <div class="text-sm breadcrumbs mb-4 border-b-2">
            <ul class="flex flex-wrap">
                <li v-for="ancestor in directoryData.ancestors" class="mr-1 text-base">
                  <!-- {# The root directory has an empty string "name" #}
                  {% set ancestor_name = ancestor.name|default('/', true) %} -->
                  <!-- {% if loop.last %}
                    <span class="font-black">{{ ancestor_name }}</span>
                  {% else %} -->
                    <a class="text-blue-700">
                      {{ Object.keys(ancestor)[0] }}
                    </a>
                  <!-- {% endif %} -->
                </li>
            </ul>
          </div>
        </div>
        <ul class="menu menu-sm">

            <!-- <a class="text-blue-700"> -->
              <li v-for="child in directoryData.children">
                <a @click="updateDirectories(Object.values(child)[0])">
                <i class="ri-folder-3-fill text-neutral"></i>
                {{ Object.keys(child)[0]}}
              </a>
              </li>
            <!-- </a> -->
        </ul>
        <ul class="pl-2">
          <!-- {% for child_image in directory_data.child_images[:10] %} -->
            <li>
              <!-- <i class="ri-image-fill text-sky-800"></i> -->
              <!-- {{ child_image.name }} -->
            </li>
          <!-- {% endfor %}
          {% if directory_data.child_images|length > 10 %}
            <li class="italic">{{ directory_data.child_images|length - 10 }} More Images</li>
          {% endif %} -->
        </ul>
      </div>
    </div>
    <form method="dialog" class="modal-backdrop">
      <button>close</button>
    </form>
  </dialog>

</template>
