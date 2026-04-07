import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Это критично: связываем системные имена с установленными пакетами
      process: "process/browser",
      buffer: "buffer",
      stream: "stream-browserify",
      util: "util",
    },
  },
  define: {
    // Принудительно заменяем обращения к global и process.env в коде библиотек
    global: 'globalThis',
    'process.env': {},
    'process.version': '"v24.14.1"', // Можно указать любую версию
  },
  optimizeDeps: {
    // Заставляем Vite заранее обработать эти пакеты
    include: ['buffer', 'process'],
  },
})