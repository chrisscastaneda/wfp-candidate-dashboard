import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { viteSingleFile } from 'vite-plugin-singlefile'

// Builds one self-contained dist/index.html (JS, CSS and candidate data inlined)
// so it can be opened from disk or served from GitHub Pages as-is.
export default defineConfig({
  base: './',
  plugins: [vue(), tailwindcss(), viteSingleFile()],
})
