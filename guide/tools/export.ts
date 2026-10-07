import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

// Bundle the app as a portable, offline HTML guide for Lavish or direct opening.
const dist = new URL('../dist/', import.meta.url);
let html = readFileSync(new URL('index.html', dist), 'utf8');
// Install metadata belongs to the hosted site; keep the file export portable.
html = html.replace(/<link\b[^>]*rel="manifest"[^>]*>/g, '');
html = html.replace(/(<link\b[^>]*rel="(?:icon|apple-touch-icon)"[^>]*href=")([^"]+)("[^>]*>)/g,
  (_tag: string, before: string, path: string, after: string) => {
    const mime = path.endsWith('.svg') ? 'image/svg+xml' : 'image/png';
    const bytes = readFileSync(new URL(path, dist));
    return `${before}data:${mime};base64,${bytes.toString('base64')}${after}`;
  });
html = html.replace(/<script\b[^>]*src="([^\"]+)"[^>]*><\/script>/g, (_tag: string, path: string) => {
  const script = new URL(path, dist);
  const js = readFileSync(script, 'utf8')
    // Vite emits relative asset URLs in the entry module. Inline them only for
    // the portable artifact; the web app keeps independently cached images.
    .replace(/new URL\((["'`])([^"'`]+\.png)\1,\s*import\.meta\.url\)\.href/g,
      (_reference: string, _quote: string, asset: string) => {
        const image = readFileSync(new URL(asset, script));
        return JSON.stringify(`data:image/png;base64,${image.toString('base64')}`);
      })
    .replace(/<\/script/gi, '<\\/script');
  if (/new URL\([^)]*\.png/.test(js)) {
    throw new Error('Card images remain external in the portable artifact.');
  }
  return `<script type="module">${js}</script>`;
});
html = html.replace(/<link\b[^>]*rel="stylesheet"[^>]*href="([^\"]+)"[^>]*>/g, (_tag: string, path: string) => {
  const css = readFileSync(new URL(path, dist), 'utf8');
  return `<style>${css}</style>`;
});
if (html.includes('src="./assets/') || html.includes('href="./assets/')) {
  throw new Error('Export still references external build assets.');
}
const output = new URL('../../.lavish/glowing-dawn-guide.html', import.meta.url);
mkdirSync(new URL('.', output), { recursive: true });
writeFileSync(output, html);
console.log(`Exported portable guide to ${output.pathname}`);
