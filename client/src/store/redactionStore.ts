import { ref, Ref } from "vue";

export const redactionStateFlags: Ref<Record<string, boolean>> = ref({
  redacting: false,
  redactionComplete: false,
  showImageTable: false,
  redactionSnackbar: false,
});
