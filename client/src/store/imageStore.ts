import { reactive } from "vue";
import { imagePlanResponse, ImagePlanParams } from "./types";
import { getRedactionPlan, getImages } from "../api/rest";
import { selectedDirectories } from "./directoryStore";
import { redactionStateFlags } from "./redactionStore";

export const useRedactionPlan = reactive({
  imageRedactionPlan: {} as imagePlanResponse,
  currentDirectory: selectedDirectories.value.inputDirectory,
  async updateImageData(params: ImagePlanParams) {
    this.currentDirectory = params.directory;
    this.imageRedactionPlan = await getRedactionPlan(params);
    this.getThumbnail(this.imageRedactionPlan.data);
  },
  async getThumbnail(imagedict: Record<string, Record<string, string>>) {
    Object.keys(imagedict).forEach(async (image) => {
      const keys = ["thumbnail", "label", "macro"];
      for (let kidx=0; kidx < keys.length; kidx += 1) {
        const key = keys[kidx];
        const response = await getImages(
          this.currentDirectory + "/" + image,
          key,
        );
        if (response.status >= 400) {
          this.imageRedactionPlan.data[image][key] = key === "thumbnail" ? "/thumbnailPlaceholder.svg" : "/associatedPlaceholder.svg";
          return;
        }
        if (response.body) {
          const reader = response.body.getReader();
          const chunks = [];

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            chunks.push(value);
          }
          const blob = new Blob(chunks);
          const url = URL.createObjectURL(blob);
          this.imageRedactionPlan.data[image][key]= url;
        }
      };
    });
  },

  clearImageData() {
    this.imageRedactionPlan = {} as imagePlanResponse;
  },
});

export const updateTableData = (params: ImagePlanParams) => {
  redactionStateFlags.value.redactionSnackbar = false;
  useRedactionPlan.updateImageData(params);
};
