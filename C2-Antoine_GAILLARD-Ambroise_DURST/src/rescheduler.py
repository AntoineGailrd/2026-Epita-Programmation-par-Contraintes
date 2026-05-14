from __future__ import annotations

from typing import Dict, Tuple

from models import RailwaySchedule, RailwayInstance
from solver import RailwaySolver


class RailwayRescheduler:
    def __init__(self, max_time_seconds: float = 10.0):
        self.max_time_seconds = max_time_seconds

    def repair_delay(
        self,
        instance: RailwayInstance,
        baseline: RailwaySchedule,
        delayed_train_id: str,
        delay_minutes: int,
    ) -> RailwaySchedule:
        first_leg = baseline.get_train_first_leg(delayed_train_id)
        fixed_starts: Dict[Tuple[str, str], int] = {}
        fixed_starts[(delayed_train_id, first_leg.leg_id)] = first_leg.start + delay_minutes

        solver = RailwaySolver(instance, max_time_seconds=self.max_time_seconds)
        return solver.solve(fixed_starts=fixed_starts, baseline_schedule=baseline)
