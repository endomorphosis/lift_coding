#!/usr/bin/env node
import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

function main() {
  const args = parseArgs(process.argv.slice(2));
  const outDir = resolve(args.outDir);
  const vectorsDir = resolve(args.vectorsDir);

  const report = loadJson(resolve(outDir, 'report.json'));
  const mutationGate = loadJson(resolve(outDir, 'mutation-gate.json'));
  const differentialFuzz = loadJson(resolve(outDir, 'differential-fuzz.json'));
  const tsCoverageReconciliation = loadJson(resolve(outDir, 'ts-coverage-reconciliation.json'));
  const selfContainmentGate = loadJson(resolve(outDir, 'self-containment-gate.json'));
  const port239HostNativeGate = loadJson(resolve(outDir, 'port239-host-native-gate.json'));
  const portSubstanceGate = loadJson(resolve(outDir, 'port-substance-gate.json'));
  const vectorStats = summarizeVectors(vectorsDir);
  const vectorsIndex = loadVectorsIndex(vectorsDir);
  const vectorsById = vectorsIndex.byId;
  const vectorFilesById = vectorsIndex.filesById;
  const zkpRows = Array.isArray(report?.rows)
    ? report.rows.filter(row => {
      const inputType = String(row?.inputType ?? '');
      return inputType === 'zkpStatement' || inputType === 'zkpWitness';
    })
    : [];
  const port239RuntimeRows = Array.isArray(report?.rows)
    ? report.rows.filter(row => {
      const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
      return tags.includes('flogic') || tags.includes('ergo') || tags.includes('host-native');
    })
    : [];
  const port239RowsById = new Map(port239RuntimeRows.map(row => [String(row?.vectorId ?? ''), row]));
  const requiredPort239VectorIds = args.port239RequiredVectorIds;
  const requiredPort239VectorExpectations = {
    'zkp-sim-005': { tags: ['flogic', 'host-native'], inputType: 'policy', subsystem: 'zkp-statement', backendMode: 'host-dependent', excludeFromParityWhenSimulated: true, status: 'sat', decided: true, acceptableReasons: ['sat', 'proved'], expectedHash: 'e05f426ec6c10a66ec3b0ef1667c8ef07291b44a977ae35f9e08d7cab1316e53' },
    'zkp-sim-011': { tags: ['ergo', 'host-native'], inputType: 'policy', subsystem: 'zkp-statement', backendMode: 'host-dependent', excludeFromParityWhenSimulated: true, status: 'sat', decided: true, acceptableReasons: ['sat', 'proved'], expectedHash: '6cf9842358a80aef35bcc9708d2c5ea2570e8506223ddf9a6a7614eb068f93e2' },
    'zkp-sim-012': { tags: ['flogic', 'host-native'], inputType: 'policy', subsystem: 'zkp-statement', backendMode: 'host-dependent', excludeFromParityWhenSimulated: true, status: 'sat', decided: true, acceptableReasons: ['sat', 'proved'], expectedHash: '3c2eb813633f9fe0692ff6ad83609a7af4390cef44d1a1145ef264888f7e83f9' },
  };
  const expectedPort239VectorsFile = args.port239RequiredVectorsFile;
  const missingPort239RequiredVectorDefinitions = requiredPort239VectorIds.filter(vectorId => !vectorsById.has(vectorId));
  const port239RequiredVectorSourceViolations = requiredPort239VectorIds.filter(vectorId => {
    const files = vectorFilesById.get(vectorId) ?? [];
    return files.length !== 1 || files[0] !== expectedPort239VectorsFile;
  });
  const missingPort239RequiredVectorIds = requiredPort239VectorIds.filter(vectorId => !port239RowsById.has(vectorId));
  const port239RequiredVectorOutcomeViolations = requiredPort239VectorIds.filter(vectorId => {
    const row = port239RowsById.get(vectorId);
    return !row || String(row?.outcome ?? '') !== 'HOST_NATIVE_EXCLUDED';
  });
  const port239RequiredVectorTagViolations = requiredPort239VectorIds.filter(vectorId => {
    const row = port239RowsById.get(vectorId);
    const expected = requiredPort239VectorExpectations[vectorId];
    if (!row || !expected) return false;
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return expected.tags.some(tag => !tags.includes(tag));
  });
  const port239RequiredVectorShapeViolations = requiredPort239VectorIds.filter(vectorId => {
    const row = port239RowsById.get(vectorId);
    const expected = requiredPort239VectorExpectations[vectorId];
    if (!row || !expected) return false;
    return String(row?.inputType ?? '') !== expected.inputType
      || String(row?.subsystem ?? '') !== expected.subsystem;
  });
  const port239RequiredVectorDefinitionViolations = requiredPort239VectorIds.filter(vectorId => {
    const vector = vectorsById.get(vectorId);
    const expected = requiredPort239VectorExpectations[vectorId];
    if (!vector || !expected) return false;
    const tags = Array.isArray(vector?.tags) ? vector.tags.map(tag => String(tag).toLowerCase()) : [];
    const backendMode = String(vector?.expected?.backendMode ?? '');
    const excludeFromParityWhenSimulated = vector?.expected?.excludeFromParityWhenSimulated === true;
    const status = String(vector?.expected?.status ?? '');
    const decided = vector?.expected?.decided === true;
    const acceptableReasons = Array.isArray(vector?.expected?.acceptableReasons)
      ? vector.expected.acceptableReasons.map(reason => String(reason).toLowerCase()).sort()
      : [];
    const expectedReasons = expected.acceptableReasons.map(reason => String(reason).toLowerCase()).sort();
    return String(vector?.inputType ?? '') !== expected.inputType
      || String(vector?.subsystem ?? '') !== expected.subsystem
      || expected.tags.some(tag => !tags.includes(tag))
      || backendMode !== expected.backendMode
      || excludeFromParityWhenSimulated !== expected.excludeFromParityWhenSimulated
      || status !== expected.status
      || decided !== expected.decided
      || JSON.stringify(acceptableReasons) !== JSON.stringify(expectedReasons);
  });
  const port239RequiredVectorHashViolations = requiredPort239VectorIds.filter(vectorId => {
    const vector = vectorsById.get(vectorId);
    const expected = requiredPort239VectorExpectations[vectorId];
    if (!vector || !expected?.expectedHash) return false;
    const actualHash = digestSha256(stableStringify(vector));
    return actualHash !== expected.expectedHash;
  });
  const strictStructuredRows = Array.isArray(report?.rows)
    ? report.rows.filter(row => row?.strictStructuredParity === true && !['HOST_NATIVE_EXCLUDED', 'SIMULATED_DEPENDENCY'].includes(String(row?.outcome ?? '')))
    : [];
  const strictStructuredArtifactProblemRows = strictStructuredRows.filter(row => row?.structuredArtifactMatch !== true);
  const port239RuntimeFlogicCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('flogic');
  }).length;
  const port239RuntimeErgoCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('ergo');
  }).length;
  const port239RuntimeHostNativeTagCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('host-native');
  }).length;
  const port239RuntimeFlogicExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('flogic') && row?.outcome === 'HOST_NATIVE_EXCLUDED';
  }).length;
  const port239RuntimeErgoExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('ergo') && row?.outcome === 'HOST_NATIVE_EXCLUDED';
  }).length;
  const port239RuntimeHostNativeTagExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('host-native') && row?.outcome === 'HOST_NATIVE_EXCLUDED';
  }).length;
  const port239RuntimeFlogicNonExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('flogic') && row?.outcome !== 'HOST_NATIVE_EXCLUDED';
  }).length;
  const port239RuntimeErgoNonExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('ergo') && row?.outcome !== 'HOST_NATIVE_EXCLUDED';
  }).length;
  const port239RuntimeHostNativeTagNonExcludedCount = port239RuntimeRows.filter(row => {
    const tags = Array.isArray(row?.tags) ? row.tags.map(tag => String(tag).toLowerCase()) : [];
    return tags.includes('host-native') && row?.outcome !== 'HOST_NATIVE_EXCLUDED';
  }).length;
  const zkpSimulatedMatchCount = zkpRows.filter(row => {
    const pyMode = String(row?.pythonBackendMode ?? '');
    const tsMode = String(row?.tsBackendMode ?? '');
    return row?.outcome === 'MATCH' && (pyMode === 'simulated' || tsMode === 'simulated');
  }).length;
  const zkpHostNativeExcludedCount = zkpRows.filter(row => row?.outcome === 'HOST_NATIVE_EXCLUDED').length;
  const port239RuntimeSimulatedMatchCount = port239RuntimeRows.filter(row => {
    const pyMode = String(row?.pythonBackendMode ?? '');
    const tsMode = String(row?.tsBackendMode ?? '');
    return row?.outcome === 'MATCH' && (pyMode === 'simulated' || tsMode === 'simulated');
  }).length;
  const port239RuntimeHostNativeExcludedCount = port239RuntimeRows.filter(row => row?.outcome === 'HOST_NATIVE_EXCLUDED').length;

  const checks = [
    check('parity threshold', Number(report?.summary?.parityPercent ?? 0) >= args.parityThreshold, `parity=${Number(report?.summary?.parityPercent ?? 0).toFixed(2)} threshold=${args.parityThreshold}`),
    check('zero mismatches', Number(report?.summary?.MISMATCH ?? 0) === 0, `mismatch=${Number(report?.summary?.MISMATCH ?? 0)}`),
    check('mutation gate passed', mutationGate?.passed === true, `passed=${String(mutationGate?.passed)} mutationDrop=${Number(mutationGate?.mutationDrop ?? 0)}`),
    check('mutation reduced parity', Number(mutationGate?.mutationDrop ?? 0) > 0, `mutationDrop=${Number(mutationGate?.mutationDrop ?? 0)}`),
    check('differential fuzz mismatch-free', Number(differentialFuzz?.mismatch ?? 1) === 0, `mismatch=${Number(differentialFuzz?.mismatch ?? 1)} total=${Number(differentialFuzz?.total ?? 0)}`),
    check('differential fuzz non-empty', Number(differentialFuzz?.total ?? 0) > 0, `total=${Number(differentialFuzz?.total ?? 0)}`),
    check('PORT-236 strict structured artifacts present', strictStructuredRows.length > 0 && strictStructuredArtifactProblemRows.length === 0, `strictRows=${strictStructuredRows.length} artifactProblems=${strictStructuredArtifactProblemRows.length}`),
    check('ts coverage reconciliation passed', tsCoverageReconciliation?.passed === true, `passed=${String(tsCoverageReconciliation?.passed)} failures=${Number(tsCoverageReconciliation?.summary?.failureCount ?? 0)}`),
    check('self-containment gate executed', Number((selfContainmentGate?.checks ?? []).length) > 0, `passed=${String(selfContainmentGate?.passed)} violations=${Number(selfContainmentGate?.summary?.backendViolations ?? 0) + Number(selfContainmentGate?.summary?.statusViolations ?? 0) + Number(selfContainmentGate?.summary?.reasonViolations ?? 0) + Number(selfContainmentGate?.summary?.markerViolations ?? 0)}`),
    check('PORT-239 host-native classification gate passed', port239HostNativeGate?.passed === true, `passed=${String(port239HostNativeGate?.passed)} violations=${Number(port239HostNativeGate?.summary?.violations ?? 0)}`),
    check('PORT-252 substance gate passed', portSubstanceGate?.passed === true, `passed=${String(portSubstanceGate?.passed)} flagged=${Number(portSubstanceGate?.summary?.flaggedModules ?? 0)} violations=${Number(portSubstanceGate?.summary?.violations ?? 0)}`),
    check('PORT-239 runtime vectors minimum row count', port239RuntimeRows.length >= args.port239RuntimeMinRows, `rows=${port239RuntimeRows.length} min=${args.port239RuntimeMinRows}`),
    check('PORT-239 required vector ids exist in corpus', missingPort239RequiredVectorDefinitions.length === 0, `missing=${missingPort239RequiredVectorDefinitions.join(',') || 'none'}`),
    check('PORT-239 required vector ids originate from expected vectors file', port239RequiredVectorSourceViolations.length === 0, `violations=${port239RequiredVectorSourceViolations.join(',') || 'none'} expectedFile=${expectedPort239VectorsFile}`),
    check('PORT-239 runtime required vector ids present', missingPort239RequiredVectorIds.length === 0, `missing=${missingPort239RequiredVectorIds.join(',') || 'none'}`),
    check('PORT-239 required vector ids retain expected corpus fields', port239RequiredVectorDefinitionViolations.length === 0, `violations=${port239RequiredVectorDefinitionViolations.join(',') || 'none'}`),
    check('PORT-239 required vector ids retain expected canonical hashes', port239RequiredVectorHashViolations.length === 0, `violations=${port239RequiredVectorHashViolations.join(',') || 'none'}`),
    check('PORT-239 runtime required vector ids are host-native-excluded', port239RequiredVectorOutcomeViolations.length === 0, `violations=${port239RequiredVectorOutcomeViolations.join(',') || 'none'}`),
    check('PORT-239 runtime required vector ids retain expected tags', port239RequiredVectorTagViolations.length === 0, `violations=${port239RequiredVectorTagViolations.join(',') || 'none'}`),
    check('PORT-239 runtime required vector ids retain expected shape', port239RequiredVectorShapeViolations.length === 0, `violations=${port239RequiredVectorShapeViolations.join(',') || 'none'}`),
    check('PORT-239 runtime flogic-tag minimum row count', port239RuntimeFlogicCount >= args.port239RuntimeFlogicMinRows, `rows=${port239RuntimeFlogicCount} min=${args.port239RuntimeFlogicMinRows}`),
    check('PORT-239 runtime ergo-tag minimum row count', port239RuntimeErgoCount >= args.port239RuntimeErgoMinRows, `rows=${port239RuntimeErgoCount} min=${args.port239RuntimeErgoMinRows}`),
    check('PORT-239 runtime host-native-tag minimum row count', port239RuntimeHostNativeTagCount >= args.port239RuntimeHostNativeTagMinRows, `rows=${port239RuntimeHostNativeTagCount} min=${args.port239RuntimeHostNativeTagMinRows}`),
    check('PORT-239 runtime flogic-tag host-native exclusions minimum', port239RuntimeFlogicExcludedCount >= args.port239RuntimeFlogicExcludedMinRows, `rows=${port239RuntimeFlogicExcludedCount} min=${args.port239RuntimeFlogicExcludedMinRows}`),
    check('PORT-239 runtime ergo-tag host-native exclusions minimum', port239RuntimeErgoExcludedCount >= args.port239RuntimeErgoExcludedMinRows, `rows=${port239RuntimeErgoExcludedCount} min=${args.port239RuntimeErgoExcludedMinRows}`),
    check('PORT-239 runtime host-native-tag exclusions minimum', port239RuntimeHostNativeTagExcludedCount >= args.port239RuntimeHostNativeTagExcludedMinRows, `rows=${port239RuntimeHostNativeTagExcludedCount} min=${args.port239RuntimeHostNativeTagExcludedMinRows}`),
    check('PORT-239 runtime flogic-tag non-excluded count is zero', port239RuntimeFlogicNonExcludedCount === 0, `rows=${port239RuntimeFlogicNonExcludedCount}`),
    check('PORT-239 runtime ergo-tag non-excluded count is zero', port239RuntimeErgoNonExcludedCount === 0, `rows=${port239RuntimeErgoNonExcludedCount}`),
    check('PORT-239 runtime host-native-tag non-excluded count is zero', port239RuntimeHostNativeTagNonExcludedCount === 0, `rows=${port239RuntimeHostNativeTagNonExcludedCount}`),
    check('PORT-239 runtime simulated vectors not counted as match', port239RuntimeSimulatedMatchCount === 0, `simulatedRuntimeMatch=${port239RuntimeSimulatedMatchCount}`),
    check('PORT-239 runtime host-native exclusion active', port239RuntimeHostNativeExcludedCount > 0, `runtimeHostNativeExcluded=${port239RuntimeHostNativeExcludedCount}`),
    check('PORT-238 simulated zkp not counted as parity match', zkpSimulatedMatchCount === 0, `simulatedZkpMatch=${zkpSimulatedMatchCount}`),
    check('PORT-238 host-native zkp exclusion active', zkpHostNativeExcludedCount > 0, `hostNativeExcludedZkp=${zkpHostNativeExcludedCount}`),
    ...port235Checks(vectorStats),
  ];

  const passed = checks.every(item => item.pass);
  const certificate = {
    schemaVersion: '2026-07-05',
    generatedAt: new Date().toISOString(),
    certificateType: 'behavioral-completeness',
    outDir,
    vectorsDir,
    parityThreshold: args.parityThreshold,
    port239RuntimeMinRows: args.port239RuntimeMinRows,
    port239RuntimeFlogicMinRows: args.port239RuntimeFlogicMinRows,
    port239RuntimeErgoMinRows: args.port239RuntimeErgoMinRows,
    port239RuntimeHostNativeTagMinRows: args.port239RuntimeHostNativeTagMinRows,
    port239RuntimeFlogicExcludedMinRows: args.port239RuntimeFlogicExcludedMinRows,
    port239RuntimeErgoExcludedMinRows: args.port239RuntimeErgoExcludedMinRows,
    port239RuntimeHostNativeTagExcludedMinRows: args.port239RuntimeHostNativeTagExcludedMinRows,
    port239RequiredVectorIds: args.port239RequiredVectorIds,
    port239RequiredVectorsFile: args.port239RequiredVectorsFile,
    checks,
    passed,
    metrics: {
      conformanceSummary: report?.summary ?? {},
      mutationGate,
      differentialFuzz,
      tsCoverageReconciliation,
      selfContainmentGate,
      port239HostNativeGate,
      portSubstanceGate,
      strictStructuredRows: strictStructuredRows.length,
      strictStructuredArtifactProblemRows: strictStructuredArtifactProblemRows.length,
      port239RuntimeRows: port239RuntimeRows.length,
      requiredPort239VectorCount: requiredPort239VectorIds.length,
      expectedPort239VectorsFile,
      missingPort239RequiredVectorDefinitions,
      port239RequiredVectorSourceViolations,
      port239RequiredVectorDefinitionViolations,
      port239RequiredVectorHashViolations,
      missingPort239RequiredVectorIds,
      port239RequiredVectorOutcomeViolations,
      port239RequiredVectorTagViolations,
      port239RequiredVectorShapeViolations,
      port239RuntimeFlogicCount,
      port239RuntimeErgoCount,
      port239RuntimeHostNativeTagCount,
      port239RuntimeFlogicExcludedCount,
      port239RuntimeErgoExcludedCount,
      port239RuntimeHostNativeTagExcludedCount,
      port239RuntimeFlogicNonExcludedCount,
      port239RuntimeErgoNonExcludedCount,
      port239RuntimeHostNativeTagNonExcludedCount,
      port239RuntimeSimulatedMatchCount,
      port239RuntimeHostNativeExcludedCount,
      zkpSimulatedMatchCount,
      zkpHostNativeExcludedCount,
      vectorInputCounts: vectorStats.byInputType,
      totalVectors: vectorStats.total,
    },
  };

  mkdirSync(outDir, { recursive: true });
  writeFileSync(resolve(outDir, 'behavioral-certificate.json'), JSON.stringify(certificate, null, 2) + '\n', 'utf8');
  writeFileSync(resolve(outDir, 'behavioral-certificate.md'), renderMarkdown(certificate), 'utf8');

  console.log(JSON.stringify({ passed: certificate.passed, checks: checks.length }, null, 2));

  if (!passed) {
    const failures = checks.filter(item => !item.pass).map(item => `${item.name} (${item.details})`).join('; ');
    throw new Error(`Behavioral certificate failed: ${failures}`);
  }
}

