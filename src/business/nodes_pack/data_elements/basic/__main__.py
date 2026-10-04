from data_enrichment import ReturnSummaryEnricher
from nodes_pack.data_elements import *


def minimum_example(canonical_records: list[Any], observations: list[Any]) -> Any:
    """The absolute smallest useful application of data_enrichment."""
    market_records = records_for_instrument(canonical_records, TARGET)

    context = EnrichmentContext(
        records=market_records,
        source_observations=observations,
        instrument_id=TARGET,
        as_of=AS_OF,
    )

    result = ReturnSummaryEnricher().enrich(context)
    return result


def data_source_small(*a: int):
    canonical_records, observations = load_foundation()
    return minimum_example(canonical_records, observations)


main_callable = data_source_small


if __name__ == '__main__':
    print(data_source_small().summaries)