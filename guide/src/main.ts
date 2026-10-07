import { element } from './dom';
import { setupQuiz } from './quiz';
import { toggleTheme } from './theme';
import { setupCards } from './cards';
import { setupNavigation } from './navigation';
import { setupPwa } from './pwa';

element('#theme-button', HTMLButtonElement).addEventListener('click', toggleTheme);
element('#print-button', HTMLButtonElement).addEventListener('click', () => window.print());

const checks = [...document.querySelectorAll<HTMLInputElement>('.check-row input')];
function countChecks(): void {
  element('#check-count', HTMLParagraphElement).textContent = `${checks.filter(el => el.checked).length} of ${checks.length} checked`;
}
checks.forEach(el => el.addEventListener('change', countChecks));
element('#reset-checks', HTMLButtonElement).addEventListener('click', () => {
  checks.forEach(el => { el.checked = false; });
  countChecks();
});

const filters = [...document.querySelectorAll<HTMLButtonElement>('.match-controls button')];
const matchups = [...document.querySelectorAll<HTMLElement>('.matchup')];
filters.forEach(button => button.addEventListener('click', () => {
  const match = button.dataset.match;
  filters.forEach(el => el.setAttribute('aria-pressed', String(el === button)));
  matchups.forEach(el => { el.hidden = match !== 'all' && el.dataset.opponent !== match; });
  element('#matchup-grid', HTMLDivElement).classList.toggle('single', match !== 'all');
}));

let toastTimer: ReturnType<typeof setTimeout> | undefined;
function toast(message: string): void {
  clearTimeout(toastTimer);
  const status = element('#toast', HTMLDivElement);
  status.textContent = message;
  status.hidden = false;
  toastTimer = setTimeout(() => { status.hidden = true; }, 4000);
}

async function copy(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    toast('Copied to clipboard.');
  } catch {
    window.prompt('Copy this text:', text);
  }
}

document.querySelectorAll<HTMLButtonElement>('[data-copy]').forEach(el => {
  el.addEventListener('click', () => {
    if (el.dataset.copy) void copy(el.dataset.copy);
  });
});
element('#copy-review', HTMLButtonElement).addEventListener('click', () => {
  void copy('Matchup / result:\nFirst or second:\nTamer by end of my T2:\nDeciding turn:\nLine I chose:\nAlternative with the information I had:\nCause (draw / misplay / matchup / flip):\nNext drill:');
});

// Print the full guide, then restore the reader's expanded/collapsed sections.
let printDetails: HTMLDetailsElement[] = [];
window.addEventListener('beforeprint', () => {
  printDetails = [...document.querySelectorAll<HTMLDetailsElement>('details:not([open])')];
  printDetails.forEach(details => { details.open = true; });
});
window.addEventListener('afterprint', () => {
  printDetails.forEach(details => { details.open = false; });
  printDetails = [];
});

setupCards();
setupQuiz();
setupNavigation();
setupPwa();
