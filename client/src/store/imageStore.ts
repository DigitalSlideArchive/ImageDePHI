import { ref } from "vue";

type imagePlanResponse = {
  data: Record<string, Record<string, string>>;
  total: number;
};

export const imageRedactionPlan = ref({} as imagePlanResponse);
