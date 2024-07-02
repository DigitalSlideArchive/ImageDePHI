export type DirectoryData = {
  directory: string;
  ancestors: Path[];
  children: Path[];
  childrenImages: Path[];
};

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
