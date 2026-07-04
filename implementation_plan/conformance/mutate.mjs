#!/usr/bin/env node
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

export function loadVectors(vectorsDir) {
  const vectors = [];
  for (const file of readdirSync(vectorsDir).filter(name => name.endsWith('.json')).sort()) {
    const payload = JSON.parse(readFileSync(resolve(vectorsDir, file), 'utf8'));
    vectors.push(...(payload.vectors ?? []));
  }
  return vectors;
}

export function mutateVectors(vectors) {
  const mutated = [];
  for (const vector of vectors) {
    if (vector.inputType !== 'policy' || !vector.input?.policy) continue;
    mutated.push(makePermutationVariant(vector));
    mutated.push(makeIrrelevantAxiomVariant(vector));
    mutated.push(makeAlphaRenameVariant(vector));
  }
  return mutated;
}

function makePermutationVariant(vector) {
  const clone = deepClone(vector);
  clone.id = `${vector.id}:permute`;
  clone.description = `Permutation invariant variant of ${vector.id}`;
  clone.input.policy.permissions = [...(clone.input.policy.permissions ?? [])].reverse();
  clone.input.policy.prohibitions = [...(clone.input.policy.prohibitions ?? [])].reverse();
  clone.input.policy.obligations = [...(clone.input.policy.obligations ?? [])].reverse();
  clone.metamorphic = { sourceVectorId: vector.id, oracle: 'reorder axioms preserves status' };
  clone.tags = unique([...(clone.tags ?? []), 'metamorphic', 'order-invariant']);
  return clone;
}

function makeIrrelevantAxiomVariant(vector) {
  const clone = deepClone(vector);
  clone.id = `${vector.id}:irrelevant`;
  clone.description = `Irrelevant consistent permission variant of ${vector.id}`;
  clone.input.policy.permissions = [
    ...(clone.input.policy.permissions ?? []),
    { cap: `irrelevant_${safeId(vector.id)}`, rsc: `irrelevant_${safeId(vector.subsystem)}` },
  ];
  clone.metamorphic = { sourceVectorId: vector.id, oracle: 'adding an irrelevant consistent axiom preserves status' };
  clone.tags = unique([...(clone.tags ?? []), 'metamorphic', 'monotonicity']);
  return clone;
}

function makeAlphaRenameVariant(vector) {
  const clone = deepClone(vector);
  clone.id = `${vector.id}:alpha`;
  clone.description = `Alpha-renamed identifier variant of ${vector.id}`;
  clone.input.policy.id = `${clone.input.policy.id ?? vector.id}_alpha`;
  clone.metamorphic = { sourceVectorId: vector.id, oracle: 'renaming non-logical policy id preserves status' };
  clone.tags = unique([...(clone.tags ?? []), 'metamorphic', 'alpha-rename']);
  return clone;
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function safeId(value) {
  return String(value).replace(/[^A-Za-z0-9_]+/g, '_');
}

function unique(values) {
  return [...new Set(values)];
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--vectors') args.vectors = argv[++i];
    else if (arg === '--out') args.out = argv[++i];
    else if (arg === '--help') printHelpAndExit(0);
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!args.vectors || !args.out) throw new Error('Both --vectors and --out are required');
  return args;
}

function printHelpAndExit(code) {
  console.log(`Usage: node implementation_plan/conformance/mutate.mjs --vectors implementation_plan/conformance/vectors --out conformance/mutated-vectors.json`);
  process.exit(code);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  try {
    const args = parseArgs(process.argv.slice(2));
    const payload = {
      schemaVersion: '2026-07-03',
      generatedAt: new Date().toISOString(),
      vectors: mutateVectors(loadVectors(resolve(args.vectors))),
    };
    const out = resolve(args.out);
    mkdirSync(dirname(out), { recursive: true });
    writeFileSync(out, JSON.stringify(payload, null, 2) + '\n', 'utf8');
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}
