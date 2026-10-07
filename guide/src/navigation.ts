export function setupNavigation(): void {
  const links = [...document.querySelectorAll<HTMLAnchorElement>('[data-route]')];
  const panels = [...document.querySelectorAll<HTMLElement>('[data-view]')];

  function navigate(): void {
    const id = location.hash.slice(1) || 'learn';
    const target = document.getElementById(id);
    const parent = target?.closest<HTMLElement>('[data-view]');
    // Shared notes stay in the current view; any section can own a route.
    const view = parent?.dataset.view ?? (target
      ? links.find(link => link.getAttribute('aria-current') === 'page')?.dataset.route
      : 'learn') ?? 'learn';
    panels.forEach(panel => { panel.hidden = panel.dataset.view !== view; });
    links.forEach(link => {
      if (link.dataset.route === view) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    // Deep links reveal their content even inside nested, collapsed lessons/notes.
    let node: HTMLElement | null = target;
    while (node) {
      if (node instanceof HTMLDetailsElement) node.open = true;
      node = node.parentElement;
    }
    requestAnimationFrame(() => {
      if (links.some(link => link.hash === `#${id}`)) window.scrollTo(0, 0);
      else target?.scrollIntoView({ block: 'start' });
    });
  }
  window.addEventListener('hashchange', navigate);
  // Repeated links still scroll and reopen content the reader has collapsed.
  document.querySelectorAll<HTMLAnchorElement>('a[href^="#"]').forEach(link => link.addEventListener('click', () => {
    if (link.hash === location.hash) navigate();
  }));
  navigate();
}
