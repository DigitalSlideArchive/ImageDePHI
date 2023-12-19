export interface Directory {
    name: string;
    path: string;
}

export type DirectoryData = {
    directory: string;
    ancestors: Directory[];
    children: Directory[];
    childrenImages: string[];
}

export interface SelectedDirectories {
    [key: string]: string;
  }
