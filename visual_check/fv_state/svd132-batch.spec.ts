/**
 * GAP-PASS SCRATCH HARNESS (not part of the repo): runs the repo's own
 * SVD-132 audit runner (PlaywrightVirtualDesktopAppAuditDriver +
 * runVirtualDesktopAppAudit) over a BATCH of the manifest, using the
 * runner's supported `manifest` option, because the canonical single-run
 * spec exceeds its own 900 s budget on this 2-core VM under co-tenant
 * load (see BROKEN_CONTRACT_MAP B1). Batch size via SVD_BATCH_SIZE
 * (manifest entries per batch), batch index via SVD_BATCH. Evidence is
 * written to fv_state/svd132-batch-<n>.json; screenshots go to the
 * canonical screenshot root so the retained sets are the real ones.
 * The raised per-batch timeout is a local run parameter of this scratch
 * harness only; the committed spec's budget is untouched.
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test } from '@playwright/test';
import { PlaywrightVirtualDesktopAppAuditDriver } from '../../swissknife/src/services/apps/virtual-desktop-app-audit-playwright-driver';
import { runVirtualDesktopAppAudit } from '../../swissknife/src/services/apps/virtual-desktop-app-audit-runner';
import { VIRTUAL_DESKTOP_APP_MANIFEST } from '../../swissknife/src/services/apps/virtual-desktop-app-manifest';

const HERE = dirname(fileURLToPath(import.meta.url));
const SWISSKNIFE_ROOT = '/home/hatch/workspace/lift_coding/swissknife';
const SCREENSHOT_ROOT = join(
  SWISSKNIFE_ROOT,
  'test-results',
  'virtual-desktop-ipfs-mcp-orb',
  'app-screenshots',
  'svd-132-playwright',
);
const BATCH = Number(process.env.SVD_BATCH || '0');
const BATCH_SIZE = Number(process.env.SVD_BATCH_SIZE || '15');

test(`SVD-132 audit batch ${BATCH}`, async ({ page }) => {
  test.setTimeout(30 * 60 * 1000); // scratch-harness local run parameter
  const entries = VIRTUAL_DESKTOP_APP_MANIFEST.slice(
    BATCH * BATCH_SIZE,
    (BATCH + 1) * BATCH_SIZE,
  );
  expect(entries.length).toBeGreaterThan(0);
  const driver = new PlaywrightVirtualDesktopAppAuditDriver(page, '/');
  const evidence = await runVirtualDesktopAppAudit({
    driver,
    manifest: entries as typeof VIRTUAL_DESKTOP_APP_MANIFEST,
    generatedAt: new Date().toISOString(),
    screenshotRoot: SCREENSHOT_ROOT,
    repoRoot: SWISSKNIFE_ROOT,
  });
  mkdirSync(HERE, { recursive: true });
  writeFileSync(
    join(HERE, `svd132-batch-${BATCH}.json`),
    `${JSON.stringify(evidence, null, 2)}\n`,
  );
  console.log(
    `BATCH ${BATCH}: apps=${evidence.apps.length} passed=${
      evidence.apps.filter((a: { status: string }) => a.status === 'passed').length
    } screenshots=${evidence.summary.screenshot_count}`,
  );
});
