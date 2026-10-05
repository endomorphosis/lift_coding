"""Pure v2 taxonomy controls using declaration-only, never executed Lean fixtures.

The frozen v1 guards and its already admitted 59 cases are not rerun here.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def _module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


v2 = _module("curvature_cache_v2_taxonomy_units", "real_curvature_proof_cache_v2.py")
v1_units = _module("curvature_cache_v1_fixture_only", "test_real_curvature_proof_cache.py")


@pytest.fixture(scope="module")
def declaration_only_v1_arguments():
    return v1_units.declaration_only_arguments.__wrapped__()


def _v2_arguments(original, kind):
    arguments = deepcopy(original)
    dimensions = arguments["cache_dimensions"]
    dimensions["schema"] = v2.DIMENSIONS_SCHEMA
    dimensions["evidence_kind"] = kind
    dimensions["theorem"] = "UnitFixture." + kind
    result = arguments["qualified_result"]
    result["schema"] = v2.RESULT_SCHEMA
    result["native_check"]["theorem_axiom_output"][0]["theorem"] = dimensions["theorem"]
    arguments["expected_cache_dimensions_sha256"] = v2.canonical_sha256(dimensions)
    result["cache_dimensions_sha256"] = arguments["expected_cache_dimensions_sha256"]
    result["native_check_sha256"] = v2.canonical_sha256(result["native_check"])
    arguments["expected_qualified_result_sha256"] = v2.canonical_sha256(result)
    return arguments


@pytest.mark.parametrize("kind", ["real_candidate_quadratic_curvature", "real_scalar_derivative",
    "real_directional_second_derivative", "real_logistic_coefficient_bound", "real_coordinate_geometry",
    "exact_original_rational_arithmetic", "real_objective_gradient_identity", "real_objective_step_descent",
    "original_real_profile_curvature", "original_real_profile_descent"])
def test_accurate_taxonomy_returns_only_advisory_rows(declaration_only_v1_arguments, kind):
    arguments = _v2_arguments(declaration_only_v1_arguments, kind)
    entry = v2.build_real_curvature_proof_cache_entry(**arguments)
    row = v2.lookup_real_curvature_proof_cache(**arguments, entry=entry,
                                               expected_entry_sha256=v2.canonical_sha256(entry))
    assert entry["schema"] == "terminal-ranker-real-curvature-proof-cache-entry@2"
    assert row["evidence_kind"] == kind and row["status"] == "kernel_real_statement_bound"
    assert row["advisory_only"] is True and all(row[key] is False for key in v2._AUTHORITY_FIELDS)
    assert row["full_task_satisfaction"] == "unknown" and row["all32_governing_RPI_exits"] == "OPEN"
    assert row["official_benchmark_score"] is None


@pytest.mark.parametrize("kind", ["native_float_hessian_identity", "whole_source_runtime_equivalence",
    "global_optimizer_convergence", "full_task_satisfaction", "multivariate_Frechet_Hessian_identity"])
def test_prohibited_promotions_refused_after_dimension_and_result_reseals(declaration_only_v1_arguments, kind):
    arguments = _v2_arguments(declaration_only_v1_arguments, kind)
    with pytest.raises(v2.RealCurvatureCacheError, match="evidence and source-translation"):
        v2.build_real_curvature_proof_cache_entry(**arguments)


def test_old_cache_entry_cannot_alias_v2_query(declaration_only_v1_arguments):
    old_entry = v1_units.cache.build_real_curvature_proof_cache_entry(**declaration_only_v1_arguments)
    new_query = _v2_arguments(declaration_only_v1_arguments, "real_candidate_quadratic_curvature")
    assert v2.lookup_real_curvature_proof_cache(**new_query, entry=old_entry,
                                               expected_entry_sha256=v2.canonical_sha256(old_entry)) is None


def test_v2_result_cannot_be_accepted_by_old_cache_schema(declaration_only_v1_arguments):
    new_arguments = _v2_arguments(declaration_only_v1_arguments, "real_candidate_quadratic_curvature")
    new_entry = v2.build_real_curvature_proof_cache_entry(**new_arguments)
    assert v1_units.cache.lookup_real_curvature_proof_cache(**new_arguments, entry=new_entry,
        expected_entry_sha256=v2.canonical_sha256(new_entry)) is None