function port235Checks(vectorStats) {
  const required = ['folFormula', 'modalKripke', 'temporalTrace', 'dcec', 'deonticConflict', 'legalNorm', 'zkpWitness'];
  const checks = [];
  for (const inputType of required) {
    const count = Number(vectorStats.byInputType[inputType] ?? 0);
    checks.push(check(`PORT-235 vectors ${inputType}`, count >= 25, `count=${count}`));
  }
  return checks;
}

function summarizeVectors(vectorsDir) {
  const byInputType = {};
  let total = 0;
  const files = readdirSync(vectorsDir).filter(name => name.endsWith('.json')).sort();
  for (const file of files) {
    const payload = loadJson(resolve(vectorsDir, file));
    for (const vector of payload?.vectors ?? []) {
      const inputType = String(vector?.inputType ?? 'unknown');
      byInputType[inputType] = Number(byInputType[inputType] ?? 0) + 1;
      total += 1;
    }
  }
  return { total, byInputType };
}

function loadVectorsIndex(vectorsDir) {
  const byId = new Map();
  const filesById = new Map();
  const files = readdirSync(vectorsDir).filter(name => name.endsWith('.json')).sort();
  for (const file of files) {
    const payload = loadJson(resolve(vectorsDir, file));
    for (const vector of payload?.vectors ?? []) {
      const id = String(vector?.id ?? '');
      if (!id) continue;
      byId.set(id, vector);
      const bucket = filesById.get(id) ?? [];
      bucket.push(file);
      filesById.set(id, bucket);
    }
  }
  return { byId, filesById };
}

