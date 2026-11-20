"""Defences are switchable hooks. `DefenceSet` attaches the enabled ones to a run."""

from dataclasses import dataclass

from swarmshield.config import DEFENCES
from swarmshield.defences import baseline
from swarmshield.defences.majority import merge_reports
from swarmshield.defences.provenance import write_filter
from swarmshield.defences.sanitiser import message_filter

BASELINES = ("baseline_blocklist",)  # evaluation only, not one of the three defences


@dataclass(frozen=True)
class DefenceSet:
    names: frozenset[str] = frozenset()

    def __post_init__(self):
        unknown = set(self.names) - set(DEFENCES) - set(BASELINES)
        if unknown:
            raise ValueError(f"unknown defences: {sorted(unknown)}")

    @property
    def fence(self) -> bool:
        return "d1_provenance" in self.names

    @property
    def majority(self) -> bool:
        return "d3_majority" in self.names

    def attach(self, memory, router, docs_by_agent: dict[str, list[dict]]) -> None:
        if "d1_provenance" in self.names:
            memory.write_filters.append(write_filter(docs_by_agent, memory))
        if "d2_sanitiser" in self.names:
            router.filters.append(message_filter)
        if "baseline_blocklist" in self.names:
            memory.write_filters.append(baseline.write_filter)
            router.filters.append(baseline.message_filter)


__all__ = ["DefenceSet", "merge_reports"]
