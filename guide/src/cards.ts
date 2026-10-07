import { element } from './dom';

interface Card {
  id: string;
  name: string;
  role: string;
}

const cards: readonly Card[] = [
  { id: 'ST23-13', name: 'Tomoro Tenma & Kyo Sawashiro', role: 'Your fuel engine' },
  { id: 'ST23-09', name: 'Atratusmon', role: 'Digimon-effect protection' },
  { id: 'BT25-043', name: 'Habakirimon', role: 'Removal and security pressure' },
  { id: 'ST23-06', name: 'Gekkomon', role: 'Search and load fuel' },
  { id: 'ST23-15', name: 'e-Pulse', role: 'Find and rebuild your engine' },
  { id: 'BT25-032', name: 'Liollmon', role: 'Search for your pieces' },
  { id: 'BT25-041', name: 'Murasamemon', role: 'A base for another attack' },
  { id: 'BT25-035', name: 'Cougarmon', role: 'Chain your evolution' },
  { id: 'BT26-103', name: 'Jupitermon: Wrath Mode', role: 'Watch security-removal triggers' },
  { id: 'EX12-065', name: 'Kaguyamon', role: 'Blockers and deletion payoffs' },
  { id: 'BT26-081', name: 'Mervamon', role: 'Removal and recurring bodies' },
  { id: 'BT26-082', name: 'Ravemon', role: 'Removal and hand pressure' },
  { id: 'BT26-025', name: 'Liollmon', role: 'Different card, different effect' },
  { id: 'ST23-04', name: 'Murasamemon', role: 'Check the inherited effect' },
  { id: 'BT25-057', name: 'Monarchlizamon', role: 'DUAL Option utility' },
  { id: 'ST23-03', name: 'Cougarmon', role: 'Your evolving attack stack' },
  { id: 'BT26-089', name: 'Kyo Sawashiro', role: 'Early Tamer access' },
  { id: 'BT25-049', name: 'Armalizamon', role: 'Suspend a blocker' },
  { id: 'BT24-041', name: 'Minervamon', role: 'Beware deletion payoffs' },
];

const images = import.meta.glob<string>('./assets/cards/*.png', {
  eager: true, query: '?url', import: 'default',
});

function imageFor(card: Card): string {
  const source = images[`./assets/cards/${card.id}.png`];
  if (!source) throw new Error(`Missing card artwork: ${card.id}`);
  return source;
}

export function cardButton(id: string): HTMLButtonElement {
  const card = cards.find(card => card.id === id);
  if (!card) throw new Error(`Unknown card: ${id}`);
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'digimon-card';
  button.setAttribute('aria-label', `Inspect ${card.name} (${card.id})`);
  const image = document.createElement('img');
  image.src = imageFor(card);
  image.alt = `${card.name} ${card.id}, official English card`;
  image.width = 430;
  image.height = 600;
  image.decoding = 'async';
  const caption = document.createElement('span');
  caption.className = 'card-caption';
  const name = document.createElement('strong');
  name.textContent = card.name;
  const number = document.createElement('small');
  number.textContent = card.id;
  caption.append(name, number);
  button.append(image, caption);
  button.addEventListener('click', () => {
    element('#card-dialog-title', HTMLHeadingElement).textContent = card.name;
    element('#card-dialog-id', HTMLParagraphElement).textContent = card.id;
    const enlarged = element('#card-dialog-image', HTMLImageElement);
    enlarged.src = imageFor(card);
    enlarged.alt = image.alt;
    element('#card-dialog-note', HTMLParagraphElement).textContent = card.role;
    element('#card-dialog-source', HTMLAnchorElement).href = `https://world.digimoncard.com/cards/?card_no=${card.id}&search=true`;
    element('#card-dialog', HTMLDialogElement).showModal();
  });
  return button;
}

export function renderPositionCards(situation: string): void {
  const explicitIds = new Set(situation.match(/(?:ST|BT|EX)\d+-\d+/g) ?? []);
  // Only infer a variant when its name is unique in this card catalog.
  const shown = cards.filter(card => explicitIds.has(card.id) || (
    cards.filter(candidate => candidate.name === card.name).length === 1 &&
    situation.includes(card.name) &&
    !cards.some(candidate => explicitIds.has(candidate.id) && candidate.name === card.name)
  ));
  const shelf = element('#quiz-card-shelf', HTMLDivElement);
  shelf.replaceChildren(...shown.map(card => cardButton(card.id)));
  const details = element('#quiz-cards', HTMLDetailsElement);
  details.hidden = shown.length === 0;
  const summary = details.querySelector('summary');
  if (summary) summary.textContent = `Card reference (${shown.length})`;
}

export function setupCards(): void {
  document.querySelectorAll<HTMLElement>('[data-card-slot]').forEach(slot => {
    if (slot.dataset.cardSlot) slot.append(cardButton(slot.dataset.cardSlot));
  });
  document.querySelectorAll<HTMLElement>('[data-card-list]').forEach(shelf => {
    for (const id of shelf.dataset.cardList?.split(',') ?? []) shelf.append(cardButton(id));
  });
  const dialog = element('#card-dialog', HTMLDialogElement);
  element('#close-card', HTMLButtonElement).addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const rect = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom)) dialog.close();
  });
}
