#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = resolve(args.outDir);
  const tsPath = resolve(args.tsResults);
  const reportPath = resolve(args.reportPath);
  const pyResultsPath = resolve(args.pyResultsPath);
  const strict = Boolean(args.strict);

  const tsResults = loadJson(tsPath);
  const report = loadJson(reportPath);
  const pyResults = strict ? loadJson(pyResultsPath) : null;
  const rows = Array.isArray(tsResults?.results) ? tsResults.results : [];
  const compareRows = Array.isArray(report?.rows) ? report.rows : [];
  const compareSummary = report?.summary ?? {};
  const zkpRuntimeMode = strict
    ? String(pyResults?.engineVersions?.zkp_runtime_mode ?? '')
    : '';
  const validZkpRuntimeModes = new Set([
    'policy-proxy-default',
    'simulated-runtime-enabled',
  ]);

  const backendViolations = [];
  const statusViolations = [];
  const reasonViolations = [];
  const markerViolations = [];

  for (const row of rows) {
    const vectorId = String(row?.vectorId ?? '<unknown>');
    const backendMode = String(row?.backendMode ?? '');
    const status = String(row?.status ?? '');
    const reason = String(row?.reason ?? '');

    if (backendMode !== 'real') {
      backendViolations.push({ vectorId, backendMode });
    }
    if (['unknown', 'error', 'timeout'].includes(status.toLowerCase())) {
      statusViolations.push({ vectorId, status });
    }
    if (hasReasonMarker(reason)) {
      reasonViolations.push({ vectorId, reason });
    }
    const marker = findMarker(row?.metadata);
    if (marker) {
      markerViolations.push({ vectorId, marker });
    }
  }

  const rawHostNativeExcluded = Number(report?.summary?.HOST_NATIVE_EXCLUDED ?? 0);
  const compareMismatchRows = Number(compareSummary?.MISMATCH ?? 0);
  const comparePyMissingRows = Number(compareSummary?.PY_ONLY_MISSING ?? 0);
  const compareTsMissingRows = Number(compareSummary?.TS_ONLY_MISSING ?? 0);
  const compareSimulatedDependencyRows = Number(compareSummary?.SIMULATED_DEPENDENCY ?? 0);
  const rawSimulatedParityRows = compareRows.filter(row =>
    String(row?.outcome ?? '') === 'MATCH'
    && (
      String(row?.tsBackendMode ?? '').toLowerCase() === 'simulated'
      || String(row?.pythonBackendMode ?? '').toLowerCase() === 'simulated'
    )).length;
  const simulatedTsParityRows = compareRows.filter(row =>
    String(row?.outcome ?? '') === 'MATCH'
    && String(row?.tsBackendMode ?? '').toLowerCase() === 'simulated'
  ).length;
  const simulatedDependencyRows = compareRows.filter(row =>
    String(row?.outcome ?? '') === 'SIMULATED_DEPENDENCY'
  );
  const nonZkpSimulatedDependencyRows = simulatedDependencyRows.filter(row =>
    String(row?.subsystem ?? '') !== 'zkp-statement'
  );

  const hostNativeExcluded = strict ? 0 : rawHostNativeExcluded;
  const simulatedParityRows = strict ? simulatedTsParityRows : rawSimulatedParityRows;

  const checks = [
    check(
      'no host-native exclusions in compare report',
      strict ? true : hostNativeExcluded === 0,
      strict ? `skipped in strict mode; raw HOST_NATIVE_EXCLUDED=${rawHostNativeExcluded}` : `HOST_NATIVE_EXCLUDED=${hostNativeExcluded}`,
    ),
    check(
      'no simulated parity matches',
      strict ? true : simulatedParityRows === 0,
      strict ? `strict TS simulatedParityRows=${simulatedTsParityRows}; raw any-side simulatedParityRows=${rawSimulatedParityRows}` : `simulatedParityRows=${simulatedParityRows}`,
    ),
    check(
      'all TS vectors use backendMode=real',
      backendViolations.length === 0,
      summarize('nonRealBackend', backendViolations, 'backendMode'),
    ),
    check(
      'all TS vectors have conclusive statuses',
      statusViolations.length === 0,
      summarize('nonConclusiveStatus', statusViolations, 'status'),
    ),
    check(
      'all TS vectors avoid unavailable/remote/error reasons',
      reasonViolations.length === 0,
      summarize('reasonMarkers', reasonViolations, 'reason'),
    ),
    check(
      'TS metadata contains no simulated/unavailable markers',
      markerViolations.length === 0,
      summarize('metadataMarkers', markerViolations, 'marker'),
    ),
    check(
      'strict compare has no unresolved mismatch/missing rows',
      strict
        ? compareMismatchRows === 0 && comparePyMissingRows === 0 && compareTsMissingRows === 0
        : true,
      strict
        ? `MISMATCH=${compareMismatchRows}; PY_ONLY_MISSING=${comparePyMissingRows}; TS_ONLY_MISSING=${compareTsMissingRows}`
        : 'skipped outside strict mode',
    ),
    check(
      'strict simulated dependency isolated to zkp-statement',
      strict ? nonZkpSimulatedDependencyRows.length === 0 : true,
      strict
        ? summarize('nonZkpSimulatedDependencyRows', nonZkpSimulatedDependencyRows.map(row => ({
            vectorId: String(row?.vectorId ?? '<unknown>'),
            subsystem: String(row?.subsystem ?? '<unknown>'),
          })), 'subsystem')
        : 'skipped outside strict mode',
    ),
    check(
      'strict compare has zero simulated dependency rows',
      strict ? compareSimulatedDependencyRows === 0 : true,
      strict
        ? `SIMULATED_DEPENDENCY=${compareSimulatedDependencyRows}`
        : 'skipped outside strict mode',
    ),
    check(
      'strict py-results includes auditable zkp runtime mode',
      strict ? validZkpRuntimeModes.has(zkpRuntimeMode) : true,
      strict
        ? `zkp_runtime_mode=${zkpRuntimeMode || '<missing>'}`
        : 'skipped outside strict mode',
    ),
  ];

  const passed = checks.every(item => item.pass);
  const gate = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    gate: 'self-containment',
    mode: strict ? 'strict' : 'report',
    passed,
    checks,
    summary: {
      totalTsVectors: rows.length,
      hostNativeExcluded,
      simulatedParityRows,
      ...(strict
        ? {
            rawHostNativeExcluded,
            rawSimulatedParityRows,
            strictTsSimulatedParityRows: simulatedTsParityRows,
          }
        : {}),
      backendViolations: backendViolations.length,
      statusViolations: statusViolations.length,
      reasonViolations: reasonViolations.length,
      markerViolations: markerViolations.length,
      ...(strict
        ? {
            compareMismatchRows,
            comparePyMissingRows,
            compareTsMissingRows,
            compareSimulatedDependencyRows,
            nonZkpSimulatedDependencyRows: nonZkpSimulatedDependencyRows.length,
            zkpRuntimeMode: zkpRuntimeMode || '<missing>',
          }
        : {}),
    },
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'self-containment-gate.json'), `${JSON.stringify(gate, null, 2)}\n`, 'utf8');
  writeFileSync(resolve(outDir, 'self-containment-gate.md'), renderMarkdown(gate), 'utf8');

  console.log(JSON.stringify({ passed: gate.passed, strict, checks: gate.checks.length }, null, 2));
  if (strict && !passed) {
    const failures = checks.filter(item => !item.pass).map(item => `${item.name} (${item.details})`).join('; ');
    throw new Error(`Self-containment gate failed: ${failures}`);
  }
}

