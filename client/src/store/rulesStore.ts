import { ref } from "vue";
import { fetchRules } from "../api/rest";

export const rules= ref([] as string[]);

export async function fetchRulesData() {
  const data = await fetchRules();
  rules.value = [
    ...Object.keys(data.base_rules.tiff.metadata),
    ...Object.keys(data.base_rules.svs.metadata),
    ...Object.keys(data.base_rules.dicom.metadata)
  ];
}
