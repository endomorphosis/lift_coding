#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

export function loadResultEnvelope(path) {
  const payload = JSON.parse(readFileSync(path, 'utf8'));
  if (Array.isArray(payload)) return { results: payload };
  if (!Array.isArray(payload.results)) {
    throw new Error(`Result file ${path} does not contain a results array`);
  }
  return payload;
}

export function compareResults(pythonEnvelope, tsEnvelope, options = {}) {
  const py = indexByVectorId(pythonEnvelope.results ?? []);
  const ts = indexByVectorId(tsEnvelope.results ?? []);
  const vectorExpectation = options.vectorExpectation ?? {};
  const strictSelfContainment = Boolean(options.strictSelfContainment);
  const vectorIds = [...new Set([...Object.keys(py), ...Object.keys(ts)])].sort();
  const rows = [];

  for (const vectorId of vectorIds) {
    const pyResult = py[vectorId];
    const tsResult = ts[vectorId];
    const expectedStatus = vectorExpectation[vectorId]?.expectedStatus;
    const decided = Boolean(vectorExpectation[vectorId]?.decided);
    const inputType = vectorExpectation[vectorId]?.inputType;
    const tags = Array.isArray(vectorExpectation[vectorId]?.tags)
      ? vectorExpectation[vectorId].tags
      : [];
    const expectedBackendMode = vectorExpectation[vectorId]?.backendMode;
    const excludeFromParityWhenSimulated = Boolean(vectorExpectation[vectorId]?.excludeFromParityWhenSimulated);
    const strictStructuredParity = Boolean(vectorExpectation[vectorId]?.strictStructuredParity);
    const structuredFields = Array.isArray(vectorExpectation[vectorId]?.structuredFields)
      ? vectorExpectation[vectorId].structuredFields
      : ['status', 'reason', 'proverId', 'modelHash', 'countermodelHash', 'proofHash', 'derivationHash'];
    const simulatedObserved = Boolean(
      pyResult?.backendMode === 'simulated'
      || tsResult?.backendMode === 'simulated',
    );
    const hostNativeExcluded = Boolean(
      !strictSelfContainment
      && (
      expectedBackendMode === 'host-dependent'
      && excludeFromParityWhenSimulated
      )
    );

    const expectedStatusMatch =
      !decided
      || !expectedStatus
      || (
        pyResult?.status === expectedStatus
        && tsResult?.status === expectedStatus
      );

    const structured =
      pyResult && tsResult
        ? compareStructured(pyResult, tsResult, structuredFields)
        : undefined;
    const structuredArtifacts =
      strictStructuredParity && pyResult && tsResult
        ? validateStructuredArtifacts(pyResult, tsResult, expectedStatus)
        : undefined;
    const strictUnknownBridge = Boolean(
      strictSelfContainment
      && pyResult
      && tsResult
      && String(pyResult.status ?? '').toLowerCase() === 'unknown'
      && ['proved', 'refuted', 'sat'].includes(String(tsResult.status ?? '').toLowerCase())
      && String(pyResult.backendMode ?? '').toLowerCase() === 'host-dependent'
      && expectedStatusMatch,
    );
    const bothRealBackends = Boolean(
      pyResult
      && tsResult
      && String(pyResult.backendMode ?? '').toLowerCase() === 'real'
      && String(tsResult.backendMode ?? '').toLowerCase() === 'real',
    );

    let outcome;
    if (pyResult && !tsResult) outcome = 'TS_ONLY_MISSING';
    else if (!pyResult && tsResult) outcome = 'PY_ONLY_MISSING';
    else if (pyResult.status === 'error' && tsResult.status === 'error') outcome = 'BOTH_ERROR';
    else if (hostNativeExcluded) outcome = 'HOST_NATIVE_EXCLUDED';
    else if (
      strictStructuredParity &&
      pyResult.status === tsResult.status &&
      expectedStatusMatch &&
      structured?.match === true &&
      structuredArtifacts?.pass === true
    ) {
      outcome = 'MATCH';
    } else if (
      !strictStructuredParity &&
      pyResult.status === tsResult.status &&
      expectedStatusMatch
    ) {
      outcome = 'MATCH';
    }
    else outcome = 'MISMATCH';

    if (strictUnknownBridge && outcome === 'MISMATCH') {
      outcome = 'MATCH';
    }
    const strictSimulatedExpectation = Boolean(
      strictSelfContainment
      && (
        simulatedObserved
        || (
          expectedBackendMode === 'host-dependent'
          && excludeFromParityWhenSimulated
          && !bothRealBackends
        )
      ),
    );
    const strictDependencyEligible = outcome === 'MATCH'
      || outcome === 'MISMATCH'
      || outcome === 'HOST_NATIVE_EXCLUDED'
      || outcome === 'PY_ONLY_MISSING'
      || outcome === 'TS_ONLY_MISSING';
    const strictSimulatedDependency = Boolean(strictSimulatedExpectation && strictDependencyEligible);
    if (strictSimulatedDependency) {
      outcome = 'SIMULATED_DEPENDENCY';
    }

    rows.push({
      vectorId,
      subsystem: pyResult?.subsystem ?? tsResult?.subsystem ?? 'unknown',
      inputType: inputType ?? 'unknown',
      tags,
      outcome,
      strictSimulatedDependency,
      strictStructuredParity,
      strictUnknownBridge,
      structuredMatch: strictStructuredParity ? Boolean(structured?.match) : undefined,
      structuredArtifactMatch: strictStructuredParity ? Boolean(structuredArtifacts?.pass) : undefined,
      structuredArtifactProblems: strictStructuredParity ? (structuredArtifacts?.problems ?? []) : undefined,
      structuredFields: strictStructuredParity ? structuredFields : undefined,
      pythonStructuredHash: strictStructuredParity ? structured?.pythonHash : undefined,
      tsStructuredHash: strictStructuredParity ? structured?.tsHash : undefined,
      expectedStatus: expectedStatus ?? undefined,
      decided,
      expectedStatusMatch,
      pythonStatus: pyResult?.status ?? '<missing>',
      tsStatus: tsResult?.status ?? '<missing>',
      pythonBackendMode: pyResult?.backendMode ?? '<missing>',
      tsBackendMode: tsResult?.backendMode ?? '<missing>',
      simulatedDivergence: Boolean(
        outcome === 'MISMATCH' &&
        (pyResult?.backendMode === 'simulated' || tsResult?.backendMode === 'simulated'),
      ),
      hostNativeExcluded,
      pythonError: pyResult?.error,
      tsError: tsResult?.error,
    });
  }

  const summary = summarize(rows);
  return {
    schemaVersion: '2026-07-05',
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
    `- Simulated dependency: ${comparison.summary.SIMULATED_DEPENDENCY}`,
    `- Both error: ${comparison.summary.BOTH_ERROR}`,
    `- Python-only missing: ${comparison.summary.PY_ONLY_MISSING}`,
    `- TypeScript-only missing: ${comparison.summary.TS_ONLY_MISSING}`,
    `- Host-native excluded: ${comparison.summary.HOST_NATIVE_EXCLUDED}`,
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
      const note = row.expectedStatusMatch === false
        ? `expected-status mismatch (expected ${row.expectedStatus})`
        : row.strictSimulatedDependency
          ? 'strict simulated backend dependency'
        : row.strictStructuredParity && row.structuredArtifactMatch === false
          ? `strict structured artifact missing (${(row.structuredArtifactProblems ?? []).join('; ')})`
        : row.strictStructuredParity && row.structuredMatch === false
          ? `strict structured mismatch (${(row.structuredFields ?? []).join(',')})`
        : row.simulatedDivergence
          ? 'simulated backend divergence'
          : (row.pythonError ?? row.tsError ?? '');
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
    SIMULATED_DEPENDENCY: 0,
    BOTH_ERROR: 0,
    PY_ONLY_MISSING: 0,
    TS_ONLY_MISSING: 0,
    HOST_NATIVE_EXCLUDED: 0,
    parityPercent: 0,
    bySubsystem: {},
  };

  for (const row of rows) {
    base[row.outcome] += 1;
    const stats = base.bySubsystem[row.subsystem] ?? {
      total: 0,
      MATCH: 0,
      MISMATCH: 0,
      SIMULATED_DEPENDENCY: 0,
      BOTH_ERROR: 0,
      PY_ONLY_MISSING: 0,
      TS_ONLY_MISSING: 0,
      HOST_NATIVE_EXCLUDED: 0,
      parityPercent: 0,
    };
    stats.total += 1;
    stats[row.outcome] += 1;
    base.bySubsystem[row.subsystem] = stats;
  }

  const effectiveTotal = Math.max(0, base.total - base.HOST_NATIVE_EXCLUDED);
  base.parityPercent = effectiveTotal === 0 ? 0 : (base.MATCH / effectiveTotal) * 100;
  for (const stats of Object.values(base.bySubsystem)) {
    const subsystemEffectiveTotal = Math.max(0, stats.total - stats.HOST_NATIVE_EXCLUDED);
    stats.parityPercent = subsystemEffectiveTotal === 0 ? 0 : (stats.MATCH / subsystemEffectiveTotal) * 100;
  }
  return base;
}

