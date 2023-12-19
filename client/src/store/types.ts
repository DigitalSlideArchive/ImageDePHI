export interface Path {
    name: string;
    path: string;
}

export type DirectoryData = {
    directory: string;
    ancestors: Path[];
    children: Path[];
    childrenImages: Path[];
}

export interface SelectedDirectories {
    [key: string]: string;
  }
