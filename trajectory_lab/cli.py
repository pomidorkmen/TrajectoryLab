"""Command-line entry point for iteration 1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from trajectory_lab import __version__
from trajectory_lab.core.simulation import simulate
from trajectory_lab.io.csv_io import export_trajectory_csv
from trajectory_lab.io.json_io import export_result_json, load_experiment, rerun_result_json
from trajectory_lab.plugins.cli_policy import model_id_from_result, registry_for_model
from trajectory_lab.plugins.registry import PluginLoadError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trajectory-lab", description="Low-speed particle research simulator")
    parser.add_argument("--version", action="version", version=f"TrajectoryLab {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run an experiment JSON")
    run_parser.add_argument("experiment", type=Path)
    run_parser.add_argument("--json-out", type=Path, default=Path("trajectory_result.json"))
    run_parser.add_argument("--csv-out", type=Path, default=Path("trajectory_result.csv"))
    run_parser.add_argument(
        "--allow-python-plugins", action="store_true",
        help="Execute trusted Python plugins from ~/.trajectory_lab/models (arbitrary code)",
    )

    verify_parser = subparsers.add_parser("verify", help="re-run a result JSON and compare checksum")
    verify_parser.add_argument("result", type=Path)
    verify_parser.add_argument(
        "--allow-python-plugins", action="store_true",
        help="Execute trusted Python plugins from ~/.trajectory_lab/models (arbitrary code)",
    )
    return parser


def main() -> int:
    """CLI main function."""
    args = _build_parser().parse_args()
    if args.command == "run":
        experiment = load_experiment(args.experiment)
        try:
            registry = registry_for_model(
                experiment.drag.model, allow_python_plugins=args.allow_python_plugins
            )
        except PluginLoadError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        trajectory = simulate(
            experiment.to_core_config(registry),
            method=experiment.method,
            rtol=experiment.rtol,
            atol=experiment.atol,
        )
        export_result_json(args.json_out, experiment, trajectory)
        export_trajectory_csv(args.csv_out, trajectory)
        print(f"Experiment: {experiment.name}")
        print(f"Samples: {trajectory.time_s.size}")
        print(f"Duration: {trajectory.time_s[-1]:.6f} s")
        print(f"Final position: {trajectory.position_m[-1].tolist()} m")
        print(f"Final speed: {trajectory.speed_m_s[-1]:.6f} m/s")
        print(f"Trajectory SHA-256: {trajectory.checksum_sha256}")
        for warning in trajectory.warnings:
            print(f"WARNING: {warning}")
        print(f"JSON: {args.json_out}")
        print(f"CSV:  {args.csv_out}")
        return 0

    if args.command == "verify":
        try:
            model_id = model_id_from_result(args.result)
            registry = registry_for_model(
                model_id, allow_python_plugins=args.allow_python_plugins
            )
        except (PluginLoadError, OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        _, trajectory, expected = rerun_result_json(args.result, registry)
        if expected is None:
            print("No stored trajectory checksum in this JSON.")
            return 2
        print(f"Expected: {expected}")
        print(f"Actual:   {trajectory.checksum_sha256}")
        if trajectory.checksum_sha256 == expected:
            print("Checksum match.")
            return 0
        print("Checksum mismatch; inspect version and numerical settings.")
        return 1

    return 2
