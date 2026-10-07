type Theme = 'light' | 'dark';
const key = 'gd-guide-theme';
const preference = matchMedia('(prefers-color-scheme: dark)');
let selected: Theme | null = null;

try {
  const saved = localStorage.getItem(key);
  if (saved === 'light' || saved === 'dark') selected = saved;
} catch {
  // Private browsing and local-file policies may block browser storage.
}

function apply(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  const button = document.querySelector('#theme-button');
  if (button instanceof HTMLButtonElement) {
    button.textContent = theme === 'dark' ? 'Light mode' : 'Dark mode';
    button.setAttribute('aria-label', `Switch to ${button.textContent.toLowerCase()}`);
  }
}

apply(selected ?? (preference.matches ? 'dark' : 'light'));
preference.addEventListener('change', () => {
  if (!selected) apply(preference.matches ? 'dark' : 'light');
});

export function toggleTheme(): void {
  selected = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  apply(selected);
  try {
    localStorage.setItem(key, selected);
  } catch {
    // Theme changes still work for this visit without persistence.
  }
}
