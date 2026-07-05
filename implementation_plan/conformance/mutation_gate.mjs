#!/usr/bin/env node
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

import { compareResults, loadResultEnvelope, writeComparisonArtifacts } from './compare.mjs';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = resolve(args.root);
  const vectorsDir = resolve(root, args.vectorsDir);
  const outDir = resolve(root, args.outDir);
  mkdirSync(outDir, { recursive: true });

  const pyBase = resolve(outDir, 'py-mutation-baseline-results.json');
  const tsBase = resolve(outDir, 'ts-mutation-baseline-results.json');
  const pyMut = resolve(outDir, 'py-mutated-results.json');
  const tsMut = resolve(outDir, 'ts-mutated-results.json');
  const python = pythonBin(root);

  run(
    `PYTHONPATH=${quote(join(root, 'external/ipfs_datasets'))} ${quote(python)} ${quote(join(root, 'external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py'))} --vectors ${quote(vectorsDir)} --out ${quote(pyBase)} --require-engines z3_runtime,tdfol_core,dcec_prover`,
    root,
    'Generate Python baseline conformance results',
  );
  run(
    `cd ${quote(join(root, 'swissknife'))} && npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ${quote(join('..', relFromRoot(root, vectorsDir)))} --out ${quote(join('..', relFromRoot(root, tsBase)))}`,
    root,
    'Generate TypeScript baseline conformance results',
  );

  run(
    `PYTHONPATH=${quote(join(root, 'external/ipfs_datasets'))} ${quote(python)} ${quote(join(root, 'external/ipfs_datasets/ipfs_datasets_py/logic/conformance/py_reference_runner.py'))} --vectors ${quote(vectorsDir)} --out ${quote(pyMut)} --require-engines z3_runtime,tdfol_core,dcec_prover`,
    root,
    'Generate Python reference for mutation check',
  );
  run(
    `cd ${quote(join(root, 'swissknife'))} && SWISSKNIFE_CONFORMANCE_FAULT=flip-fol npx tsx test/conformance/ts-conformance-runner.cli.ts --vectors ${quote(join('..', relFromRoot(root, vectorsDir)))} --out ${quote(join('..', relFromRoot(root, tsMut)))}`,
    root,
    'Generate TypeScript implementation-mutated conformance results',
  );

  const baselineComparison = compareResults(
    loadResultEnvelope(pyBase),
    loadResultEnvelope(tsBase),
    { vectorExpectation: loadVectorExpectation(vectorsDir) },
  );
  const mutationComparison = compareResults(
    loadResultEnvelope(pyMut),
    loadResultEnvelope(tsMut),
    { vectorExpectation: loadVectorExpectation(vectorsDir) },
  );

  const mutationDrop = baselineComparison.summary.MATCH - mutationComparison.summary.MATCH;
  writeComparisonArtifacts(mutationComparison, resolve(outDir, 'mutated-report'));

  if (!(mutationDrop > 0)) {
    throw new Error(`Implementation mutation did not reduce MATCH count (baseline=${baselineComparison.summary.MATCH}, mutated=${mutationComparison.summary.MATCH})`);
  }

  const expectedOutputMutationDrop = assertExpectedOutputMutationDetectsMismatch(pyBase, tsBase, vectorsDir);

  const gateSummary = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    baselineMatch: baselineComparison.summary.MATCH,
    mutatedMatch: mutationComparison.summary.MATCH,
    mutationDrop,
    expectedOutputMutationDrop,
    passed: mutationDrop > 0 && expectedOutputMutationDrop > 0,
  };
  writeFileSync(resolve(outDir, 'mutation-gate.json'), JSON.stringify(gateSummary, null, 2) + '\n', 'utf8');

  if (!gateSummary.passed) {
    throw new Error('Mutation gate failed');
  }

  console.log(JSON.stringify(gateSummary, null, 2));
}

function assertExpectedOutputMutationDetectsMismatch(pyPath, tsPath, vectorsDir) {
  const expectation = loadVectorExpectation(vectorsDir);
  const decidedRows = Object.entries(expectation).filter(([, exp]) => exp.decided && typeof exp.expectedStatus === 'string');
  if (decidedRows.length === 0) {
    throw new Error('No decided vectors available for expected-output mutation test');
  }

  const [vectorId, row] = decidedRows[0];
  const original = row.expectedStatus;
  row.expectedStatus = original === 'proved' ? 'refuted' : 'proved';

  const comparison = compareResults(loadResultEnvelope(pyPath), loadResultEnvelope(tsPath), { vectorExpectation: expectation });
  const mismatch = comparison.rows.find(item => item.vectorId === vectorId);
  if (!mismatch || mismatch.expectedStatusMatch !== false) {
    throw new Error(`Expected-output mutation was not detected for vector ${vectorId}`);
  }
  return 1;
}

function loadVectorExpectation(vectorsDir) {
  const payload = {};
  const files = spawnSync('bash', ['-lc', `ls ${quote(vectorsDir)}/*.json`], { encoding: 'utf8' });
  if (files.status !== 0) {
    throw new Error(`Unable to list vector files in ${vectorsDir}`);
  }
  for (const file of files.stdout.split(/\n+/).map(line => line.trim()).filter(Boolean)) {
    const corpus = JSON.parse(readFileSync(file, 'utf8'));
    for (const vector of corpus.vectors ?? []) {
      payload[vector.id] = {
        strictStructuredParity: Boolean(vector?.expected?.strictStructuredParity),
        expectedStatus: typeof vector?.expected?.status === 'string' ? vector.expected.status : undefined,
        decided: vector?.expected?.decided === true,
      };
    }
  }
  return payload;
}

function parseArgs(argv) {
  const args = { root: process.cwd(), vectorsDir: 'implementation_plan/conformance/vectors', outDir: 'conformance' };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--root') args.root = argv[++i];
    else if (arg === '--vectors') args.vectorsDir = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--help') {
      console.log('Usage: node implementation_plan/conformance/mutation_gate.mjs [--root <repo>] [--vectors <dir>] [--out-dir <dir>]');
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function pythonBin(root) {
  const venvPython = join(root, '.venv/bin/python');
  return existsSync(venvPython) ? venvPython : 'python3';
}

function run(command, cwd, label) {
  const completed = spawnSync('bash', ['-lc', command], { cwd, stdio: 'inherit' });
  if (completed.status !== 0) {
    throw new Error(`${label} failed with exit code ${completed.status}`);
  }
}

function relFromRoot(root, abs) {
  const normalizedRoot = resolve(root);
  const normalizedAbs = resolve(abs);
  return normalizedAbs.startsWith(normalizedRoot + '/')
    ? normalizedAbs.slice(normalizedRoot.length + 1)
    : normalizedAbs;
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
