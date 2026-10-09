from data_enrichment import ContextPackBuilder, FULL_RESEARCH_CONTEXT, EnrichmentResult
from data_foundation import CanonicalBundle
from data_representation import render_context_pack


def render_data(dataset: list[tuple[EnrichmentResult, CanonicalBundle]]) -> list[str]:
    reports = []
    for research in dataset:
        result, bundle = research
        pack = ContextPackBuilder().build([result], FULL_RESEARCH_CONTEXT, source_records=bundle.canonical_records)
        reports.append(render_context_pack(pack))

    return reports


main_callable = render_data
