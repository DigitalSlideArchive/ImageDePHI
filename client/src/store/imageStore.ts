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
      const response = await getImages(
        this.currentDirectory + "/" + image,
        "thumbnail",
      );
      if (response.status >= 400) {
        this.imageRedactionPlan.data[image].thumbnail =
          "/thumbnailPlaceholder.svg";
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
        this.imageRedactionPlan.data[image].thumbnail = url;
      }
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
