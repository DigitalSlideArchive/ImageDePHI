export type DirectoryData = {
  directory: string;
  ancestors: Path[];
  children: Path[];
  childrenImages: Path[];
  childrenYaml: Path[];
};

export interface ImagePlanParams {
  directory: string;
  rules?: string;
  limit?: number;
  offset?: number;
  update?: boolean;
}

export type imagePlanResponse = {
  data: Record<string, Record<string, string>>;
  total: number;
  tags: string[];
};

export interface Path {
  name: string;
  path: string;
}
export interface SelectedDirectories {
  [key: string]: string;
}