function renderMarkdown(certificate) {
  const lines = [
    '# Behavioral Completeness Certificate',
    '',
    `Generated: ${certificate.generatedAt}`,
    `Result: ${certificate.passed ? 'PASS' : 'FAIL'}`,
    '',
    '## Checks',
    '',
    '| Check | Result | Details |',
    '|---|---|---|',
  ];

  for (const item of certificate.checks) {
    lines.push(`| ${escapeCell(item.name)} | ${item.pass ? 'PASS' : 'FAIL'} | ${escapeCell(item.details)} |`);
  }

  lines.push('', '## Metrics', '', '```json', JSON.stringify(certificate.metrics, null, 2), '```', '');
  return lines.join('\n');
}

function check(name, pass, details) {
  return { name, pass: Boolean(pass), details: String(details ?? '') };
}

function escapeCell(value) {
  return String(value ?? '').replace(/\|/g, '\\|');
}

function parseArgs(argv) {
  const args = {
    outDir: 'conformance',
    vectorsDir: 'implementation_plan/conformance/vectors',
    parityThreshold: 100,
    port239RuntimeMinRows: 3,
    port239RuntimeFlogicMinRows: 2,
    port239RuntimeErgoMinRows: 1,
    port239RuntimeHostNativeTagMinRows: 3,
    port239RuntimeFlogicExcludedMinRows: 2,
    port239RuntimeErgoExcludedMinRows: 1,
    port239RuntimeHostNativeTagExcludedMinRows: 3,
    port239RequiredVectorIds: ['zkp-sim-005', 'zkp-sim-011', 'zkp-sim-012'],
    port239RequiredVectorsFile: 'core-policy-vectors.json',
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--out-dir') args.outDir = argv[++i];
    else if (arg === '--vectors') args.vectorsDir = argv[++i];
    else if (arg === '--parity-threshold') args.parityThreshold = Number(argv[++i]);
    else if (arg === '--port239-runtime-min-rows') args.port239RuntimeMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-flogic-min-rows') args.port239RuntimeFlogicMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-ergo-min-rows') args.port239RuntimeErgoMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-host-native-tag-min-rows') args.port239RuntimeHostNativeTagMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-flogic-excluded-min-rows') args.port239RuntimeFlogicExcludedMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-ergo-excluded-min-rows') args.port239RuntimeErgoExcludedMinRows = Number(argv[++i]);
    else if (arg === '--port239-runtime-host-native-tag-excluded-min-rows') args.port239RuntimeHostNativeTagExcludedMinRows = Number(argv[++i]);
    else if (arg === '--port239-required-vector-ids') args.port239RequiredVectorIds = parseCsvList(argv[++i]);
    else if (arg === '--port239-required-vectors-file') args.port239RequiredVectorsFile = String(argv[++i]);
    else if (arg === '--help') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!Number.isFinite(args.parityThreshold) || args.parityThreshold < 0 || args.parityThreshold > 100) {
    throw new Error(`Invalid --parity-threshold: ${args.parityThreshold}`);
  }
  if (!Number.isInteger(args.port239RuntimeMinRows) || args.port239RuntimeMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-min-rows: ${args.port239RuntimeMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeFlogicMinRows) || args.port239RuntimeFlogicMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-flogic-min-rows: ${args.port239RuntimeFlogicMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeErgoMinRows) || args.port239RuntimeErgoMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-ergo-min-rows: ${args.port239RuntimeErgoMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeHostNativeTagMinRows) || args.port239RuntimeHostNativeTagMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-host-native-tag-min-rows: ${args.port239RuntimeHostNativeTagMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeFlogicExcludedMinRows) || args.port239RuntimeFlogicExcludedMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-flogic-excluded-min-rows: ${args.port239RuntimeFlogicExcludedMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeErgoExcludedMinRows) || args.port239RuntimeErgoExcludedMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-ergo-excluded-min-rows: ${args.port239RuntimeErgoExcludedMinRows}`);
  }
  if (!Number.isInteger(args.port239RuntimeHostNativeTagExcludedMinRows) || args.port239RuntimeHostNativeTagExcludedMinRows < 1) {
    throw new Error(`Invalid --port239-runtime-host-native-tag-excluded-min-rows: ${args.port239RuntimeHostNativeTagExcludedMinRows}`);
  }
  if (!Array.isArray(args.port239RequiredVectorIds) || args.port239RequiredVectorIds.length === 0) {
    throw new Error('Invalid --port239-required-vector-ids: must provide at least one vector id');
  }
  if (!args.port239RequiredVectorsFile || !String(args.port239RequiredVectorsFile).trim()) {
    throw new Error('Invalid --port239-required-vectors-file: must provide a non-empty file name');
  }
  return args;
}

function printHelp() {
  console.log('Usage: node implementation_plan/conformance/behavioral_certificate.mjs [--out-dir conformance] [--vectors implementation_plan/conformance/vectors] [--parity-threshold 100] [--port239-runtime-min-rows 3] [--port239-runtime-flogic-min-rows 2] [--port239-runtime-ergo-min-rows 1] [--port239-runtime-host-native-tag-min-rows 3] [--port239-runtime-flogic-excluded-min-rows 2] [--port239-runtime-ergo-excluded-min-rows 1] [--port239-runtime-host-native-tag-excluded-min-rows 3] [--port239-required-vector-ids zkp-sim-005,zkp-sim-011,zkp-sim-012] [--port239-required-vectors-file core-policy-vectors.json]');
}

function parseCsvList(value) {
  return String(value ?? '')
    .split(',')
    .map(item => item.trim())
    .filter(Boolean);
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map(item => stableStringify(item)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    const keys = Object.keys(value).sort();
    const body = keys
      .map(key => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(',');
    return `{${body}}`;
  }
  return JSON.stringify(value);
}

function digestSha256(text) {
  return createHash('sha256').update(String(text ?? '')).digest('hex');
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
