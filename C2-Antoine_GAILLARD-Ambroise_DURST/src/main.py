from __future__ import annotations

from instance import build_sample_instance
from rescheduler import RailwayRescheduler
from solver import RailwaySolver


def print_schedule(schedule) -> None:
    trains = schedule.assignments_by_train()
    print("Railway timetable for period", schedule.period)
    print("-" * 72)
    for train_id, assignments in sorted(trains.items()):
        print(f"Train {train_id}")
        for leg in sorted(assignments, key=lambda item: item.start):
            print(
                f"  {leg.leg_id}: {leg.from_station}->{leg.to_station} "
                f"[{leg.segment_id}] start={leg.start:2d} dur={leg.duration:2d} end={leg.end:2d}"
            )
        print("-" * 72)


def run_example() -> None:
    instance = build_sample_instance()
    solver = RailwaySolver(instance, max_time_seconds=15.0)
    schedule = solver.solve()
    print("Baseline schedule")
    print_schedule(schedule)

    rescheduler = RailwayRescheduler(max_time_seconds=15.0)
    delayed_schedule = rescheduler.repair_delay(instance, schedule, delayed_train_id="T1", delay_minutes=5)
    print("\nRescheduled timetable after delay on T1")
    print_schedule(delayed_schedule)


if __name__ == "__main__":
    run_example()