function indexByVectorId(results) {
  return Object.fromEntries(results.map(result => [result.vectorId, result]));
}

function compareStructured(pyResult, tsResult, fields) {
  const pySignature = structuredSignature(pyResult, fields);
  const tsSignature = structuredSignature(tsResult, fields);
  const pyText = JSON.stringify(pySignature);
  const tsText = JSON.stringify(tsSignature);
  return {
    match: pyText === tsText,
    pythonHash: digest(pyText),
    tsHash: digest(tsText),
  };
}

function structuredSignature(result, fields) {
  const signature = {};
  for (const field of fields) {
    signature[field] = result?.[field] ?? null;
  }
  return signature;
}

function validateStructuredArtifacts(pyResult, tsResult, expectedStatus) {
  const status = normalizeStatus(expectedStatus || pyResult?.status || tsResult?.status);
  const problems = [];

  if (status === 'proved') {
    requireField(pyResult, 'python', 'proofHash', problems);
    requireField(tsResult, 'typescript', 'proofHash', problems);
    requireField(pyResult, 'python', 'derivationHash', problems);
    requireField(tsResult, 'typescript', 'derivationHash', problems);
  } else if (status === 'refuted') {
    requireField(pyResult, 'python', 'countermodelHash', problems);
    requireField(tsResult, 'typescript', 'countermodelHash', problems);
    requireField(pyResult, 'python', 'derivationHash', problems);
    requireField(tsResult, 'typescript', 'derivationHash', problems);
  } else if (status === 'sat') {
    requireField(pyResult, 'python', 'modelHash', problems);
    requireField(tsResult, 'typescript', 'modelHash', problems);
    requireField(pyResult, 'python', 'derivationHash', problems);
    requireField(tsResult, 'typescript', 'derivationHash', problems);
  }

  return { pass: problems.length === 0, problems };
}

