from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class TrackSegment:
    id: str
    name: str
    min_travel: int
    max_travel: int
    is_single_track: bool = True
    capacity: int = 1


@dataclass(frozen=True)
class RouteLeg:
    id: str
    segment_id: str
    from_station: str
    to_station: str
    min_duration: int
    max_duration: int


@dataclass(frozen=True)
class TrainRoute:
    id: str
    name: str
    legs: Tuple[RouteLeg, ...]
    earliest_departure: int
    latest_departure: int
    target_departure: int


@dataclass(frozen=True)
class ConnectionConstraint:
    from_train_id: str
    to_train_id: str
    min_transfer: int
    max_transfer: int


@dataclass(frozen=True)
class RailwayInstance:
    period: int
    segments: Tuple[TrackSegment, ...]
    routes: Tuple[TrainRoute, ...]
    connections: Tuple[ConnectionConstraint, ...] = field(default_factory=tuple)
    headway: int = 1
    station_platforms: Dict[str, int] = field(default_factory=dict)

    def segment_by_id(self, segment_id: str) -> TrackSegment:
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        raise KeyError(f"Segment not found: {segment_id}")

    def route_by_id(self, route_id: str) -> TrainRoute:
        for route in self.routes:
            if route.id == route_id:
                return route
        raise KeyError(f"Train route not found: {route_id}")

    def all_station_names(self) -> List[str]:
        stations: List[str] = []
        for route in self.routes:
            for leg in route.legs:
                if leg.from_station not in stations:
                    stations.append(leg.from_station)
                if leg.to_station not in stations:
                    stations.append(leg.to_station)
        return stations


@dataclass(frozen=True)
class TrainLegAssignment:
    train_id: str
    leg_id: str
    segment_id: str
    from_station: str
    to_station: str
    start: int
    duration: int
    end: int


@dataclass(frozen=True)
class RailwaySchedule:
    period: int
    assignments: Tuple[TrainLegAssignment, ...]

    def assignments_by_train(self) -> Dict[str, Tuple[TrainLegAssignment, ...]]:
        trains: Dict[str, List[TrainLegAssignment]] = {}
        for assignment in self.assignments:
            trains.setdefault(assignment.train_id, []).append(assignment)
        return {train_id: tuple(sorted(items, key=lambda item: item.start)) for train_id, items in trains.items()}

    def get_leg_start(self, train_id: str, leg_id: str) -> int:
        for assignment in self.assignments:
            if assignment.train_id == train_id and assignment.leg_id == leg_id:
                return assignment.start
        raise KeyError(f"No assignment found for train {train_id} leg {leg_id}")

    def get_train_first_leg(self, train_id: str) -> TrainLegAssignment:
        assignments = self.assignments_by_train().get(train_id, ())
        if not assignments:
            raise KeyError(f"Train {train_id} not found in schedule")
        return min(assignments, key=lambda assignment: assignment.start)

    def get_train_last_leg(self, train_id: str) -> TrainLegAssignment:
        assignments = self.assignments_by_train().get(train_id, ())
        if not assignments:
            raise KeyError(f"Train {train_id} not found in schedule")
        return max(assignments, key=lambda assignment: assignment.end)
