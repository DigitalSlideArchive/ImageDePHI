import { reactive } from "vue";
import { imagePlanResponse } from "./types";
import { getRedactionPlan } from "../api/rest";

export const useRedactionPlan = reactive({
  imageRedactionPlan: {} as imagePlanResponse,
  async updateImageData(
    directory: string,
    limit: number,
    offset: number,
    update: boolean,
  ) {
    this.imageRedactionPlan = await getRedactionPlan(
      directory,
      limit,
      offset,
      update,
    );
  },

  clearImageData() {
    this.imageRedactionPlan = {} as imagePlanResponse;
  },
});
