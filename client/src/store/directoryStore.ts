import { ref, Ref } from "vue";
import { SelectedDirectories } from "./types";

export const selectedDirectories: Ref<SelectedDirectories> = ref({
  inputDirectory: "",
  outputDirectory: "",
});
