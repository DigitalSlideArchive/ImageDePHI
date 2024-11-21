import { ref, Ref } from "vue";
import { SelectedDirectories } from "./types";

const storedDirectories = {
  inputDirectory: localStorage.getItem("inputDirectory"),
  outputDirectory: localStorage.getItem("outputDirectory"),
  rulesetDirectory: localStorage.getItem("rulesetDirectory"),
}

export const selectedDirectories: Ref<SelectedDirectories> = ref({
  inputDirectory: storedDirectories.inputDirectory ? storedDirectories.inputDirectory : "",
  outputDirectory: storedDirectories.outputDirectory ? storedDirectories.outputDirectory : "",
  rulesetDirectory: storedDirectories.rulesetDirectory ? storedDirectories.rulesetDirectory : "",
});
