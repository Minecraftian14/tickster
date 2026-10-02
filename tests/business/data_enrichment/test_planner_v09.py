from __future__ import annotations

from datetime import datetime, timezone

import pytest

from data_enrichment import (
    CORE_MARKET_PROFILE,
    DependencyPlanner,
    EnrichmentContext,
    EnrichmentPipeline,
    EnrichmentRegistry,
    ProfilePlanner,
    SimpleReturnEnricher,
    ReturnSummaryEnricher,
    RESEARCH_CORE_PROFILE,
    default_profile_registry,
    default_registry,
    execute_plan,
)


class ProviderA:
    name = "test.provider_a"
    version = "1.0.0"
    requires = frozenset()
    provides = frozenset({"test.shared"})

    def enrich(self, context):
        from data_enrichment import EnrichmentResult
        return EnrichmentResult(enricher=self.name, enricher_version=self.version)


class ProviderB(ProviderA):
    name = "test.provider_b"


def test_registry_indexes_capability_providers():
    registry = EnrichmentRegistry()
    registry.register(ProviderA())
    registry.register(ProviderB())
    assert [x.name for x in registry.providers_for("test.shared")] == ["test.provider_a", "test.provider_b"]


def test_dependency_planner_reuses_available_capabilities():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    planner = DependencyPlanner(registry)
    plan = planner.plan(["market.simple_return"], available={"price.close"})
    assert plan.step_names == ("market.simple_return",)
    assert "price.close" in plan.reused_capabilities
    assert plan.is_executable


def test_dependency_planner_reports_missing_external_capability():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    plan = DependencyPlanner(registry).plan(["market.simple_return"])
    assert plan.missing_capabilities == frozenset({"price.close"})
    assert plan.steps == ()
    assert not plan.is_executable


def test_dependency_planner_resolves_transitive_provider():
    registry = EnrichmentRegistry()

    class ProviderPrice:
        name = "test.price"
        version = "1.0.0"
        requires = frozenset()
        provides = frozenset({"price.close"})

        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    class Consumer:
        name = "test.consumer"
        version = "1.0.0"
        requires = frozenset({"price.close"})
        provides = frozenset({"test.output"})

        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    registry.register(Consumer())
    registry.register(ProviderPrice())
    plan = DependencyPlanner(registry).plan(["test.consumer"])
    assert plan.step_names == ("test.price", "test.consumer")
    assert plan.is_executable


def test_ambiguous_provider_requires_explicit_preference():
    registry = EnrichmentRegistry()
    registry.register(ProviderA())
    registry.register(ProviderB())
    class Consumer:
        name = "test.consumer"
        version = "1.0.0"
        requires = frozenset({"test.shared"})
        provides = frozenset({"test.output"})
        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)
    registry.register(Consumer())
    with pytest.raises(ValueError, match="Ambiguous provider"):
        DependencyPlanner(registry).plan(["test.consumer"])
    plan = DependencyPlanner(registry, provider_preferences={"test.shared": "test.provider_b"}).plan(["test.consumer"])
    assert plan.step_names == ("test.provider_b", "test.consumer")


def test_profile_registry_and_planner():
    profiles = default_profile_registry()
    assert "market_core" in profiles.names()
    planner = ProfilePlanner(default_registry(), profiles)
    plan = planner.plan(CORE_MARKET_PROFILE, available={"price.close"})
    assert plan.profile == "market_core"
    from data_enrichment import __version__
    assert plan.profile_version == __version__
    assert plan.is_executable
    assert "market.returns" in plan.step_names


def test_profile_planner_can_resolve_named_profile():
    profiles = default_profile_registry()
    planner = ProfilePlanner(default_registry(), profiles)
    plan = planner.plan("fundamental_core", available={"fundamental.statement"})
    assert plan.is_executable
    assert plan.profile == "fundamental_core"


def test_execute_plan_records_planner_metadata():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    plan = DependencyPlanner(registry).plan(["market.simple_return"], available={"price.close"})
    ctx = EnrichmentContext([], as_of=datetime.now(timezone.utc))
    result = execute_plan(ctx, plan)
    from data_enrichment import __version__
    assert result.enricher_version == __version__
    assert result.metadata["planned_enrichers"] == ["market.simple_return"]


def test_legacy_pipeline_dependency_plan_convenience():
    registry = EnrichmentRegistry()
    registry.register(SimpleReturnEnricher())
    pipeline = EnrichmentPipeline(registry)
    plan = pipeline.dependency_plan(["market.simple_return"], available={"price.close"})
    assert plan.step_names == ("market.simple_return",)


def test_research_core_profile_is_registered_and_plannable():
    profiles = default_profile_registry()
    assert "research_core" in profiles.names()
    planner = ProfilePlanner(default_registry(), profiles)
    available = {
        "price.close",
        "benchmark.close",
        "fundamental.statement",
        "shareholding.snapshot",
        "insider.transaction",
        "large.deal",
        "company.event",
    }
    plan = planner.plan(RESEARCH_CORE_PROFILE, available=available)
    assert plan.profile == "research_core"
    assert plan.is_executable
    assert "market.returns" in plan.step_names
    assert "fundamental.growth" in plan.step_names


def test_dependency_planner_does_not_plan_provider_with_missing_dependency():
    registry = EnrichmentRegistry()

    class BrokenProvider:
        name = "test.broken_provider"
        version = "1.0.0"
        requires = frozenset({"test.missing"})
        provides = frozenset({"test.shared"})

        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    class Consumer:
        name = "test.consumer_missing"
        version = "1.0.0"
        requires = frozenset({"test.shared"})
        provides = frozenset({"test.output_missing"})

        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    registry.register(BrokenProvider())
    registry.register(Consumer())
    plan = DependencyPlanner(registry).plan(["test.consumer_missing"])
    assert not plan.is_executable
    assert plan.steps == ()
    assert plan.missing_capabilities == frozenset({"test.missing"})


def test_dependency_planner_detects_cycle():
    registry = EnrichmentRegistry()

    class A:
        name = "test.cycle_a"
        version = "1.0.0"
        requires = frozenset({"test.cap_b"})
        provides = frozenset({"test.cap_a"})
        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    class B:
        name = "test.cycle_b"
        version = "1.0.0"
        requires = frozenset({"test.cap_a"})
        provides = frozenset({"test.cap_b"})
        def enrich(self, context):
            from data_enrichment import EnrichmentResult
            return EnrichmentResult(enricher=self.name, enricher_version=self.version)

    registry.register(A())
    registry.register(B())
    with pytest.raises(ValueError, match="Cyclic enrichment dependency"):
        DependencyPlanner(registry).plan(["test.cycle_a"])


def test_profile_available_capabilities_are_effective_plan_inputs():
    profiles = default_profile_registry()
    profile = profiles.get("market_core")
    from dataclasses import replace
    profile = replace(profile, available_capabilities=frozenset({"price.close"}))
    planner = ProfilePlanner(default_registry(), profiles)
    plan = planner.plan(profile)
    assert plan.is_executable
    assert "price.close" in plan.available_capabilities

