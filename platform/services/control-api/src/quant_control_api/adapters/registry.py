from __future__ import annotations

from collections.abc import Iterable, Iterator

from .base import AnalysisProjectAdapter
from .best_factor import BestFactorAdapter
from .fear_greed import FearGreedAdapter
from .momentum import MomentumAdapter


class ProjectAdapterRegistry:
    def __init__(self, adapters: Iterable[AnalysisProjectAdapter]) -> None:
        by_project: dict[str, AnalysisProjectAdapter] = {}
        for adapter in adapters:
            if adapter.project_id in by_project:
                raise ValueError(f"duplicate project adapter: {adapter.project_id}")
            by_project[adapter.project_id] = adapter
        if not by_project:
            raise ValueError("at least one project adapter is required")
        self._by_project = by_project

    def get(self, project_id: str) -> AnalysisProjectAdapter | None:
        return self._by_project.get(project_id)

    def require(self, project_id: str) -> AnalysisProjectAdapter:
        try:
            return self._by_project[project_id]
        except KeyError as exc:
            raise KeyError(f"project adapter is not registered: {project_id}") from exc

    def __iter__(self) -> Iterator[AnalysisProjectAdapter]:
        return iter(self._by_project.values())

    @property
    def project_ids(self) -> tuple[str, ...]:
        return tuple(self._by_project)


def default_project_adapters() -> ProjectAdapterRegistry:
    return ProjectAdapterRegistry(
        (BestFactorAdapter(), MomentumAdapter(), FearGreedAdapter())
    )
