import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0', // Escuchar en todas las interfaces de red
    port: 5173,
    strictPort: true,
  }
})
