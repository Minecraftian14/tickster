from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .._version import __version__


class ContextSectionSpec(BaseModel):
    """Declarative selection rule for one context-pack section."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    include_all_summaries: bool = False
    summary_types: tuple[str, ...] = ()
    summary_prefixes: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    metric_prefixes: tuple[str, ...] = ()
    max_points_per_series: int | None = None
    include_observations: bool = False
    include_series: bool = True
    include_summaries: bool = True


class ContextPackProfile(BaseModel):
    """Configuration for assembling a multi-resolution analytical context."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = __version__
    description: str = ""
    sections: tuple[ContextSectionSpec, ...] = Field(default_factory=tuple)
    max_items: int | None = None
    max_points: int | None = None
    tail_series_points: bool = True


class ContextItemRef(BaseModel):
    """Reference to an item selected into a pack."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["observation", "series", "summary"]
    derived_id: str
    section: str
    included_points: int | None = None
    omitted_points: int | None = None


class ContextPack(BaseModel):
    """Materialized, compact analytical view over derived enrichment outputs.

    This object is not an LLM representation. It contains selected derived
    objects plus selection metadata and lineage references, leaving serialization
    and language-model formatting to downstream packages.
    """

    model_config = ConfigDict(extra="allow")

    pack_id: str
    profile: str
    profile_version: str
    instrument_id: str | None = None
    as_of: datetime | None = None
    observations: list[Any] = Field(default_factory=list)
    series: list[Any] = Field(default_factory=list)
    summaries: list[Any] = Field(default_factory=list)
    items: list[ContextItemRef] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def item_count(self) -> int:
        return len(self.observations) + len(self.series) + len(self.summaries)

    @property
    def point_count(self) -> int:
        return sum(len(series.points) for series in self.series)


@dataclass(frozen=True)
class _SelectionBudget:
    max_items: int | None
    max_points: int | None
    tail_series_points: bool
    item_count: int = 0
    point_count: int = 0

    def can_add_item(self) -> bool:
        return self.max_items is None or self.item_count < self.max_items

@dataclass
class _MutableBudget:
    max_items: int | None
    max_points: int | None
    tail_series_points: bool
    item_count: int = 0
    point_count: int = 0

    def can_add_item(self) -> bool:
        return self.max_items is None or self.item_count < self.max_items

    def remaining_points(self) -> int | None:
        if self.max_points is None:
            return None
        return max(self.max_points - self.point_count, 0)
