# NS026 provider qualification evidence

The current historical development implementation is the [reviewed host service](host_service/README.md). It uses one exact development grant, one fixed HTTP proposal, an explicitly reviewed sealed candidate, a separate cold score and a signed result. Pilot/final units remain locked; [scorer trust limits](SCORER_TRUST_LIMITS.md) remain explicit.

`run_qualification.py`, `development_invocation/`, `historical/` and the old `qualification_report.json` preserve the original provider-authored draft and its evidence. That draft's actual API call used an addition fixture, and its historical score was a separate unchanged-candidate operation. These are not a real historical model-to-repair qualification. The old run script is disabled to prevent a fresh, ungranted duplicate fixture call. Do not overwrite its retained reports or interpret them as current completion evidence.

Current evidence is `host_receipts/<grant>/` (public signed metadata only), `historical_development/` (actual client import, same-grant resume and signature-only rescore), and `host_service/` (durable service sources, normal constructed qualifications and trust documentation). Runtime queue files and signing keys stay outside Git.

Run `python3 papers/completion/neurosymbolic_supervision/qualification/production_provider/validate_production_provider.py` from the paper repository to validate current retained evidence without any provider or scorer call. Until the actual reviewed signed result and client artifacts exist, this check fails rather than granting credit to the legacy fixture.
