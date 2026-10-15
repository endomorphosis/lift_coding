"""Qualify emitted retrieval decoding and genuine audits in Harbor, without providers."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import shlex
import tempfile
import time

from harbor.environments.docker.docker import DockerEnvironment
from harbor.models.task.task import Task
from harbor.models.trial.paths import TrialPaths
from benchmarks.agent_supervisor.container_coding.terminal_deployment import (
    INPUT_SNAPSHOT, PYTHON, ROOT, deploy_supervisor, runtime_environment,
)
from benchmarks.agent_supervisor.container_coding.container_worker_deployment import deploy_worker_boundary


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


async def main(args):
    output = args.output.absolute()
    output.mkdir(exist_ok=False)
    manifest_path = args.archive / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    task = Task(args.task)
    paths = TrialPaths(output / 'harbor')
    paths.mkdir()
    environment = DockerEnvironment(environment_dir=task.paths.environment_dir,
        environment_name=task.short_name, session_id='ipfs-compact-qual-' + str(int(time.time())),
        trial_paths=paths, task_env_config=task.config.environment, keep_containers=False)
    started = time.monotonic()
    summary = {'schema': 'terminal-compact-installed-runtime-qualification@1',
        'qualified': False, 'provider_calls': 0, 'official_verifier_executed': False,
        'archive_sha256': manifest['archive_sha256'], 'controller_sha256': digest(__file__),
        'runtime_manifest_sha256': digest(manifest_path),
        'probe_sha256': digest(args.probe), 'synthetic_auth_fixture_only': True,
        'audit_probe_sha256': digest(args.audit_probe) if args.audit_probe is not None else None}

    def event(stage):
        print(json.dumps({'stage': stage, 'seconds': round(time.monotonic() - started, 3)}), flush=True)

    async def execute(label, argv, *, user='root', env=None, timeout=300):
        result = await environment.exec(command=shlex.join(argv), cwd='/app', user=user,
            env=env, timeout_sec=timeout)
        (output / (label + '.stdout')).write_text(result.stdout or '')
        (output / (label + '.stderr')).write_text(result.stderr or '')
        if result.return_code:
            raise RuntimeError(label + ' failed; see retained provider-free logs')
        return result

    try:
        event('start-original-task-container')
        await environment.start(force_build=True)
        event('deploy-pinned-runtime')
        deployment = await deploy_supervisor(environment, archive_dir=args.archive,
            output=output / 'deployment', auth_json=None, install_codex=True)
        event('install-synthetic-worker-auth-fixture')
        with tempfile.TemporaryDirectory() as temp:
            auth = Path(temp) / 'synthetic-auth.json'
            auth.write_text('{}\n')
            await environment.upload_file(auth, ROOT + '/codex-auth/auth.json')
        await execute('synthetic-auth-permissions', ['python3', '-I', '-c',
            "import os; p='/opt/ipfs-supervisor/codex-auth/auth.json'; os.chown(p,1000,1000); os.chmod(p,0o600)"])
        event('qualify-worker-boundary')
        boundary = await deploy_worker_boundary(environment, output=output / 'worker-boundary')
        assert boundary['qualified']
        await environment.upload_file(args.probe, ROOT + '/frontier-worker-probe.py')
        await environment.upload_file(manifest_path, ROOT + '/frontier-runtime-manifest.json')
        await environment.upload_file(args.instruction, ROOT + '/frontier-public-instruction.md')
        protect = "import os; " + "; ".join(
            "os.chown(%r,0,0); os.chmod(%r,0o444)" % (path, path) for path in (
                ROOT + '/frontier-worker-probe.py', ROOT + '/frontier-runtime-manifest.json',
                ROOT + '/frontier-public-instruction.md'))
        await execute('protect-qualification-inputs', ['python3', '-I', '-c', protect])
        await execute('pin-public-source', ['python3', '-I', '-c',
            "import hashlib,pathlib; p=pathlib.Path('/app/bottle.py'); assert hashlib.sha256(p.read_bytes()).hexdigest()=='761756ce31753e526c48d28ccbca13a5d2493b16fe37aff3e1e4d2efaf3a2bba'"])
        event('expand-frontier-as-installed-worker')
        probe = await execute('frontier-probe', [PYTHON, '-P', ROOT + '/frontier-worker-probe.py',
            '--runtime-manifest', ROOT + '/frontier-runtime-manifest.json',
            '--runtime-manifest-sha256', digest(manifest_path), '--archive-sha256', manifest['archive_sha256'],
            '--public-code', '/app/bottle.py', '--public-instruction', ROOT + '/frontier-public-instruction.md'],
            user='supervisor', env=runtime_environment(), timeout=600)
        receipt = json.loads(probe.stdout)
        assert receipt['qualified'] and receipt['provider_calls'] == 0
        compact=receipt['production_quota_probe']['compact_code_retrieval']
        assert compact['qualified'] and compact['worker']['qualified'] and compact['worker']['complete_native_hits']==5
        assert compact['worker']['exact_decoder_native_roundtrip'] is True
        assert compact['worker']['schema'] == 'terminal-installed-compact-retrieval-worker@2'
        assert compact['worker']['guidance_version'] == 2
        assert compact['worker']['exact_advertised_command_executed'] is True
        assert compact['worker']['wire_arguments_manually_appended'] is False
        assert compact['worker']['shell_environment_keys'] == ['SUPERVISOR_CODE_RETRIEVAL_WIRE']
        assert compact['worker']['runtime_archive_sha256'] == manifest['archive_sha256']
        materialized = compact['materialized_worker']
        assert materialized['schema'] == 'terminal-installed-materialized-retrieval-worker@1'
        assert materialized['qualified'] and materialized['uid'] == materialized['euid'] == 1001
        assert materialized['guidance_version'] == 3 and materialized['provider_calls'] == 0
        assert materialized['exact_advertised_command_executed'] is True
        assert materialized['wire_arguments_manually_appended'] is False
        assert materialized['shell_environment_keys'] == []
        assert materialized['exact_decoder_native_roundtrip'] is True and materialized['complete_native_hits'] == 5
        assert materialized['wire_delivery']['materialized'] is True
        assert materialized['wire_delivery']['owner_custody'] is False
        assert materialized['candidate_git_census_unchanged'] is True
        assert materialized['public_cache_source_witnesses_unchanged'] is True
        assert materialized['owner_roots_individually_inaccessible'] is True
        assert materialized['same_uid_wire_hash_mutation_refused'] is True
        assert materialized['same_uid_write_restore_witness_refused'] is True
        assert materialized['exact_positive_wire_cleanup'] == 'removed'
        assert materialized['runtime_archive_sha256'] == manifest['archive_sha256']
        assert digest(args.probe) == summary['probe_sha256']
        if args.audit_probe is not None:
            event('qualify-full-public-installed-audit')
            audit_path=ROOT+'/installed-full-audit-probe.py'
            await environment.upload_file(args.audit_probe,audit_path)
            await execute('protect-full-public-audit-probe',['python3','-I','-c',
                'import os; p='+repr(audit_path)+'; os.chown(p,0,0); os.chmod(p,0o444)'])
            audit_result=await execute('installed-full-public-audit',[PYTHON,'-P',audit_path,
                '--runtime-manifest',ROOT+'/frontier-runtime-manifest.json',
                '--runtime-manifest-sha256',digest(manifest_path),
                '--public-instruction',ROOT+'/frontier-public-instruction.md',
                '--name','full-public-audit-01'],
                user='supervisor',env=runtime_environment(),timeout=600)
            audit_receipt=json.loads(audit_result.stdout.strip().splitlines()[-1])
            assert audit_receipt['qualified'] is True
            assert audit_receipt['runtime_manifest_sha256'] == summary['runtime_manifest_sha256']
            assert audit_receipt['archive_sha256'] == manifest['archive_sha256']
            assert audit_receipt['fixture']['genuine_context_result_metadata_absent'] is True
            assert audit_receipt['fixture']['expected_context_bytes_copied_without_modification'] is True
            assert audit_receipt['native_bundle_negative_controls'] == {
                'digest_tamper_refused': True, 'repinned_foreign_task_refused': True}
            expected_pairs = {(case, mode)
                for case in ('failed_no_publication', 'copied_publication_retired_workspace')
                for mode in ('expanded', 'compact_v2', 'legacy_v1', 'materialized_v3')}
            collections = audit_receipt['collections']
            assert len(collections) == 8
            assert {(row['case'], row['code_retrieval_codec']) for row in collections} == expected_pairs
            assert all(row['status'] == 'verified_all_observed_model_inputs'
                and row['all_observed_coding_inputs_verified'] is True for row in collections)
            assert digest(args.audit_probe) == summary['audit_probe_sha256']
            summary['full_public_installed_audit']=audit_receipt
        after = json.loads((await execute('retained-original-tracked-inputs', ['python3', '-I', '-c', INPUT_SNAPSHOT],
            user='supervisor', env=runtime_environment())).stdout)
        before = deployment['original_inputs']
        assert after['files'] == before['files'] and after['head'] == before['head']
        assert after['report_exists'] == before['report_exists']
        assert digest(manifest_path) == summary['runtime_manifest_sha256']
        assert digest(__file__) == summary['controller_sha256']
        summary.update({'qualified': True, 'runtime_deployment_qualified': deployment['qualified'],
            'worker_boundary_qualified': boundary['qualified'], 'native_cli_cache_used': deployment['codex_native_cache_used'],
            'retrieval_probe': receipt, 'original_tracked_task_inputs_preserved': True,
            'qualification_added_fresh_public_probe_directories_synthetic_owner_controls_and_allocated_worktree': True,
            'signed_plan_admission_claimed': False, 'benchmark_success_claimed': False})
        event('qualified')
    except BaseException as exc:
        summary['failure_type'] = type(exc).__name__
        summary['failure'] = str(exc)
        raise
    finally:
        event('remove-qualification-container')
        try:
            await environment.stop(delete=True)
            summary['qualification_container_removed'] = True
        except Exception as exc:
            summary['cleanup_failure_type'] = type(exc).__name__
            if summary['qualified']:
                raise
        finally:
            summary['elapsed_seconds'] = time.monotonic() - started
            (output / 'qualification.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'task', 'output', 'probe', 'instruction'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--audit-probe',type=Path,required=True)
    asyncio.run(main(parser.parse_args()))
