from __future__ import annotations

from typing import Any

from .base import BackendComputation, BackendUnavailableError, OptionalBackend


class FinanceToolkitBackend(OptionalBackend):
    """Execute FinanceToolkit calculations on caller-supplied canonicalized datasets."""

    name = "financetoolkit"
    version = "0.7.0"
    dependency_name = "financetoolkit"
    dependency_version = "2.2.1"
    capabilities = frozenset({
        "ratios",
        "efficiency",
        "liquidity",
        "profitability",
        "solvency",
        "valuation",
    })

    def _module(self):
        try:
            import financetoolkit  # type: ignore
        except ImportError as exc:
            raise BackendUnavailableError(
                "FinanceToolkit is not installed; install the optional 'financetoolkit' extra."
            ) from exc
        return financetoolkit

    def available(self) -> bool:
        try:
            self._module()
        except BackendUnavailableError:
            return False
        return True

    @staticmethod
    def _require_data(data: Any) -> dict[str, Any]:
        if not isinstance(data, dict):
            raise TypeError("FinanceToolkit calculations require a mapping of caller-supplied datasets.")
        required = {"tickers", "balance", "income", "cash"}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"FinanceToolkit input is missing required datasets: {missing}")
        return dict(data)

    def _toolkit(self, data: dict[str, Any], **kwargs: Any):
        module = self._module()
        Toolkit = getattr(module, "Toolkit", None)
        if Toolkit is None:
            raise BackendUnavailableError("Installed FinanceToolkit does not expose Toolkit.")
        constructor_kwargs = {
            "tickers": data["tickers"],
            "balance": data["balance"],
            "income": data["income"],
            "cash": data["cash"],
            "format_location": data.get("format_location"),
            "reverse_dates": data.get("reverse_dates", False),
        }
        constructor_kwargs.update(data.get("toolkit_kwargs", {}))
        constructor_kwargs.update(kwargs)
        constructor_kwargs = {k: v for k, v in constructor_kwargs.items() if v is not None}
        return Toolkit(**constructor_kwargs)

    def compute(self, capability: str, data: Any, **kwargs: Any) -> BackendComputation:
        if capability not in self.capabilities:
            raise ValueError(f"Unsupported FinanceToolkit capability: {capability}")
        supplied = self._require_data(data)
        toolkit = self._toolkit(supplied)
        ratios = toolkit.ratios
        method_names = {
            "ratios": "collect_all_ratios",
            "efficiency": "collect_efficiency_ratios",
            "liquidity": "collect_liquidity_ratios",
            "profitability": "collect_profitability_ratios",
            "solvency": "collect_solvency_ratios",
            "valuation": "collect_valuation_ratios",
        }
        method = getattr(ratios, method_names[capability], None)
        if method is None:
            raise BackendUnavailableError(
                f"Installed FinanceToolkit does not expose the requested {capability} collector."
            )
        result = method(**kwargs)
        return BackendComputation(
            backend=self.name,
            capability=capability,
            value=result,
            backend_version=self.dependency_version,
            parameters=dict(kwargs),
            metadata={"data_source_policy": "caller_supplied_only"},
        )
