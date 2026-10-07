import rawPuzzles from './puzzles.json';
import { appendText, element } from './dom';
import { letters, parsePuzzles } from './puzzle-schema';
import type { Letter, Puzzle } from './puzzle-schema';
import { renderPositionCards } from './cards';

export function setupQuiz(): void {
  const puzzles = parsePuzzles(rawPuzzles);
  const picks = new Map<number, Letter>();
  let current = 0;
  const select = element('#puzzle-select', HTMLSelectElement);
  const question = element('#quiz-question', HTMLHeadingElement);
  const options = element('#quiz-options', HTMLDivElement);
  const feedback = element('#quiz-feedback', HTMLDivElement);
  const previous = element('#quiz-prev', HTMLButtonElement);
  const next = element('#quiz-next', HTMLButtonElement);
  const restart = element('#quiz-restart', HTMLButtonElement);

  document.querySelectorAll('[data-puzzle-count]').forEach(el => {
    el.textContent = String(puzzles.length);
  });
  puzzles.forEach((puzzle, index) => {
    const option = document.createElement('option');
    option.value = String(index);
    option.textContent = `${index + 1}. ${puzzle.skill} / ${puzzle.matchup}`;
    select.append(option);
  });

  function showFeedback(puzzle: Puzzle, pick: Letter): void {
    appendText(feedback, 'h4', pick === puzzle.answer
      ? `Correct. ${puzzle.answer} is the answer.`
      : `You chose ${pick}. The answer is ${puzzle.answer}.`);
    appendText(feedback, 'p', puzzle.why);
    appendText(feedback, 'p', `Workbook takeaway: ${puzzle.rule}`);
    appendText(feedback, 'p', `Evidence: ${puzzle.evidence}`, 'small');
    appendText(feedback, 'p', puzzle.source, 'small');
    if (puzzle.evidence.includes('SIM')) {
      appendText(feedback, 'p', 'Scope: this answer includes goldfish-model evidence. Real opposing boards can change the best play.', 'small');
    }
  }

  function render(focus = false): void {
    const puzzle = puzzles[current];
    if (!puzzle) throw new Error(`Missing puzzle at index ${current}`);
    select.value = String(current);
    element('#quiz-tag', HTMLSpanElement).textContent = `${puzzle.matchup} · ${puzzle.skill}`;
    element('#quiz-situation', HTMLParagraphElement).textContent = puzzle.situation;
    renderPositionCards(puzzle.situation);
    question.textContent = puzzle.question;
    const pick = picks.get(current);
    const answered = pick !== undefined;
    options.replaceChildren();

    puzzle.options.forEach((text, index) => {
      const letter = letters[index];
      if (!letter) throw new Error('Too many answer choices');
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'quiz-option';
      button.disabled = answered;
      appendText(button, 'span', letter, 'letter');
      appendText(button, 'span', text);
      if (answered && letter === puzzle.answer) {
        button.classList.add('correct');
        button.setAttribute('aria-label', `${letter}. ${text} Correct answer`);
      }
      if (answered && letter === pick && pick !== puzzle.answer) {
        button.classList.add('incorrect');
        button.setAttribute('aria-label', `${letter}. ${text} Your answer, incorrect`);
      }
      button.addEventListener('click', () => {
        if (picks.has(current)) return;
        picks.set(current, letter);
        render();
        feedback.tabIndex = -1;
        feedback.focus({ preventScroll: true });
        feedback.scrollIntoView({ block: 'nearest', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
      });
      options.append(button);
    });

    feedback.replaceChildren();
    feedback.hidden = !answered;
    if (pick !== undefined) showFeedback(puzzle, pick);
    const correct = [...picks].filter(([index, answer]) => answer === puzzles[index]?.answer).length;
    element('#quiz-score', HTMLElement).textContent = `${correct} / ${picks.size}`;
    element('#quiz-progress', HTMLParagraphElement).textContent = `Puzzle ${current + 1} of ${puzzles.length} · ${picks.size} answered`;
    previous.disabled = current === 0;
    next.hidden = current === puzzles.length - 1;
    restart.hidden = current !== puzzles.length - 1;
    if (focus) question.focus({ preventScroll: true });
  }

  select.addEventListener('change', () => {
    current = Number(select.value);
    render();
  });
  previous.addEventListener('click', () => {
    if (current > 0) { current--; render(true); }
  });
  next.addEventListener('click', () => {
    if (current < puzzles.length - 1) { current++; render(true); }
  });
  restart.addEventListener('click', () => {
    picks.clear();
    current = 0;
    render(true);
  });
  render();
  element('#quiz', HTMLDivElement).hidden = false;
}