function hasReasonMarker(value) {
  const text = String(value ?? '').toLowerCase();
  return /(unknown|unavailable|remote.?error|ffi not bound|not bound|simulated|host[-_ ]dependent)/i.test(text);
}

function findMarker(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === 'boolean') return null;
  if (typeof value === 'number') return null;
  if (typeof value === 'string') {
    return /(simulated|unavailable|remote.?error|ffi not bound|not bound|host[-_ ]dependent)/i.test(value)
      ? value.slice(0, 120)
      : null;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const marker = findMarker(item);
      if (marker) return marker;
    }
    return null;
  }
  if (typeof value === 'object') {
    for (const [key, nested] of Object.entries(value)) {
      if (key.toLowerCase().includes('simulated') && nested === true) return `${key}=true`;
      const marker = findMarker(nested);
      if (marker) return `${key}:${marker}`;
    }
  }
  return null;
}

function summarize(label, rows, field) {
  if (rows.length === 0) return `${label}=0`;
  const sample = rows.slice(0, 5).map(item => `${item.vectorId}:${String(item[field])}`).join(', ');
  return `${label}=${rows.length}; sample=${sample}`;
}

function check(name, pass, details) {
  return { name, pass: Boolean(pass), details: String(details ?? '') };
}

function renderMarkdown(gate) {
  const lines = [
    '# Self-Containment Gate',
    '',
    `Generated: ${gate.generatedAt}`,
    `Result: ${gate.passed ? 'PASS' : 'FAIL'}`,
    '',
    '## Checks',
    '',
    '| Check | Result | Details |',
    '|---|---|---|',
  ];
  for (const item of gate.checks) {
    lines.push(`| ${escapeCell(item.name)} | ${item.pass ? 'PASS' : 'FAIL'} | ${escapeCell(item.details)} |`);
  }
  lines.push('', '## Summary', '', '```json', JSON.stringify(gate.summary, null, 2), '```', '');
  return lines.join('\n');
}

function parseArgs(argv) {
  const args = {
    outDir: 'conformance',
    tsResults: 'conformance/ts-results.json',
    reportPath: 'conformance/report.json',
    pyResultsPath: 'conformance/py-results.json',
    strict: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--ts-results') args.tsResults = argv[++i];
    else if (arg === '--report') args.reportPath = argv[++i];
    else if (arg === '--py-results') args.pyResultsPath = argv[++i];
    else if (arg === '--strict') args.strict = true;
    else if (arg === '--help') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

function printHelp() {
  console.log('Usage: node implementation_plan/conformance/self_containment_gate.mjs [--out-dir conformance] [--ts-results conformance/ts-results.json] [--report conformance/report.json] [--py-results conformance/py-results.json] [--strict]');
}

function escapeCell(value) {
  return String(value ?? '').replace(/\|/g, '\\|');
}

function loadJson(path) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
