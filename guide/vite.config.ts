import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  base: './',
  plugins: [VitePWA({
    // pwa.ts handles registration; the portable HTML export never registers.
    injectRegister: false,
    registerType: 'prompt',
    manifest: false,
    workbox: {
      globPatterns: ['**/*.{html,js,css,png,svg,webmanifest}'],
      navigateFallback: 'index.html',
      cleanupOutdatedCaches: true,
      clientsClaim: true,
      skipWaiting: false,
    },
  })],
  build: { cssCodeSplit: false, assetsInlineLimit: 0 },
});
