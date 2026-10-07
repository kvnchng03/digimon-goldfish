# Digimon improvement guide

A TypeScript field guide with general Digimon TCG lessons and the existing Glowing Dawn research and practice tools.
The design uses white and navy reading surfaces, blue controls, and real Digimon card artwork.
Learn, Improve, Matchups and Practice are separate views with shareable hash links and browser back navigation.
The **Improve** tab (`#fundamentals`) teaches opening plans, memory, sequencing, finishing, matchups, outs, game review and deliberate list changes.
Each lesson includes an example and drill, followed by a suggested weekly practice cycle.
Focus links open the relevant lesson; individual lessons also have shareable deep links.
Rule reminders cite Bandai's Comprehensive Rules Manual v4.3, checked on 7 Oct 2026.
The narrative is in `index.html`; styling and strictly typed interactions are in `src/`.

## Run

Use Node 22.18 or newer, from this directory:

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5173.

## Check and build

```sh
npm run check
npm run build
npm test
```

The build type-checks the app, writes a static site to `dist/`, and exports a single offline HTML file to `../.lavish/glowing-dawn-guide.html`.
Open the exported HTML directly or run `lavish-axi ../.lavish/glowing-dawn-guide.html` for visual review.
Change source files and rebuild instead of editing exported files.
The browser suite uses installed Google Chrome locally and Playwright Chromium in CI.
It checks quiz scoring, checklist resets, navigation and lesson deep links, the card viewer, matchup filtering, printing, light/dark layouts from 320px to 1440px, and the offline export including card images.
PWA tests use temporary normal browser profiles to check installation requirements, offline reopening, card images, and user-controlled updates.
The same build is tested at the origin root and at `/pages-check/` to catch GitHub Pages repository-path errors.
Screenshots and test output go to the OS temporary directory under `glowing-dawn-guide-tests`.

## Deploy with GitHub Pages

The workflow in [`../.github/workflows/guide-pages.yml`](../.github/workflows/guide-pages.yml) builds and tests the guide, then deploys `guide/dist` on pushes to `main`.
Pull requests run the checks without deploying.
It can also be run manually from the Actions tab on `main`.

1. Put this project in a GitHub repository with a `main` branch, preserving the `guide/` and `.github/workflows/` paths.
   Include the guide source, `package-lock.json`, public icons, and workflow; `guide/node_modules/` and `guide/dist/` stay untracked.
2. In the repository, open **Settings > Pages > Build and deployment** and select **GitHub Actions** as the source.
3. Push to `main` or run **Guide checks and GitHub Pages** from the Actions tab.
4. Open the HTTPS URL shown by the deployment, typically `https://<owner>.github.io/<repository>/`.

These steps follow [GitHub's Pages workflow setup](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
The build uses relative asset, manifest, and worker URLs, so repository names and custom domains do not need a hard-coded base path.
No backend or separate hosting credentials are needed; deployment uses the workflow's GitHub token.
Only the built site is in the Pages artifact; the workbook files, game log, simulator and research source files are not served.
Local workbooks (including the personal player log), downloaded research transcripts, and the generated offline export are excluded by the root `.gitignore`.
The workflow assumes `main`; update its branch filters and deployment conditions together if you use another branch name.

## Install on a phone

Open the deployed HTTPS site online, then wait for **Ready for offline use** near the bottom of the guide.

- **iPhone:** In Safari, tap Share, then Add to Home Screen; keep Open as Web App enabled if offered.
- **Android:** In Chrome, use the guide's Install guide button when available, or the browser menu's Install app / Add to Home screen option.

See [Apple's home-screen instructions](https://support.apple.com/guide/iphone/iph42ab2f3a7/ios) and [Chrome's web-app instructions](https://support.google.com/chrome/answer/9658361?hl=en&co=GENIE.Platform%3DAndroid).
The installed guide opens in its own window at the Improve view.
The guide, puzzles, styles and all card artwork are cached for offline reading; linked videos and websites still need a connection.
Workbook paths refer to files on your computer and are not phone downloads.
Browsers can clear saved site data, so reopen online if the offline copy is removed.

New deployments are downloaded in the background when the guide checks for updates.
A **Reload to update** button appears when a new version is ready; the current quiz and checklist stay intact until you reload or close the page.
The app checks again when returning to a visible online tab, at most once a minute.
Scores and checklist ticks still last only for the current visit.

For local PWA testing, run `npm run build` followed by `npm run preview`, then open `http://127.0.0.1:4173/` on that computer.
`npm run dev` deliberately does not install a service worker.
A phone needs the deployed HTTPS URL; a computer's loopback URL is not reachable from the phone.
The standalone HTML export remains usable as a local file, but it does not register a worker or offer installation.

### Maintain the PWA

- `public/manifest.webmanifest` defines the name, start view, display mode and scope.
- `public/icon.svg` is the app icon source; run `npm run generate-icons` to regenerate the committed PNG icons.
- `vite.config.ts` uses Vite PWA and Workbox to generate a versioned precache from the build output.
- `src/pwa.ts` manages installation, offline status and update prompts.
- Keep service-worker registration scoped to the guide directory so sibling GitHub Pages projects remain independent.

## Refresh puzzles

```sh
npm run sync-puzzles
npm run build
```

The sync command runs the existing `tools/puzzles.py` through Python and validates the result before writing `src/puzzles.json`.
The source currently contains 15 puzzles; the handoff's count of 16 was stale.
The original situations, answers, explanations and evidence tags are preserved.
Source research dates, summaries and the timing table are editorial content in `index.html`; review those separately when the research changes.

## Behavior

- Quiz scores and turn checks last for the current page visit.
- Theme preference is stored locally when browser storage is available.
- Matchup filters narrow the reference cards; printing includes all four matchups.
- Printing expands lessons and source notes, then restores the reader's previous sections.
- Printing omits the interactive quiz; use the workbook for its printable puzzle collection.
- Clipboard buttons copy workspace-relative paths or the simulator command, with a manual-copy fallback.
- The guide never reads or writes the user's game log and uses no external services for its own features.
- External source links open only when clicked.
- Official English card images are stored in `src/assets/cards/`; `src/cards.ts` holds their names and teaching roles.
- Clicking a card opens its full image, card number and official source link in an accessible dialog.
- Puzzle references show mentioned cards, including cards explicitly absent from the position; they are not a reconstructed hand or board.
- The hosted build precaches the guide and card images with a service worker; the export embeds them for offline use.

Research remains a dated snapshot, including format-specific advice, conflicting pilot recommendations, small samples and simulator limitations.
