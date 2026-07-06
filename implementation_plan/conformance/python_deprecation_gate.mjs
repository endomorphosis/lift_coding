#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const RUNTIME_PYTHON_PATTERNS = [
  /\bentrypoint:\s*['"]python['"]/,
  /\bpython\s+-m\s+ipfs_datasets_py\b/,
  /\bpy_reference_runner\.py\b/,
  /\bexternal\/ipfs_datasets\b/,
];

const ALLOWED_RUNTIME_SURFACES = [
  /swissknife\/src\/services\/mcp-remote-deontic-engine\.ts$/,
  /swissknife\/src\/services\/swissknife-mcp-capability-registry\.ts$/,
];

const BROWSER_CRITICAL_FILES = [
  'swissknife/src/services/mcp-wasm-prover-hub.ts',
  'swissknife/src/services/flogic-zkp-integration.ts',
  'swissknife/src/services/zkp-attestation-bridge.ts',
  'swissknife/src/services/zkp-circuits.ts',
  'swissknife/src/services/zkp-onchain-pipeline.ts',
  'swissknife/src/services/zkp-provekit-cache.ts',
  'swissknife/src/services/zkp-provekit-public-inputs.ts',
  'swissknife/src/services/zkp/zkp-ucan-bridge.ts',
];

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = resolve(args.root);
  const outDir = resolve(root, args.outDir);

  const makefilePath = resolve(root, 'Makefile');
  const makefile = existsSync(makefilePath) ? readFileSync(makefilePath, 'utf8') : '';
  const makefileNoComments = stripComments(makefile);
  const conformanceLine = findLine(makefileNoComments, /^conformance:.*$/m);
  const selfContainmentLine = findLine(makefileNoComments, /^conformance-self-containment:.*$/m);

  const browserPythonHits = BROWSER_CRITICAL_FILES
    .filter(path => existsSync(resolve(root, path)))
    .map(path => {
      const source = stripComments(readFileSync(resolve(root, path), 'utf8'));
      const markers = RUNTIME_PYTHON_PATTERNS.filter(pattern => pattern.test(source)).map(pattern => pattern.source);
      return markers.length ? { file: path, markers } : null;
    })
    .filter(Boolean);

  const checks = [
    check(
      'default conformance target excludes conformance-py',
      !/\bconformance-py\b/.test(conformanceLine),
      conformanceLine || '<missing conformance line>',
    ),
    check(
      'strict self-containment target excludes conformance-py prerequisite',
      !/\bconformance-py\b/.test(selfContainmentLine),
      selfContainmentLine || '<missing self-containment line>',
    ),
    check(
      'browser-critical TS/WASM runtime paths have no Python execution hooks',
      browserPythonHits.length === 0,
      summarizeRows(browserPythonHits),
    ),
    check(
      'remaining runtime Python hooks are isolated to explicitly allowed compatibility surfaces',
      runtimePythonHits(root).every(hit => ALLOWED_RUNTIME_SURFACES.some(pattern => pattern.test(hit.file))),
      summarizeRows(runtimePythonHits(root)),
    ),
  ];

  const gate = {
    schemaVersion: '2026-07-06',
    generatedAt: new Date().toISOString(),
    gate: 'python-deprecation',
    passed: checks.every(row => row.pass),
    checks,
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'python-deprecation-gate.json'), `${JSON.stringify(gate, null, 2)}\n`, 'utf8');
  writeFileSync(resolve(outDir, 'python-deprecation-gate.md'), renderMarkdown(gate), 'utf8');

  console.log(JSON.stringify({
    passed: gate.passed,
    checks: gate.checks.length,
    failingChecks: gate.checks.filter(row => !row.pass).map(row => row.name),
  }, null, 2));

  if (args.failOnGap && !gate.passed) {
    const failing = gate.checks
      .filter(row => !row.pass)
      .map(row => `${row.name}: ${row.details}`)
      .join('; ');
    throw new Error(`Python deprecation gate failed: ${failing}`);
  }
}

function runtimePythonHits(root) {
  const files = [
    'swissknife/src/services/mcp-remote-deontic-engine.ts',
    'swissknife/src/services/swissknife-mcp-capability-registry.ts',
    'swissknife/src/services/mcp-wasm-prover-hub.ts',
    'swissknife/src/services/zkp/zkp-ucan-bridge.ts',
  ].filter(path => existsSync(resolve(root, path)));

  return files
    .map(path => {
      const source = stripComments(readFileSync(resolve(root, path), 'utf8'));
      const markers = RUNTIME_PYTHON_PATTERNS.filter(pattern => pattern.test(source)).map(pattern => pattern.source);
      return markers.length ? { file: path, markers } : null;
    })
    .filter(Boolean);
}

function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1');
}

function findLine(source, pattern) {
  const match = source.match(pattern);
  return match ? String(match[0]).trim() : '';
}

function summarizeRows(rows) {
  if (!rows.length) return 'none';
  const sample = rows.slice(0, 8).map(row => row.file).join(', ');
  return `${rows.length}; sample=${sample}${rows.length > 8 ? ', ...' : ''}`;
}

function check(name, pass, details) {
  return { name, pass: Boolean(pass), details: String(details ?? '') };
}

function renderMarkdown(gate) {
  const lines = [
    '# Python Deprecation Gate',
    '',
    `Generated: ${gate.generatedAt}`,
    `Result: ${gate.passed ? 'PASS' : 'FAIL'}`,
    '',
    '| Check | Result | Details |',
    '|---|---|---|',
  ];
  for (const row of gate.checks) {
    lines.push(`| ${escapeCell(row.name)} | ${row.pass ? 'PASS' : 'FAIL'} | ${escapeCell(row.details)} |`);
  }
  lines.push('');
  return lines.join('\n');
}

function escapeCell(value) {
  return String(value ?? '').replace(/\|/g, '\\|').replace(/\n/g, '<br>');
}

function parseArgs(argv) {
  const args = {
    root: process.cwd(),
    outDir: 'conformance',
    failOnGap: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--root') args.root = argv[++i];
    else if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--fail-on-gap') args.failOnGap = true;
    else if (arg === '--help') {
      console.log('Usage: node implementation_plan/conformance/python_deprecation_gate.mjs [--root .] [--out-dir conformance] [--fail-on-gap]');
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  return args;
}

try {
  main();
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
}
