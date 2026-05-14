from __future__ import annotations

from models import (
    ConnectionConstraint,
    RailwayInstance,
    RouteLeg,
    TrainRoute,
    TrackSegment,
)


def build_sample_instance() -> RailwayInstance:
    period = 60

    segments = (
        TrackSegment(id="S_AB", name="A-B", min_travel=8, max_travel=10, is_single_track=True),
        TrackSegment(id="S_BC", name="B-C", min_travel=6, max_travel=8, is_single_track=True),
        TrackSegment(id="S_CD", name="C-D", min_travel=7, max_travel=9, is_single_track=True),
        TrackSegment(id="S_BE", name="B-E", min_travel=5, max_travel=7, is_single_track=True),
    )

    routes = (
        TrainRoute(
            id="T1",
            name="Line 1",
            earliest_departure=0,
            latest_departure=15,
            target_departure=5,
            legs=(
                RouteLeg(id="L1", segment_id="S_AB", from_station="A", to_station="B", min_duration=8, max_duration=10),
                RouteLeg(id="L2", segment_id="S_BC", from_station="B", to_station="C", min_duration=6, max_duration=8),
                RouteLeg(id="L3", segment_id="S_CD", from_station="C", to_station="D", min_duration=7, max_duration=9),
            ),
        ),
        TrainRoute(
            id="T2",
            name="Line 2",
            earliest_departure=10,
            latest_departure=40,
            target_departure=15,
            legs=(
                RouteLeg(id="L1", segment_id="S_BE", from_station="B", to_station="E", min_duration=5, max_duration=7),
                RouteLeg(id="L2", segment_id="S_BC", from_station="E", to_station="C", min_duration=6, max_duration=8),
            ),
        ),
        TrainRoute(
            id="T3",
            name="Line 3",
            earliest_departure=12,
            latest_departure=30,
            target_departure=20,
            legs=(
                RouteLeg(id="L1", segment_id="S_AB", from_station="A", to_station="B", min_duration=9, max_duration=11),
                RouteLeg(id="L2", segment_id="S_BE", from_station="B", to_station="E", min_duration=5, max_duration=7),
            ),
        ),
    )

    connections = (
        ConnectionConstraint(from_train_id="T1", to_train_id="T2", min_transfer=2, max_transfer=8),
    )

    station_platforms = {
        "B": 2,
        "C": 1,
    }

    return RailwayInstance(
        period=period,
        segments=segments,
        routes=routes,
        connections=connections,
        headway=2,
        station_platforms=station_platforms,
    )
