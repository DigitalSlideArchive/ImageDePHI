import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import os from "os";


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server:{
    fs:{
      // Include the current yarn cache directory in the allow list
      allow:['..',  `${os.homedir()}/.yarn/`]
    }
  }
});
