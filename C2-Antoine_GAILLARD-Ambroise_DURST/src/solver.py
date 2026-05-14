from __future__ import annotations

from itertools import combinations
from typing import Dict, Optional, Tuple

try:
    from ortools.sat.python import cp_model
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "The OR-Tools package is required for RailwaySolver. Install it with `pip install ortools`."
    ) from exc

from models import (
    ConnectionConstraint,
    RailwayInstance,
    RailwaySchedule,
    RouteLeg,
    TrainLegAssignment,
)


class RailwaySolver:
    def __init__(self, instance: RailwayInstance, max_time_seconds: float = 10.0):
        self.instance = instance
        self.max_time_seconds = max_time_seconds

    def solve(
        self,
        fixed_starts: Optional[Dict[Tuple[str, str], int]] = None,
        baseline_schedule: Optional[RailwaySchedule] = None,
    ) -> RailwaySchedule:
        model = cp_model.CpModel()
        period = self.instance.period

        start_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        duration_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        end_vars: Dict[Tuple[str, str], cp_model.IntVar] = {}
        intervals: Dict[Tuple[str, str], cp_model.IntervalVar] = {}

        route_first_leg_start: Dict[str, cp_model.IntVar] = {}
        route_last_leg_end: Dict[str, cp_model.IntVar] = {}

        segment_intervals: Dict[str, list[cp_model.IntervalVar]] = {}
        segment_interval_data: Dict[cp_model.IntervalVar, Tuple[cp_model.IntVar, cp_model.IntVar, str]] = {}

        for route in self.instance.routes:
            route_start = None
            route_end = None
            for leg in route.legs:
                key = (route.id, leg.id)
                start = model.NewIntVar(0, period - 1, f"{route.id}_{leg.id}_start")
                duration = model.NewIntVar(leg.min_duration, leg.max_duration, f"{route.id}_{leg.id}_dur")
                end = model.NewIntVar(0, period + leg.max_duration + 10, f"{route.id}_{leg.id}_end")
                interval = model.NewIntervalVar(start, duration, end, f"{route.id}_{leg.id}_interval")

                start_vars[key] = start
                duration_vars[key] = duration
                end_vars[key] = end
                intervals[key] = interval
                segment_intervals.setdefault(leg.segment_id, []).append(interval)
                segment_interval_data[interval] = (start, end, route.id)

                model.Add(end == start + duration)

                if route_start is None:
                    route_start = start
                if route_end is not None:
                    model.Add(start >= route_end)
                route_end = end

                if fixed_starts and key in fixed_starts:
                    model.Add(start == fixed_starts[key])

            if route_start is None or route_end is None:
                raise ValueError(f"Route {route.id} has no defined legs.")
            route_first_leg_start[route.id] = route_start
            route_last_leg_end[route.id] = route_end
            model.Add(route_start >= route.earliest_departure)
            model.Add(route_start <= route.latest_departure)

        for connection in self.instance.connections:
            if connection.from_train_id not in route_last_leg_end or connection.to_train_id not in route_first_leg_start:
                raise KeyError("Connection references unknown train route.")
            source_end = route_last_leg_end[connection.from_train_id]
            destination_start = route_first_leg_start[connection.to_train_id]
            model.Add(destination_start >= source_end + connection.min_transfer)
            model.Add(destination_start <= source_end + connection.max_transfer)

        for segment_id, interval_list in segment_intervals.items():
            segment = self.instance.segment_by_id(segment_id)
            if segment.is_single_track or segment.capacity <= 1:
                model.AddNoOverlap(interval_list)
                for first, second in combinations(interval_list, 2):
                    start_a, end_a, route_a = segment_interval_data[first]
                    start_b, end_b, route_b = segment_interval_data[second]
                    if route_a == route_b:
                        continue
                    order_ab = model.NewBoolVar(f"order_{route_a}_{route_b}_{segment_id}")
                    model.Add(start_b >= end_a + self.instance.headway).OnlyEnforceIf(order_ab)
                    model.Add(start_a >= end_b + self.instance.headway).OnlyEnforceIf(order_ab.Not())

        penalty_vars: list[cp_model.IntVar] = []
        for route in self.instance.routes:
            target = route.target_departure
            offset_var = model.NewIntVar(0, period, f"{route.id}_offset_dev")
            model.AddAbsEquality(offset_var, route_first_leg_start[route.id] - target)
            penalty_vars.append(offset_var)

        if baseline_schedule is not None:
            for route in self.instance.routes:
                baseline_first = baseline_schedule.get_train_first_leg(route.id).start
                baseline_var = model.NewIntVar(0, period, f"{route.id}_baseline_dev")
                model.AddAbsEquality(baseline_var, route_first_leg_start[route.id] - baseline_first)
                penalty_vars.append(baseline_var)

        model.Minimize(sum(penalty_vars))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = 8

        status = solver.Solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            raise RuntimeError("No feasible schedule found for the instance.")

        assignments = []
        for route in self.instance.routes:
            for leg in route.legs:
                key = (route.id, leg.id)
                start = solver.Value(start_vars[key])
                duration = solver.Value(duration_vars[key])
                end = solver.Value(end_vars[key])
                assignments.append(
                    TrainLegAssignment(
                        train_id=route.id,
                        leg_id=leg.id,
                        segment_id=leg.segment_id,
                        from_station=leg.from_station,
                        to_station=leg.to_station,
                        start=start,
                        duration=duration,
                        end=end,
                    )
                )

        return RailwaySchedule(period=self.instance.period, assignments=tuple(assignments))