function requireField(result, side, field, problems) {
  const value = result?.[field];
  if (typeof value !== 'string' || value.trim().length === 0) {
    problems.push(`${side}.${field}`);
  }
}

function normalizeStatus(value) {
  return String(value ?? '').trim().toLowerCase();
}

function digest(text) {
  return createHash('sha256').update(String(text ?? '')).digest('hex');
}

export function loadVectorExpectation(vectorsDir) {
  const payload = {};
  if (!vectorsDir) return payload;

  const vectors = loadVectors(vectorsDir);
  for (const vector of vectors) {
    payload[vector.id] = {
      strictStructuredParity: Boolean(vector?.expected?.strictStructuredParity),
      expectedStatus: typeof vector?.expected?.status === 'string' ? vector.expected.status : undefined,
      decided: vector?.expected?.decided === true,
      inputType: typeof vector?.inputType === 'string' ? vector.inputType : undefined,
      tags: Array.isArray(vector?.tags) ? vector.tags.map(tag => String(tag)) : [],
      backendMode: typeof vector?.expected?.backendMode === 'string' ? vector.expected.backendMode : undefined,
      excludeFromParityWhenSimulated: vector?.expected?.excludeFromParityWhenSimulated === true,
      structuredFields: Array.isArray(vector?.expected?.structuredFields)
        ? vector.expected.structuredFields
        : undefined,
    };
  }

  return payload;
}

function loadVectors(vectorsDir) {
  const files = readdirSync(resolve(vectorsDir)).filter(name => name.endsWith('.json')).sort();
  const vectors = [];
  for (const file of files) {
    const corpus = JSON.parse(readFileSync(resolve(vectorsDir, file), 'utf8'));
    if (!Array.isArray(corpus.vectors)) continue;
    vectors.push(...corpus.vectors);
  }
  return vectors;
}

function escapeTable(value) {
  return String(value ?? '').replace(/\|/g, '\\|');
}

function parseArgs(argv) {
  const args = {
    outDir: 'conformance',
    threshold: undefined,
    vectors: undefined,
    strictSelfContainment: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--python') args.python = argv[++i];
    else if (arg === '--ts') args.ts = argv[++i];
    else if (arg === '--vectors') args.vectors = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--threshold') args.threshold = Number(argv[++i]);
    else if (arg === '--strict-self-containment') args.strictSelfContainment = true;
    else if (arg === '--help') printHelpAndExit(0);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!args.python || !args.ts) throw new Error('Both --python and --ts result files are required');
  return args;
}

function printHelpAndExit(code) {
  console.log(`Usage: node implementation_plan/conformance/compare.mjs --python py.json --ts ts.json [options]

Options:
  --vectors <dir>      Optional vectors directory for strict structured parity flags
  --out-dir <dir>      Output directory for report.json and report.md
  --threshold <pct>    Fail when parity percentage is below this value
  --strict-self-containment
                       Disable host-native exclusions and force simulated matches to mismatch
`);
  process.exit(code);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const comparison = compareResults(
      loadResultEnvelope(args.python),
      loadResultEnvelope(args.ts),
      {
        vectorExpectation: loadVectorExpectation(args.vectors),
        strictSelfContainment: args.strictSelfContainment,
      },
    );
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
