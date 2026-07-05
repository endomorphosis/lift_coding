#!/usr/bin/env node
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = resolve(args.outDir);
  const symbolMap = loadJson(resolve(args.symbolMap));

  const hostNativeModuleMatchers = [
    module => module.startsWith('external_provers/'),
    module => module === 'flogic/ergoai_wrapper.py',
  ];

  const violations = [];
  const checkedSymbols = [];

  for (const mod of symbolMap?.modules ?? []) {
    const moduleName = String(mod?.pythonModule ?? '');
    if (!hostNativeModuleMatchers.some(match => match(moduleName))) continue;

    for (const symbol of mod?.symbols ?? []) {
      const symbolName = String(symbol?.pythonSymbol ?? '<unknown>');
      const status = String(symbol?.status ?? '');
      const reason = String(symbol?.reason ?? '').trim();
      checkedSymbols.push({ moduleName, symbolName, status });

      if (status !== 'n/a') {
        violations.push(`${moduleName}:${symbolName} status=${status} expected=n/a`);
        continue;
      }
      if (!reason) {
        violations.push(`${moduleName}:${symbolName} missing reason for n/a host-native classification`);
      }
    }
  }

  const gate = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    gate: 'port239-host-native-classification',
    passed: violations.length === 0,
    summary: {
      checkedSymbols: checkedSymbols.length,
      violations: violations.length,
    },
    checkedModules: [...new Set(checkedSymbols.map(row => row.moduleName))].sort(),
    sample: checkedSymbols.slice(0, 30),
    violations,
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'port239-host-native-gate.json'), JSON.stringify(gate, null, 2) + '\n', 'utf8');
  writeFileSync(resolve(outDir, 'port239-host-native-gate.md'), renderMarkdown(gate), 'utf8');

  console.log(JSON.stringify({ passed: gate.passed, checkedSymbols: gate.summary.checkedSymbols, violations: gate.summary.violations }, null, 2));

  if (!gate.passed) {
    throw new Error(`PORT-239 host-native gate failed: ${violations.slice(0, 10).join('; ')}${violations.length > 10 ? ' ...' : ''}`);
  }
}

function parseArgs(argv) {
  const args = {
    outDir: 'conformance',
    symbolMap: 'implementation_plan/conformance/symbol-map.json',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--symbol-map') args.symbolMap = argv[++i];
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
  console.log('Usage: node implementation_plan/conformance/port239_host_native_gate.mjs [--out-dir conformance] [--symbol-map implementation_plan/conformance/symbol-map.json]');
}

function renderMarkdown(gate) {
  const lines = [
    '# PORT-239 Host-Native Classification Gate',
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
    '## Violations',
    '',
  ];
  if (!gate.violations.length) {
    lines.push('None.');
  } else {
    for (const violation of gate.violations.slice(0, 200)) {
      lines.push(`- ${violation}`);
    }
    if (gate.violations.length > 200) {
      lines.push(`- ... ${gate.violations.length - 200} more`);
    }
  }
  lines.push('');
  return lines.join('\n');
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
