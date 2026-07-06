#!/usr/bin/env node
import { readFileSync, readdirSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const symbolMap = loadJson(resolve(args.symbolMap));
  const evidenceMap = loadJson(resolve(args.evidenceMap));
  const tsResults = loadJson(resolve(args.tsResults));
  const vectorsById = loadVectorsById(resolve(args.vectorsDir));
  const executedTargets = loadExecutedTargets(resolve(args.v8CoverageDir));

  const executedVectorIds = new Set((tsResults?.results ?? []).map(row => String(row?.vectorId ?? '')).filter(Boolean));
  const executedInputTypes = new Set();
  for (const vectorId of executedVectorIds) {
    const inputType = vectorsById.get(vectorId)?.inputType;
    if (inputType) executedInputTypes.add(inputType);
  }

  const rules = Array.isArray(evidenceMap?.moduleRules) ? evidenceMap.moduleRules : [];
  const failures = [];
  const coveredRules = [];

  for (const rule of rules) {
    const scope = String(rule?.coverageScope ?? 'baseline');
    if (scope !== 'core') continue;

    const prefix = String(rule?.modulePrefix ?? '');
    const requiredTargets = (rule?.requiredExecutedTargets ?? []).map(String).filter(Boolean);
    const requiredInputTypes = (rule?.coveringInputTypes ?? []).map(String).filter(Boolean);

    const hasMappedSymbols = moduleHasPortedSymbols(symbolMap, prefix);
    if (!hasMappedSymbols) continue;

    if (requiredTargets.length === 0) {
      failures.push(`core rule ${prefix || '<root>'} must declare requiredExecutedTargets`);
      continue;
    }

    const missingTargets = requiredTargets.filter(target => !executedTargets.has(target));
    if (missingTargets.length > 0) {
      failures.push(`core rule ${prefix || '<root>'} missing executed targets: ${missingTargets.join(', ')}`);
    }

    const missingInputTypes = requiredInputTypes.filter(inputType => !executedInputTypes.has(inputType));
    if (missingInputTypes.length > 0) {
      failures.push(`core rule ${prefix || '<root>'} missing executed input types: ${missingInputTypes.join(', ')}`);
    }

    coveredRules.push({
      modulePrefix: prefix,
      requiredTargets,
      missingTargets,
      requiredInputTypes,
      missingInputTypes,
    });
  }

  const report = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    passed: failures.length === 0,
    summary: {
      executedVectorCount: executedVectorIds.size,
      executedInputTypeCount: executedInputTypes.size,
      executedTargetCount: executedTargets.size,
      coreRuleCount: coveredRules.length,
      failureCount: failures.length,
    },
    coveredRules,
    failures,
  };

  const outPath = resolve(args.out);
  mkdirSync(resolve(outPath, '..'), { recursive: true });
  writeFileSync(outPath, JSON.stringify(report, null, 2) + '\n', 'utf8');

  if (!report.passed) {
    throw new Error(`TS coverage reconciliation failed (${failures.length}): ${failures.join('; ')}`);
  }

  console.log(JSON.stringify({ passed: report.passed, coreRules: coveredRules.length }, null, 2));
}

function moduleHasPortedSymbols(symbolMap, modulePrefix) {
  for (const mod of symbolMap?.modules ?? []) {
    const moduleName = String(mod?.pythonModule ?? '');
    if (modulePrefix && !moduleName.startsWith(modulePrefix)) continue;
    if (!modulePrefix && moduleName.length === 0) continue;
    for (const symbol of mod?.symbols ?? []) {
      const status = String(symbol?.status ?? '');
      if (status === 'ported' || status === 'consolidated') return true;
    }
  }
  return false;
}

function loadVectorsById(vectorsDir) {
  const byId = new Map();
  for (const file of readdirSync(vectorsDir).filter(name => name.endsWith('.json')).sort()) {
    const payload = loadJson(resolve(vectorsDir, file));
    for (const vector of payload?.vectors ?? []) {
      const id = String(vector?.id ?? '');
      const inputType = String(vector?.inputType ?? '');
      if (!id) continue;
      byId.set(id, { inputType });
    }
  }
  return byId;
}

function loadExecutedTargets(v8CoverageDir) {
  const targets = new Set();
  const files = readdirSync(v8CoverageDir).filter(name => name.endsWith('.json'));
  for (const file of files) {
    const payload = loadJson(resolve(v8CoverageDir, file));
    for (const row of payload?.result ?? []) {
      const normalized = normalizeCoverageUrl(String(row?.url ?? ''));
      if (!normalized) continue;
      targets.add(normalized);
    }
  }
  return targets;
}

function normalizeCoverageUrl(url) {
  if (!url.includes('/swissknife/')) return null;
  let value = url;
  if (value.startsWith('file://')) value = value.slice('file://'.length);
  const idx = value.indexOf('/swissknife/');
  if (idx < 0) return null;
  const normalized = value.slice(idx + 1);
  if (!normalized.startsWith('swissknife/src/services/')) return null;
  if (!(normalized.endsWith('.ts') || normalized.endsWith('.tsx') || normalized.endsWith('.js') || normalized.endsWith('.jsx'))) {
    return null;
  }
  return normalized;
}

function parseArgs(argv) {
  const args = {
    symbolMap: 'implementation_plan/conformance/symbol-map.json',
    evidenceMap: 'implementation_plan/conformance/symbol-evidence.json',
    tsResults: 'conformance/ts-results.json',
    vectorsDir: 'implementation_plan/conformance/vectors',
    v8CoverageDir: 'conformance/v8-coverage',
    out: 'conformance/ts-coverage-reconciliation.json',
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--symbol-map') args.symbolMap = argv[++i];
    else if (arg === '--evidence-map') args.evidenceMap = argv[++i];
    else if (arg === '--ts-results') args.tsResults = argv[++i];
    else if (arg === '--vectors') args.vectorsDir = argv[++i];
    else if (arg === '--v8-coverage-dir') args.v8CoverageDir = argv[++i];
    else if (arg === '--out') args.out = argv[++i];
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
  console.log('Usage: node implementation_plan/conformance/coverage_reconciliation.mjs [--symbol-map path] [--evidence-map path] [--ts-results path] [--vectors dir] [--v8-coverage-dir dir] [--out path]');
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
