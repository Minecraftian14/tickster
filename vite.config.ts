import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import path from 'node:path'
import { resolve } from 'path';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(),],
})
