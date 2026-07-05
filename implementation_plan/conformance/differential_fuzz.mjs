#!/usr/bin/env node
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

import { compareResults, loadResultEnvelope, writeComparisonArtifacts } from './compare.mjs';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = resolve(args.root);
  const outDir = resolve(root, args.outDir);
  const tempDir = mkdtempSync(join(tmpdir(), 'logic-diff-fuzz-'));

  try {
    const vectorsDir = join(tempDir, 'vectors');
    mkdirSync(vectorsDir, { recursive: true });
    const vectorsPath = join(vectorsDir, 'fuzz-vectors.json');
    const pyOut = join(tempDir, 'py-fuzz.json');
    const tsOut = join(tempDir, 'ts-fuzz.json');
    const reportDir = resolve(outDir, 'differential-fuzz-report');

    const vectors = buildFuzzVectors(args.casesPerEngine, args.seed);
    writeFileSync(vectorsPath, JSON.stringify({ schemaVersion: '2026-07-05', vectors }, null, 2) + '\n', 'utf8');

    run(
      `PYTHONPATH=${quote(join(root, 'external/ipfs_datasets'))} python3 ${quote(join(root, 'external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py'))} --vectors ${quote(vectorsDir)} --out ${quote(pyOut)}`,
      root,
    );
    run(
      `cd ${quote(join(root, 'swissknife'))} && npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ${quote(vectorsDir)} --out ${quote(tsOut)}`,
      root,
    );

    const expectation = Object.fromEntries(vectors.map(vector => [vector.id, {
      strictStructuredParity: true,
      decided: false,
      inputType: String(vector?.inputType ?? 'unknown'),
    }]));

    const comparison = compareResults(loadResultEnvelope(pyOut), loadResultEnvelope(tsOut), { vectorExpectation: expectation });
    writeComparisonArtifacts(comparison, reportDir);

    if (comparison.summary.MISMATCH > 0) {
      throw new Error(`Differential fuzz detected ${comparison.summary.MISMATCH} mismatches`);
    }

    const requiredInputTypes = ['folFormula', 'temporalTrace', 'modalKripke', 'deonticConflict', 'dcec', 'legalNorm', 'zkpWitness'];
    const byInputType = {};
    for (const vector of vectors) {
      const inputType = String(vector?.inputType ?? 'unknown');
      byInputType[inputType] = Number(byInputType[inputType] ?? 0) + 1;
    }

    const summary = {
      schemaVersion: '2026-07-05',
      generatedAt: new Date().toISOString(),
      seed: args.seed,
      casesPerEngine: args.casesPerEngine,
      requiredInputTypes,
      byInputType,
      total: comparison.summary.total,
      match: comparison.summary.MATCH,
      mismatch: comparison.summary.MISMATCH,
      parityPercent: comparison.summary.parityPercent,
    };
    writeFileSync(resolve(outDir, 'differential-fuzz.json'), JSON.stringify(summary, null, 2) + '\n', 'utf8');
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

function buildFuzzVectors(casesPerEngine, seed) {
  const rng = mulberry32(seed);
  const vectors = [];
  const engines = ['folFormula', 'temporalTrace', 'modalKripke', 'deonticConflict', 'dcec', 'legalNorm', 'zkpWitness'];

  for (const engine of engines) {
    for (let i = 0; i < casesPerEngine; i += 1) {
      const atom = `a_${engine}_${i}`;
      const mode = i % 3;
      const id = `fuzz-${engine}-${String(i).padStart(3, '0')}`;
      vectors.push(buildVector(engine, id, atom, mode, rng));
    }
  }

  return vectors;
}

function buildVector(engine, id, atom, mode, rng) {
  if (engine === 'folFormula') {
    return {
      id,
      subsystem: 'fol',
      inputType: 'folFormula',
      input: {
        folFormula: {
          premises: mode === 0 ? [atom, `!${atom}`] : mode === 1 ? [atom, `x${randInt(rng, 999)}`] : [],
          goal: mode === 1 ? atom : '',
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  if (engine === 'temporalTrace') {
    return {
      id,
      subsystem: 'temporal',
      inputType: 'temporalTrace',
      input: {
        temporalTrace: {
          events: mode === 0 ? [atom, `!${atom}`] : mode === 1 ? [atom, `e${randInt(rng, 999)}`] : [],
          query: mode === 1 ? atom : '',
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  if (engine === 'modalKripke') {
    return {
      id,
      subsystem: 'modal',
      inputType: 'modalKripke',
      input: {
        modalKripke: {
          worlds: mode === 0 ? [atom, `!${atom}`] : mode === 1 ? [atom, `w${randInt(rng, 999)}`] : [],
          query: mode === 1 ? atom : '',
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  if (engine === 'deonticConflict') {
    return {
      id,
      subsystem: 'deontic',
      inputType: 'deonticConflict',
      input: {
        deonticConflict: {
          obligations: mode === 2 ? [] : [atom],
          prohibitions: mode === 0 ? [atom] : [],
          query: mode === 1 ? atom : '',
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  if (engine === 'dcec') {
    return {
      id,
      subsystem: 'dcec',
      inputType: 'dcec',
      input: {
        dcec: {
          premises: mode === 0 ? [`O(${atom})`, `F(${atom})`] : mode === 1 ? [`O(${atom})`, `B${randInt(rng, 999)}`] : [],
          goal: mode === 1 ? `O(${atom})` : '',
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  if (engine === 'legalNorm') {
    return {
      id,
      subsystem: 'legal-norm',
      inputType: 'legalNorm',
      input: {
        legalNorm: {
          norms: mode === 2 ? [] : [`derive:${atom}`],
          facts: mode === 0 ? [`not:${atom}`] : mode === 1 ? [atom] : [],
          query: mode === 2 ? '' : atom,
        },
      },
      expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
    };
  }
  return {
    id,
    subsystem: 'zkp-statement',
    inputType: 'zkpWitness',
    input: {
      zkpWitness: {
        claims: mode === 2 ? [] : [atom],
        ...(mode === 0 ? { witnessState: 'invalid' } : mode === 1 ? { witnessState: 'valid' } : {}),
      },
    },
    expected: { status: mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved', acceptableReasons: [mode === 0 ? 'refuted' : mode === 2 ? 'unknown' : 'proved'] },
  };
}

function parseArgs(argv) {
  const args = { root: process.cwd(), outDir: 'conformance', casesPerEngine: 20, seed: 1337 };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--root') args.root = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--cases-per-engine') args.casesPerEngine = Number(argv[++i]);
    else if (arg === '--seed') args.seed = Number(argv[++i]);
    else if (arg === '--help') {
      console.log('Usage: node implementation_plan/conformance/differential_fuzz.mjs [--cases-per-engine N] [--seed N] [--out-dir DIR]');
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function run(command, cwd) {
  const completed = spawnSync('bash', ['-lc', command], { cwd, stdio: 'inherit' });
  if (completed.status !== 0) {
    throw new Error(`Command failed with exit code ${completed.status}: ${command}`);
  }
}

function randInt(rng, maxExclusive) {
  return Math.floor(rng() * maxExclusive);
}

function mulberry32(seed) {
  let value = seed >>> 0;
  return function next() {
    value += 0x6d2b79f5;
    let t = value;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function quote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
