from datetime import date

from data_foundation.relationships import make_relationship, relationship_id, index_relationships


def test_relationship_id_is_stable():
    assert relationship_id("A", "relates_to", "B") == relationship_id("A", "relates_to", "B")


def test_relationship_id_distinguishes_validity():
    assert relationship_id("A", "relates_to", "B", valid_from=date(2026, 1, 1)) != relationship_id("A", "relates_to", "B", valid_from=date(2026, 2, 1))


def test_relationship_index():
    edge = make_relationship("R1", "relates_to_instrument", "I1", source="nse")
    indexed = index_relationships([edge])
    assert indexed["R1"][0].object_id == "I1"
