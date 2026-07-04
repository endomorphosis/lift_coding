#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

export function loadResultEnvelope(path) {
  const payload = JSON.parse(readFileSync(path, 'utf8'));
  if (Array.isArray(payload)) return { results: payload };
  if (!Array.isArray(payload.results)) {
    throw new Error(`Result file ${path} does not contain a results array`);
  }
  return payload;
}

export function compareResults(pythonEnvelope, tsEnvelope) {
  const py = indexByVectorId(pythonEnvelope.results ?? []);
  const ts = indexByVectorId(tsEnvelope.results ?? []);
  const vectorIds = [...new Set([...Object.keys(py), ...Object.keys(ts)])].sort();
  const rows = [];

  for (const vectorId of vectorIds) {
    const pyResult = py[vectorId];
    const tsResult = ts[vectorId];
    let outcome;
    if (pyResult && !tsResult) outcome = 'TS_ONLY_MISSING';
    else if (!pyResult && tsResult) outcome = 'PY_ONLY_MISSING';
    else if (pyResult.status === 'error' && tsResult.status === 'error') outcome = 'BOTH_ERROR';
    else if (pyResult.status === tsResult.status) outcome = 'MATCH';
    else outcome = 'MISMATCH';

    rows.push({
      vectorId,
      subsystem: pyResult?.subsystem ?? tsResult?.subsystem ?? 'unknown',
      outcome,
      pythonStatus: pyResult?.status ?? '<missing>',
      tsStatus: tsResult?.status ?? '<missing>',
      pythonBackendMode: pyResult?.backendMode ?? '<missing>',
      tsBackendMode: tsResult?.backendMode ?? '<missing>',
      simulatedDivergence: Boolean(
        outcome === 'MISMATCH' &&
        (pyResult?.backendMode === 'simulated' || tsResult?.backendMode === 'simulated'),
      ),
      pythonError: pyResult?.error,
      tsError: tsResult?.error,
    });
  }

  const summary = summarize(rows);
  return {
    schemaVersion: '2026-07-03',
    generatedAt: new Date().toISOString(),
    pythonRunner: pythonEnvelope.runner ?? 'python-reference',
    tsRunner: tsEnvelope.runner ?? 'typescript-swissknife',
    summary,
    rows,
  };
}

export function writeComparisonArtifacts(comparison, outDir) {
  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'report.json'), JSON.stringify(comparison, null, 2) + '\n', 'utf8');
  writeFileSync(resolve(outDir, 'report.md'), renderMarkdownReport(comparison), 'utf8');
}

export function renderMarkdownReport(comparison) {
  const lines = [
    '# Logic Conformance Parity Report',
    '',
    `Generated: ${comparison.generatedAt}`,
    '',
    '## Summary',
    '',
    `- Total vectors: ${comparison.summary.total}`,
    `- Match: ${comparison.summary.MATCH}`,
    `- Mismatch: ${comparison.summary.MISMATCH}`,
    `- Both error: ${comparison.summary.BOTH_ERROR}`,
    `- Python-only missing: ${comparison.summary.PY_ONLY_MISSING}`,
    `- TypeScript-only missing: ${comparison.summary.TS_ONLY_MISSING}`,
    `- Parity: ${comparison.summary.parityPercent.toFixed(2)}%`,
    '',
    '## By Subsystem',
    '',
    '| Subsystem | Total | Match | Mismatch | Parity |',
    '|---|---:|---:|---:|---:|',
  ];

  for (const [subsystem, stats] of Object.entries(comparison.summary.bySubsystem).sort()) {
    lines.push(`| ${subsystem} | ${stats.total} | ${stats.MATCH} | ${stats.MISMATCH} | ${stats.parityPercent.toFixed(2)}% |`);
  }

  lines.push('', '## Differences', '');
  const differences = comparison.rows.filter(row => row.outcome !== 'MATCH');
  if (differences.length === 0) {
    lines.push('No differences.');
  } else {
    lines.push('| Vector | Subsystem | Outcome | Python | TypeScript | Note |');
    lines.push('|---|---|---|---|---|---|');
    for (const row of differences) {
      const note = row.simulatedDivergence ? 'simulated backend divergence' : (row.pythonError ?? row.tsError ?? '');
      lines.push(`| ${row.vectorId} | ${row.subsystem} | ${row.outcome} | ${row.pythonStatus} (${row.pythonBackendMode}) | ${row.tsStatus} (${row.tsBackendMode}) | ${escapeTable(note)} |`);
    }
  }

  lines.push('');
  return lines.join('\n');
}

function summarize(rows) {
  const base = {
    total: rows.length,
    MATCH: 0,
    MISMATCH: 0,
    BOTH_ERROR: 0,
    PY_ONLY_MISSING: 0,
    TS_ONLY_MISSING: 0,
    parityPercent: 0,
    bySubsystem: {},
  };

  for (const row of rows) {
    base[row.outcome] += 1;
    const stats = base.bySubsystem[row.subsystem] ?? {
      total: 0,
      MATCH: 0,
      MISMATCH: 0,
      BOTH_ERROR: 0,
      PY_ONLY_MISSING: 0,
      TS_ONLY_MISSING: 0,
      parityPercent: 0,
    };
    stats.total += 1;
    stats[row.outcome] += 1;
    base.bySubsystem[row.subsystem] = stats;
  }

  base.parityPercent = base.total === 0 ? 0 : (base.MATCH / base.total) * 100;
  for (const stats of Object.values(base.bySubsystem)) {
    stats.parityPercent = stats.total === 0 ? 0 : (stats.MATCH / stats.total) * 100;
  }
  return base;
}

function indexByVectorId(results) {
  return Object.fromEntries(results.map(result => [result.vectorId, result]));
}

function escapeTable(value) {
  return String(value ?? '').replace(/\|/g, '\\|');
}

function parseArgs(argv) {
  const args = { outDir: 'conformance', threshold: undefined };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--python') args.python = argv[++i];
    else if (arg === '--ts') args.ts = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--threshold') args.threshold = Number(argv[++i]);
    else if (arg === '--help') printHelpAndExit(0);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!args.python || !args.ts) throw new Error('Both --python and --ts result files are required');
  return args;
}

function printHelpAndExit(code) {
  console.log(`Usage: node implementation_plan/conformance/compare.mjs --python py.json --ts ts.json [options]

Options:
  --out-dir <dir>      Output directory for report.json and report.md
  --threshold <pct>    Fail when parity percentage is below this value
`);
  process.exit(code);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const comparison = compareResults(loadResultEnvelope(args.python), loadResultEnvelope(args.ts));
    writeComparisonArtifacts(comparison, resolve(args.outDir));
    if (args.threshold !== undefined && comparison.summary.parityPercent < args.threshold) {
      console.error(`Parity ${comparison.summary.parityPercent.toFixed(2)}% is below threshold ${args.threshold}%`);
      process.exit(1);
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
