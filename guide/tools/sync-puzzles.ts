import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parsePuzzles } from '../src/puzzle-schema.ts';

const root = fileURLToPath(new URL('../../', import.meta.url));
const output = execFileSync('python3', ['-c', [
  'import json',
  'from tools.puzzles import puzzles',
  'print(json.dumps([p._asdict() for p in puzzles()], ensure_ascii=False))',
].join('\n')], { cwd: root, encoding: 'utf8' });
const puzzles = parsePuzzles(JSON.parse(output));
writeFileSync(new URL('../src/puzzles.json', import.meta.url), `${JSON.stringify(puzzles, null, 2)}\n`);
console.log(`Synced ${puzzles.length} puzzles from tools/puzzles.py.`);
