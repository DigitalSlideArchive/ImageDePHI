import { reactive } from "vue";
import { imagePlanResponse } from "./types";
import { getRedactionPlan, getImages } from "../api/rest";
import { selectedDirectories } from "./directoryStore";

export const useRedactionPlan = reactive({
  imageRedactionPlan: {} as imagePlanResponse,
  currentDirectory: selectedDirectories.value.inputDirectory,
  async updateImageData(
    directory: string,
    limit: number,
    offset: number,
    update: boolean,
  ) {
    this.currentDirectory = directory;
    this.imageRedactionPlan = await getRedactionPlan(
      directory,
      limit,
      offset,
      update,
    );
    this.getThumbnail(this.imageRedactionPlan.data);
  },
  async getThumbnail(imagedict: Record<string, Record<string, string>>){
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
        // eslint-disable-next-line no-constant-condition
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
