import { element } from './dom';

interface InstallPrompt extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export function setupPwa(): void {
  // The exported HTML is already self-contained and has no installable origin.
  if (location.protocol === 'file:') return;

  const panel = element('#install-panel', HTMLElement);
  const status = element('#offline-status', HTMLParagraphElement);
  const install = element('#install-app', HTMLButtonElement);
  const update = element('#update-app', HTMLButtonElement);
  const notice = element('#update-notice', HTMLDivElement);
  panel.hidden = false;

  let installPrompt: InstallPrompt | undefined;
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event as InstallPrompt;
    install.hidden = false;
  });
  window.addEventListener('appinstalled', () => {
    installPrompt = undefined;
    install.hidden = true;
  });
  install.addEventListener('click', async () => {
    const prompt = installPrompt;
    if (!prompt) return;
    installPrompt = undefined;
    install.hidden = true;
    try {
      await prompt.prompt();
      await prompt.userChoice;
    } catch {
      status.textContent = 'Use your browser menu to add the guide to your home screen.';
    }
  });

  if (!import.meta.env.PROD) {
    status.textContent = 'Development preview. Offline saving is enabled in the built app.';
    return;
  }
  if (!window.isSecureContext || !('serviceWorker' in navigator)) {
    status.textContent = 'Offline saving is unavailable here. Open the published HTTPS site in a supported browser.';
    return;
  }

  const serviceWorkers = navigator.serviceWorker;
  let reloadRequested = false;
  serviceWorkers.addEventListener('controllerchange', () => {
    if (reloadRequested) location.reload();
  });

  void serviceWorkers.register(new URL('./sw.js', document.baseURI), {
    scope: new URL('./', document.baseURI).pathname,
    updateViaCache: 'none',
  }).then(registration => {
    const showUpdate = (): void => {
      // A first install can briefly wait before activation, but it isn't an update.
      notice.hidden = !registration.waiting || !serviceWorkers.controller;
    };
    showUpdate();
    const watchInstall = (): void => {
      const worker = registration.installing;
      if (!worker) return;
      worker.addEventListener('statechange', () => {
        if (worker.state === 'installed') showUpdate();
        if (worker.state === 'redundant' && !registration.active) {
          status.textContent = 'Offline saving did not finish. Reconnect and reload to try again.';
        }
      });
    };
    watchInstall();
    registration.addEventListener('updatefound', watchInstall);
    update.addEventListener('click', () => {
      if (!registration.waiting) {
        // Another open tab may already have activated this update.
        location.reload();
        return;
      }
      reloadRequested = true;
      update.disabled = true;
      update.textContent = 'Updating...';
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    });
    void serviceWorkers.ready.then(() => {
      status.textContent = 'Ready for offline use. Lessons, puzzles and card art are saved on this device.';
    });
    let lastUpdateCheck = Date.now();
    const checkUpdate = (): void => {
      if (document.visibilityState !== 'visible' || !navigator.onLine) return;
      if (Date.now() - lastUpdateCheck < 60_000) return;
      lastUpdateCheck = Date.now();
      void registration.update().catch(() => { /* Keep the saved guide during network failures. */ });
    };
    document.addEventListener('visibilitychange', checkUpdate);
    window.addEventListener('online', checkUpdate);
  }).catch(() => {
    status.textContent = 'Offline saving is unavailable. You can keep reading online; reconnect and reload to retry.';
  });
}
