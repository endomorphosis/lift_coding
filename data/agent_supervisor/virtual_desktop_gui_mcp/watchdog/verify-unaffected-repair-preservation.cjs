'use strict';
// Read-only verification; the receipt records preservation, never completion.
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../../../..');
const sourceRoot = path.join(root, 'swissknife');
const evidenceRoot = path.join(sourceRoot, 'test-results/virtual-desktop-ipfs-mcp-orb');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = filename => JSON.parse(fs.readFileSync(filename, 'utf8'));
for (const line of fs.readFileSync(path.join(__dirname, 'backends/client.env'), 'utf8').split('\n')) {
  if (!line || line.startsWith('#')) continue;
  const at = line.indexOf('=');
  assert.ok(at > 0);
  process.env[line.slice(0, at)] = line.slice(at + 1);
}
const { FAMILIES, loadFamilyEvidence } = require(path.join(sourceRoot, 'scripts/vdg-evidence.cjs'));
const { captureInputFingerprint } = require(path.join(sourceRoot, 'scripts/vdg-capture-fingerprint.cjs'));
const { inspectInventory } = require(path.join(sourceRoot, 'scripts/vdg-inventory-contract.cjs'));
const { checkCapture } = require(path.join(sourceRoot, 'scripts/check-vdg-capture.cjs'));
const baselinePath = path.join(__dirname, 'smoke-receipts/preservation-before-strudel-repair-20261021T085215Z.json');
const baselineBytes = fs.readFileSync(baselinePath);
assert.equal(hash(baselineBytes), '1cfb8f265e0fd1b1cfa2f158eb127e329a85b8352eb37d5cea53fc6f538b3a05');
const baseline = JSON.parse(baselineBytes);
const inventory = inspectInventory({ sourceRoot, evidenceRoot });
assert.equal(inventory.current, true, JSON.stringify(inventory));
const families = {};
let imageCount = 0;
for (const family of ['vdg-storage', 'vdg-datasets', 'vdg-network']) {
  const definition = FAMILIES[family];
  const cells = {};
  for (const transport of ['http', 'libp2p']) {
    const previous = baseline.families[family].transports[transport];
    const fingerprint = captureInputFingerprint(family, transport, { sourceRoot, evidenceRoot, definition });
    assert.equal(fingerprint, previous.input_fingerprint, `${family}:${transport} source changed`);
    const checkpointPath = path.join(sourceRoot, previous.checkpoint_path);
    const checkpointBytes = fs.readFileSync(checkpointPath);
    assert.equal(hash(checkpointBytes), previous.checkpoint_file_sha256);
    const checkpoint = JSON.parse(checkpointBytes);
    assert.equal(hash(JSON.stringify(checkpoint.payload)), previous.payload_sha256);
    assert.equal(checkpoint.payload_sha256, previous.payload_sha256);
    // Incremental checkpoints deliberately grant no acquisition authority.
    assert.equal(checkpoint.capture_complete, false);
    assert.equal(checkpoint.work_complete, false);
    assert.equal(checkpoint.completion_authority, false);
    const acquisition = checkCapture(family, transport, { sourceRoot, evidenceRoot });
    assert.equal(acquisition.capture_complete, true);
    assert.equal(acquisition.report_sha256, previous.acquisition.report_sha256);
    assert.equal(acquisition.run_id, previous.acquisition.run_id);
    let verifiedImages = 0;
    for (const [relative, digest] of Object.entries(checkpoint.payload.image_hashes)) {
      const filename = path.resolve(root, relative);
      assert.ok(filename.startsWith(`${evidenceRoot}${path.sep}`));
      const bytes = fs.readFileSync(filename);
      assert.equal(hash(bytes), digest, relative);
      assert.equal(bytes.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
      verifiedImages++;
    }
    assert.equal(verifiedImages, previous.images.count);
    imageCount += verifiedImages;
    cells[transport] = { input_fingerprint: fingerprint, checkpoint_sha256: hash(checkpointBytes),
      payload_sha256: checkpoint.payload_sha256, report_sha256: acquisition.report_sha256,
      run_id: acquisition.run_id, row_count: acquisition.row_count, actual_png_hashes_verified: verifiedImages };
  }
  const strict = loadFamilyEvidence(family, { sourceRoot, evidenceRoot });
  assert.equal(strict.decision, 'GO', JSON.stringify(strict.gap_counts));
  assert.equal(strict.passed, true);
  assert.equal(strict.gap_count, 0);
  families[family] = { transports: cells, strict: { decision: strict.decision, passed: strict.passed, gap_count: strict.gap_count } };
}
const affected = {};
for (const family of ['vdg-control', 'vdg-local', 'vdg-accelerate']) {
  affected[family] = {};
  for (const transport of ['http', 'libp2p']) {
    const previous = family === 'vdg-local' ? baseline.local[transport].old_input_fingerprint
      : baseline.families[family].transports[transport].input_fingerprint;
    const current = captureInputFingerprint(family, transport, { sourceRoot, evidenceRoot, definition: FAMILIES[family] });
    assert.notEqual(current, previous, `${family}:${transport} repair was not bound`);
    affected[family][transport] = { previous_input_fingerprint: previous, current_input_fingerprint: current,
      previous_source_binding_obsolete: true,
      previous_checkpoint_existed: family === 'vdg-local' ? baseline.local[transport].checkpoint_exists : true,
      new_canonical_capture_required: true,
      reason: family === 'vdg-accelerate' ? 'Fresh real census changed the Neural Photoshop history selector from Expand history panel to Collapse history panel; both profiles require current inventory proof.'
        : 'Actual app repair changed the declared family source binding.' };
  }
}
const receipt = { schema: 'swissknife.vdg-completion-repair-preservation.v1', observed_at: new Date().toISOString(),
  baseline_path: path.relative(root, baselinePath), baseline_sha256: hash(baselineBytes), inventory,
  families, affected, unaffected_family_count: 3, unaffected_transport_cells: 6, actual_png_hashes_verified: imageCount,
  work_complete: false, completion_authority: false };
const output = path.join(__dirname, 'smoke-receipts/preservation-after-strudel-control-repairs-20261022.json');
fs.writeFileSync(output, `${JSON.stringify(receipt, null, 2)}\n`, { flag: 'wx' });
console.log(JSON.stringify({ receipt: output, sha256: hash(fs.readFileSync(output)),
  unaffected_family_count: 3, unaffected_transport_cells: 6, actual_png_hashes_verified: imageCount,
  affected_captures_require_fresh_evidence: true, work_complete: false, completion_authority: false }));
