export type Letter = 'A' | 'B' | 'C' | 'D';
export const letters: readonly Letter[] = ['A', 'B', 'C', 'D'];

export interface Puzzle {
  matchup: string;
  skill: string;
  situation: string;
  question: string;
  options: string[];
  answer: Letter;
  why: string;
  rule: string;
  evidence: string;
  source: string;
}

function isPuzzle(value: unknown): value is Puzzle {
  if (typeof value !== 'object' || value === null) return false;
  const required = ['matchup', 'skill', 'situation', 'question', 'why', 'rule', 'evidence', 'source'];
  for (const key of required) {
    if (!(key in value) || typeof Reflect.get(value, key) !== 'string') return false;
  }
  if (!('options' in value) || !Array.isArray(value.options)) return false;
  if (value.options.length < 2 || value.options.length > letters.length) return false;
  if (!value.options.every(option => typeof option === 'string')) return false;
  return 'answer' in value && letters.slice(0, value.options.length).some(letter => letter === value.answer);
}

export function parsePuzzles(value: unknown): Puzzle[] {
  if (!Array.isArray(value) || value.length === 0 || !value.every(isPuzzle)) {
    throw new Error('Puzzle data must contain valid questions, choices and answer letters.');
  }
  return value;
}
