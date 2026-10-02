import sys
from pathlib import Path

# The project is developed beside the separately installed foundation package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_enrichment import (
    CONTRACT_VERSION,
    __version__,
    assert_compatible_contract,
    is_compatible_contract,
    public_contract,
    validate_public_contract,
)


def test_package_and_contract_versions_are_1x():
    contract = public_contract()
    assert __version__ == "1.0.0"
    assert contract.package_version == "1.0.0"
    assert contract.contract_version == CONTRACT_VERSION == "1.0"


def test_stable_public_contract_exports_resolve():
    assert validate_public_contract() == ()


def test_contract_compatibility_is_major_version_based():
    assert is_compatible_contract("1.0")
    assert is_compatible_contract("1.7")
    assert not is_compatible_contract("2.0")
    assert_compatible_contract("1.4")
    try:
        assert_compatible_contract("2.0")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected incompatible contract to raise")


def test_contract_guarantees_are_explicit():
    guarantees = public_contract().guarantees
    assert any("deterministic" in item.lower() for item in guarantees)
    assert any("point-in-time" in item.lower() for item in guarantees)
    assert any("optional" in item.lower() for item in guarantees)
