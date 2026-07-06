#!/usr/bin/env node
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { extname, relative, resolve } from 'node:path';

const REAL_ZKP_DEPENDENCIES = [
  'snarkjs',
  'ffjavascript',
  'circomlibjs',
  '@noir-lang/noir_js',
  '@noir-lang/backend_barretenberg',
  '@aztec/bb.js',
  '@iden3/js-crypto',
];

const BROWSER_ZKP_IMPL_PATTERNS = [
  /\bclass\s+\w*(?:Browser|Wasm|Snark|Snarkjs|Noir|Barretenberg)\w*(?:Backend|Prover|Verifier)\b/i,
  /\bgroth16\.(?:fullProve|prove|verify)\b/,
  /\b(?:Noir|BarretenbergBackend)\b/,
];

const SIMULATED_ZKP_PATTERNS = [
  /\bZkpSimulatedProver\b/,
  /\bSimulatedZKPBackend\b/,
  /\bGroth16BackendFallback\b/,
  /\bdecodeSimulatedProofLayout\b/,
  /\bis_simulation:\s*true\b/,
  /\bbackend:\s*['"]simulated['"]/,
  /\bproofType:\s*['"]simulated['"]/,
  /\bverifier_id:\s*['"]simulated-zkp-v0\.1['"]/,
];

const RUNTIME_PYTHON_PATTERNS = [
  /\bentrypoint:\s*['"]python\b/,
  /\b(?:invokeTool|callTool|dispatch)\s*\([^)]*['"](?:tdfol_prove|tdfol_batch_prove|legal_text_to_deontic|logic_health)['"]/s,
  /\bpython\s+-m\s+ipfs_datasets_py\b/,
];

const BROWSER_FACING_ZKP_FILES = [
  'swissknife/src/services/flogic-zkp-integration.ts',
  'swissknife/src/services/cec-zkp-integration.ts',
  'swissknife/src/services/zkp-attestation-bridge.ts',
  'swissknife/src/services/zkp-onchain-pipeline.ts',
  'swissknife/src/services/zkp-ucan-bridge.ts',
  'swissknife/src/services/zkp-provekit-cache.ts',
  'swissknife/src/services/zkp-provekit-public-inputs.ts',
  'swissknife/src/services/zkp/browser-snarkjs-backend.ts',
  'swissknife/src/services/zkp/zkp-ucan-bridge.ts',
];

const SIMULATION_ALLOWED_FILES = new Set([
  'swissknife/src/services/zkp/zkp-simulated-prover.ts',
  'swissknife/src/services/zkp/zkp-types.ts',
  'swissknife/src/services/zkp-circuits.ts',
  'swissknife/src/services/zkp-backends.ts',
  'swissknife/src/services/tdfol-zkp-integration.ts',
]);

function main() {
  const args = parseArgs(process.argv.slice(2));
  const root = resolve(args.root);
  const outDir = resolve(root, args.outDir);
  const swissknifeRoot = resolve(root, 'swissknife');
  const servicesRoot = resolve(swissknifeRoot, 'src/services');

  const serviceFiles = listFiles(servicesRoot)
    .filter(path => ['.ts', '.tsx', '.js', '.mjs', '.cjs'].includes(extname(path)));
  const swissknifeFiles = listFiles(swissknifeRoot, ['node_modules', '.git', 'coverage', 'dist', 'build']);
  const packageDeps = readPackageDeps(resolve(swissknifeRoot, 'package.json'));

  const realDeps = REAL_ZKP_DEPENDENCIES.filter(dep => packageDeps.has(dep));
  const zkpArtifacts = swissknifeFiles
    .filter(path => /\.(wasm|zkey|r1cs|vk|pk)$/i.test(path) || /(?:proving|verification|verifying)[-_]?key/i.test(path))
    .map(path => relative(root, path))
    .filter(path => !path.includes('/node_modules/'));
  const zkpArtifactRefs = serviceFiles
    .filter(path => /zkp|groth|snark|noir|barretenberg/i.test(path))
    .map(path => {
      const rel = relative(root, path);
      const source = readFileSync(path, 'utf8');
      const markers = [];
      if (/\.wasm\b|WASM_PATH|wasmPath/.test(source)) markers.push('wasm-ref');
      if (/\.zkey\b|ZKEY_PATH|zkeyPath/.test(source)) markers.push('zkey-ref');
      if (/verification[_-]?key|VK_PATH|verificationKeyPath/.test(source)) markers.push('vk-ref');
      return markers.length ? { file: rel, markers } : null;
    })
    .filter(Boolean);

  const browserRealImplHits = serviceFiles
    .filter(path => /zkp|groth|provekit|snark|noir|barretenberg/i.test(path))
    .filter(path => {
      const source = readFileSync(path, 'utf8');
      return BROWSER_ZKP_IMPL_PATTERNS.some(pattern => pattern.test(source))
        && !/node:(?:child_process|fs|crypto|path|os)|from\s+['"]crypto['"]|spawnSync|execFile|existsSync/.test(source);
    })
    .map(path => relative(root, path));

  const simulationConsumers = serviceFiles
    .filter(path => /zkp|groth|provekit|lurk|stark|sphinx/i.test(path))
    .map(path => {
      const rel = relative(root, path);
      if (SIMULATION_ALLOWED_FILES.has(rel)) return null;
      const source = readFileSync(path, 'utf8');
      const markers = SIMULATED_ZKP_PATTERNS
        .filter(pattern => pattern.test(source))
        .map(pattern => pattern.source);
      return markers.length ? { file: rel, markers } : null;
    })
    .filter(Boolean);

  const nativeBinaryBackends = serviceFiles
    .filter(path => /zkp|groth|provekit/i.test(path))
    .map(path => {
      const source = readFileSync(path, 'utf8');
      const rel = relative(root, path);
      const markers = [];
      if (/node:child_process|spawnSync|execFile/.test(source)) markers.push('child_process');
      if (/node:fs|existsSync|readFileSync|writeFileSync/.test(source)) markers.push('filesystem');
      if (/node:crypto|from\s+['"]crypto['"]|createHash/.test(source)) markers.push('node-crypto');
      return markers.length ? { file: rel, markers } : null;
    })
    .filter(Boolean);

  const browserZkpPythonHits = BROWSER_FACING_ZKP_FILES
    .filter(rel => existsSync(resolve(root, rel)))
    .map(rel => {
      const source = readFileSync(resolve(root, rel), 'utf8');
      const markers = RUNTIME_PYTHON_PATTERNS
        .filter(pattern => pattern.test(source))
        .map(pattern => pattern.source);
      return markers.length ? { file: rel, markers } : null;
    })
    .filter(Boolean);

  const runtimePythonHits = serviceFiles
    .map(path => {
      const rel = relative(root, path);
      const source = stripComments(readFileSync(path, 'utf8'));
      const markers = RUNTIME_PYTHON_PATTERNS
        .filter(pattern => pattern.test(source))
        .map(pattern => pattern.source);
      return markers.length ? { file: rel, markers } : null;
    })
    .filter(Boolean);

  const checks = [
    check(
      'browser-facing ZKP files do not call Python runtimes',
      browserZkpPythonHits.length === 0,
      summarizeRows(browserZkpPythonHits, 'file'),
    ),
    check(
      'runtime Python calls are isolated to deprecated compatibility surfaces',
      runtimePythonHits.every(row => /mcp-remote-deontic-engine\.ts|swissknife-mcp-capability-registry\.ts/.test(row.file)),
      summarizeRows(runtimePythonHits, 'file'),
    ),
    check(
      'real browser ZKP dependency is present',
      realDeps.length > 0,
      realDeps.length ? realDeps.join(', ') : `missing any of: ${REAL_ZKP_DEPENDENCIES.join(', ')}`,
    ),
    check(
      'browser ZKP proving artifacts or explicit artifact references are present',
      zkpArtifacts.some(path => /\.(wasm|zkey|r1cs)$/i.test(path)) || zkpArtifactRefs.length > 0,
      [
        zkpArtifacts.length ? `artifacts=${zkpArtifacts.slice(0, 10).join(', ')}` : 'artifacts=none',
        zkpArtifactRefs.length ? `refs=${summarizeRows(zkpArtifactRefs, 'file')}` : 'refs=none',
      ].join('; '),
    ),
    check(
      'browser-real ZKP backend implementation is present',
      browserRealImplHits.length > 0,
      browserRealImplHits.length ? browserRealImplHits.join(', ') : 'no browser/WASM Groth16/Noir/SnarkJS backend implementation found',
    ),
    check(
      'production ZKP service paths do not consume simulated provers',
      simulationConsumers.length === 0,
      summarizeRows(simulationConsumers, 'file'),
    ),
    check(
      'native-binary ZKP adapters are not the only real backend',
      nativeBinaryBackends.length === 0 || browserRealImplHits.length > 0,
      summarizeRows(nativeBinaryBackends, 'file'),
    ),
  ];

  const gate = {
    schemaVersion: '2026-07-06',
    generatedAt: new Date().toISOString(),
    gate: 'zkp-real-browser-backend',
    passed: checks.every(row => row.pass),
    checks,
    summary: {
      realDeps,
      zkpArtifacts,
      zkpArtifactRefs,
      browserRealImplHits,
      simulationConsumers,
      nativeBinaryBackends,
      browserZkpPythonHits,
      runtimePythonHits,
    },
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'zkp-real-backend-gate.json'), `${JSON.stringify(gate, null, 2)}\n`, 'utf8');
  writeFileSync(resolve(outDir, 'zkp-real-backend-gate.md'), renderMarkdown(gate), 'utf8');
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
    throw new Error(`Real browser ZKP gate failed: ${failing}`);
  }
}

function readPackageDeps(path) {
  if (!existsSync(path)) return new Map();
  const pkg = JSON.parse(readFileSync(path, 'utf8'));
  return new Map(Object.entries({
    ...(pkg.dependencies ?? {}),
    ...(pkg.devDependencies ?? {}),
    ...(pkg.optionalDependencies ?? {}),
  }));
}

function listFiles(root, ignored = []) {
  if (!existsSync(root)) return [];
  const ignoreSet = new Set(ignored);
  const out = [];
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    let stat;
    try {
      stat = statSync(current);
    } catch {
      continue;
    }
    if (stat.isDirectory()) {
      const name = current.split(/[\\/]/).pop();
      if (name && ignoreSet.has(name)) continue;
      for (const entry of readdirSync(current)) stack.push(resolve(current, entry));
    } else if (stat.isFile()) {
      out.push(current);
    }
  }
  return out.sort();
}

function stripComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1');
}

function check(name, pass, details) {
  return { name, pass: Boolean(pass), details: String(details ?? '') };
}

function summarizeRows(rows, field) {
  if (!rows.length) return 'none';
  const sample = rows.slice(0, 8).map(row => row[field]).join(', ');
  return `${rows.length}; sample=${sample}${rows.length > 8 ? ', ...' : ''}`;
}

function renderMarkdown(gate) {
  const lines = [
    '# Real Browser ZKP Backend Gate',
    '',
    `Generated: ${gate.generatedAt}`,
    `Result: ${gate.passed ? 'PASS' : 'FAIL'}`,
    '',
    'This gate is intentionally stricter than browser import purity. It requires an actual browser-compatible ZKP proving backend and rejects production paths that rely on deterministic simulation.',
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
      console.log('Usage: node implementation_plan/conformance/zkp_real_backend_gate.mjs [--root .] [--out-dir conformance] [--fail-on-gap]');
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
