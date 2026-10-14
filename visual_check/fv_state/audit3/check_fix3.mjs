// Fix-3 check: the new supervisor gateway mappings in the MCP++ desktop
// client — logs.read (accelerate dag/history), content.retrieve (kit
// artifacts GET), receipts.persist (kit artifacts PUT, confirmation-gated,
// CID verified with the production cidForBytes), event-dag.checkpoint
// (kit dag append, confirmation-gated).
import { createRequire } from 'node:module';
const require = createRequire('/home/hatch/workspace/lift_coding/swissknife/scripts/');
const { cidForBytes, stableStringify } = require('/home/hatch/workspace/lift_coding/swissknife/scripts/mcpplusplus-profile-a.cjs');
const { MCPPlusPlusDesktopClient } = await import('/home/hatch/workspace/lift_coding/swissknife/web/js/core/mcp-plus-plus-desktop-client.js');

const jsonResponse = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  text: async () => JSON.stringify(body),
});

const fetchStub = async (url, options = {}) => {
  const method = options.method || 'GET';
  if (url.includes('/mcp/services/ipfs_accelerate_py/mcp') && method === 'POST') {
    const body = JSON.parse(options.body);
    if (body.method === 'mcp++/dag/history') {
      return jsonResponse(200, {
        jsonrpc: '2.0', id: body.id,
        result: { events: [{ event_cid: 'bafyevent1', event_type: 'execution', timestamp: '2026-10-14T00:00:00.000Z', message: 'Queue snapshot recorded.' }], count: 1 },
      });
    }
    throw new Error(`unexpected rpc ${body.method}`);
  }
  if (url.includes('/mcp/services/ipfs_kit_py/mcp/artifacts/') && method === 'GET') {
    const cid = decodeURIComponent(url.split('/mcp/artifacts/')[1]);
    return jsonResponse(200, { found: true, verified: true, backend: 'disk', cid, bytes_base64: Buffer.from('hello').toString('base64'), metadata: null });
  }
  if (url.includes('/mcp/services/ipfs_kit_py/mcp/artifacts/put') && method === 'POST') {
    const body = JSON.parse(options.body);
    const bytes = Buffer.from(body.bytes_base64, 'base64');
    if (cidForBytes(bytes) !== body.cid) return jsonResponse(500, { error: 'Artifact CID does not match its canonical bytes.' });
    return jsonResponse(200, { persisted: true, verified: true, cid: body.cid, backend: 'disk', profile: body.profile, kind: body.kind, service: body.service });
  }
  if (url.includes('/mcp/services/ipfs_kit_py/mcp/dag/append') && method === 'POST') {
    return jsonResponse(200, { event_cid: 'bafycheckpoint1', status: 'recorded' });
  }
  throw new Error(`unexpected fetch ${method} ${url}`);
};

const client = new MCPPlusPlusDesktopClient({ fetch: fetchStub });
const gateway = client.createSupervisorGateway();
const invoke = (capability_id, owner, access, payload) => gateway.invoke({ capability_id, owner, access, payload, correlation_id: `check-${capability_id}` });

const logs = await invoke('supervisor.logs.read', 'ipfs_accelerate_py', 'read', { limit: 50 });
console.log('logs:', logs.state, JSON.stringify(logs.data?.[0]));

const goodCid = cidForBytes(Buffer.from('hello'));
const retrieve = await invoke('supervisor.content.retrieve', 'ipfs_kit_py', 'read', { cid: goodCid });
console.log('retrieve:', retrieve.state, retrieve.data?.cid, 'verified:', retrieve.data?.verified, 'bytes:', retrieve.data?.content_bytes);

const badRetrieve = await invoke('supervisor.content.retrieve', 'ipfs_kit_py', 'read', { cid: 'bafyagenttask1051' });
console.log('retrieve invalid cid:', badRetrieve.state, badRetrieve.reason);

const receiptRecord = { receipt_id: 'rcpt-x', cid: 'bafyabc', owner: 'ipfs_kit_py', created_at: '2026-07-10T12:00:00.000Z' };
const persistDenied = await invoke('supervisor.receipts.persist', 'ipfs_kit_py', 'governed-write', { receipt: receiptRecord });
console.log('persist unconfirmed:', persistDenied.state, persistDenied.reason);

const persist = await invoke('supervisor.receipts.persist', 'ipfs_kit_py', 'governed-write', {
  receipt: receiptRecord, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-x:check',
});
const expectedCid = cidForBytes(Buffer.from(stableStringify(receiptRecord), 'utf8'));
console.log('persist:', persist.state, 'cid:', persist.receipt?.cid, 'expected:', expectedCid, 'match:', persist.receipt?.cid === expectedCid);

const checkpointDenied = await invoke('supervisor.event-dag.checkpoint', 'ipfs_kit_py', 'governed-write', { receipt: receiptRecord });
console.log('checkpoint unconfirmed:', checkpointDenied.state, checkpointDenied.reason);

const checkpoint = await invoke('supervisor.event-dag.checkpoint', 'ipfs_kit_py', 'governed-write', {
  receipt: receiptRecord, confirmation_token: 'confirm-agent-supervisor:receipt:rcpt-x:check',
});
console.log('checkpoint:', checkpoint.state, 'event cid:', checkpoint.data?.event_dag?.cid, 'receipt:', checkpoint.receipt?.receipt_id);

const failures = [];
if (logs.state !== 'available' || logs.data?.[0]?.log_id !== 'bafyevent1' || logs.data?.[0]?.message !== 'Queue snapshot recorded.') failures.push('logs');
if (retrieve.state !== 'available' || retrieve.data?.verified !== true) failures.push('retrieve');
if (badRetrieve.state !== 'unavailable' || badRetrieve.reason !== 'receipt_unavailable') failures.push('bad-retrieve');
if (persistDenied.state !== 'denied' || persistDenied.reason !== 'confirmation_required') failures.push('persist-denied');
if (persist.state !== 'available' || persist.receipt?.cid !== expectedCid) failures.push('persist');
if (checkpointDenied.state !== 'denied' || checkpointDenied.reason !== 'confirmation_required') failures.push('checkpoint-denied');
if (checkpoint.state !== 'available' || checkpoint.data?.event_dag?.cid !== 'bafycheckpoint1') failures.push('checkpoint');
if (failures.length) { console.error('FAIL:', failures.join(',')); process.exit(1); }
console.log('FIX3 CHECK PASSED');
