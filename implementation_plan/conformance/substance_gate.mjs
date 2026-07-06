#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const FLAGGED_VERDICTS = new Set(['MISSING', 'WRAPPER', 'HOLLOW', 'THIN']);
const DEFAULT_CLASSIFICATIONS = new Set(['consolidated', 'compact-faithful', 'host-native', 'data-bloat', 'simulated']);

function main() {
  const args = parseArgs(process.argv.slice(2));
  const audit = loadJson(resolve(args.audit));
  const substanceMap = loadJson(resolve(args.substanceMap));
  const evidenceMap = loadJson(resolve(args.evidenceMap));

  const knownTestIds = new Set((evidenceMap?.knownTestIds ?? []).map(String));
  const allowedClassifications = new Set(
    (substanceMap?.allowedClassifications ?? [...DEFAULT_CLASSIFICATIONS]).map(String),
  );
  const entries = Array.isArray(substanceMap?.entries) ? substanceMap.entries : [];
  const entryByModule = new Map();
  const violations = [];
  const warnings = [];

  for (const entry of entries) {
    const moduleName = String(entry?.module ?? '').trim();
    if (!moduleName) {
      violations.push('substance-map entry missing module');
      continue;
    }
    if (entryByModule.has(moduleName)) {
      violations.push(`duplicate substance-map entry for ${moduleName}`);
      continue;
    }
    entryByModule.set(moduleName, entry);
  }

  const flaggedRows = [];
  const coveredRows = [];
  const classificationCounts = {};
  const auditRows = Array.isArray(audit?.modules) ? audit.modules : [];
  for (const row of auditRows) {
    const verdict = String(row?.verdict ?? '');
    if (!FLAGGED_VERDICTS.has(verdict)) continue;
    flaggedRows.push(row);

    const moduleName = String(row?.module ?? '').trim();
    const entry = entryByModule.get(moduleName);
    if (!entry) {
      violations.push(`${moduleName} verdict=${verdict} missing substance-map entry`);
      continue;
    }

    const classification = String(entry?.classification ?? '').trim();
    const reason = String(entry?.reason ?? '').trim();
    const testIds = Array.isArray(entry?.testIds) ? entry.testIds.map(String).filter(Boolean) : [];
    classificationCounts[classification] = Number(classificationCounts[classification] ?? 0) + 1;

    if (!allowedClassifications.has(classification)) {
      violations.push(`${moduleName} has invalid classification=${classification || '<empty>'}`);
    }
    if (classification === 'simulated') {
      violations.push(`${moduleName} classification=simulated cannot satisfy the substance gate`);
    }
    if (reason.length < 20) {
      violations.push(`${moduleName} must cite a non-trivial reason`);
    }
    if (testIds.length === 0) {
      violations.push(`${moduleName} must cite at least one behavioral conformance test id`);
    }
    for (const testId of testIds) {
      if (!knownTestIds.has(testId)) {
        violations.push(`${moduleName} cites unknown test id ${testId}`);
      }
    }

    coveredRows.push({
      module: moduleName,
      verdict,
      pyLoc: Number(row?.pyLoc ?? 0),
      tsLoc: Number(row?.tsLoc ?? 0),
      locRatio: Number(row?.locRatio ?? 0),
      classification,
      testIds,
      reason,
    });
  }

  const flaggedModules = new Set(flaggedRows.map(row => String(row?.module ?? '').trim()).filter(Boolean));
  for (const moduleName of entryByModule.keys()) {
    if (!flaggedModules.has(moduleName)) {
      warnings.push(`${moduleName} has a substance-map entry but is not currently flagged by the audit`);
    }
  }

  const gate = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    gate: 'port-substance-ratio',
    passed: violations.length === 0,
    inputs: {
      audit: resolve(args.audit),
      substanceMap: resolve(args.substanceMap),
      evidenceMap: resolve(args.evidenceMap),
    },
    summary: {
      totalAuditModules: auditRows.length,
      flaggedModules: flaggedRows.length,
      classifiedFlaggedModules: coveredRows.length,
      substanceMapEntries: entryByModule.size,
      classifications: sortObject(classificationCounts),
      violations: violations.length,
      warnings: warnings.length,
    },
    coveredRows: coveredRows.sort((a, b) => a.module.localeCompare(b.module)),
    violations,
    warnings,
  };

  const outPath = resolve(args.out);
  mkdirSync(dirname(outPath), { recursive: true });
  writeFileSync(outPath, JSON.stringify(gate, null, 2) + '\n', 'utf8');
  writeFileSync(outPath.replace(/\.json$/i, '.md'), renderMarkdown(gate), 'utf8');

  console.log(JSON.stringify({
    passed: gate.passed,
    flaggedModules: gate.summary.flaggedModules,
    classifiedFlaggedModules: gate.summary.classifiedFlaggedModules,
    violations: gate.summary.violations,
  }, null, 2));

  if (!gate.passed) {
    const sample = violations.slice(0, 12).join('; ');
    throw new Error(`Substance gate failed (${violations.length}): ${sample}${violations.length > 12 ? ' ...' : ''}`);
  }
}

function renderMarkdown(gate) {
  const lines = [
    '# Port Substance Gate',
    '',
    `Generated: ${gate.generatedAt}`,
    `Result: ${gate.passed ? 'PASS' : 'FAIL'}`,
    '',
    '## Summary',
    '',
    '```json',
    JSON.stringify(gate.summary, null, 2),
    '```',
    '',
    '## Classifications',
    '',
    '| Module | Audit Verdict | Class | Test IDs | Reason |',
    '|---|---|---|---|---|',
  ];

  for (const row of gate.coveredRows) {
    lines.push(`| ${escapeCell(row.module)} | ${escapeCell(row.verdict)} | ${escapeCell(row.classification)} | ${escapeCell(row.testIds.join(', '))} | ${escapeCell(row.reason)} |`);
  }

  lines.push('', '## Violations', '');
  if (gate.violations.length === 0) {
    lines.push('None.');
  } else {
    for (const violation of gate.violations) lines.push(`- ${violation}`);
  }

  if (gate.warnings.length > 0) {
    lines.push('', '## Warnings', '');
    for (const warning of gate.warnings) lines.push(`- ${warning}`);
  }

  lines.push('');
  return lines.join('\n');
}

function sortObject(value) {
  return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)));
}

function escapeCell(value) {
  return String(value ?? '').replace(/\|/g, '\\|');
}

function parseArgs(argv) {
  const args = {
    audit: 'implementation_plan/port-audit/port-substance.json',
    substanceMap: 'implementation_plan/conformance/substance-map.json',
    evidenceMap: 'implementation_plan/conformance/symbol-evidence.json',
    out: 'conformance/port-substance-gate.json',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--audit') args.audit = argv[++i];
    else if (arg === '--substance-map') args.substanceMap = argv[++i];
    else if (arg === '--evidence-map') args.evidenceMap = argv[++i];
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
  console.log('Usage: node implementation_plan/conformance/substance_gate.mjs [--audit implementation_plan/port-audit/port-substance.json] [--substance-map implementation_plan/conformance/substance-map.json] [--evidence-map implementation_plan/conformance/symbol-evidence.json] [--out conformance/port-substance-gate.json]');
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
