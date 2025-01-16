import { ref, Ref, nextTick } from "vue";
import { SelectedDirectories, DirectoryData, Path } from "./types";
import { getDirectoryInfo } from "../api/rest";

const storedDirectories = {
  inputDirectory: localStorage.getItem("inputDirectory"),
  outputDirectory: localStorage.getItem("outputDirectory"),
  rulesetDirectory: localStorage.getItem("rulesetDirectory"),
};

export const selectedDirectories: Ref<SelectedDirectories> = ref({
  inputDirectory: storedDirectories.inputDirectory
    ? storedDirectories.inputDirectory
    : "",
  outputDirectory: storedDirectories.outputDirectory
    ? storedDirectories.outputDirectory
    : "",
  rulesetDirectory: storedDirectories.rulesetDirectory
    ? storedDirectories.rulesetDirectory
    : "",
});

export const directoryData: Ref<DirectoryData> = ref({
  directory: "",
  ancestors: [],
  children: [],
  childrenImages: [],
  childrenYaml: [],
});

export const loadingData = ref(false);

export const updateDirectories = async (currentDirectory?: string) => {
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

export const visibleImages: Ref<Path[]> = ref([]);
export const remainingImages = ref(0);

export const calculateVisibleItems = () => {
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
    const listItemHeight =
      listItems && listItems[0] ? listItems[0].clientHeight : 0;

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
