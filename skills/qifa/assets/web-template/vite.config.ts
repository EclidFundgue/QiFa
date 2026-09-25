import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base 用相对路径，构建产物可离线打开（file:// 或任意静态服务器）。
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5174,
    strictPort: false,
    open: false
  },
  build: {
    outDir: "dist",
    assetsDir: "assets"
  }
});
