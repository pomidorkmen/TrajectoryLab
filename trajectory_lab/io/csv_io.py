"""CSV export for complete sampled trajectories."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from trajectory_lab.core.simulation import Trajectory


COLUMNS = (
    "time_s",
    "x_m",
    "y_m",
    "z_m",
    "vx_m_s",
    "vy_m_s",
    "vz_m_s",
    "speed_m_s",
    "relative_speed_m_s",
    "mach",
    "kinetic_energy_j",
    "reynolds",
    "cd",
)


def export_trajectory_csv(path: str | Path, trajectory: Trajectory) -> None:
    """Export numerical columns and provenance comment lines."""
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        stream.write("# TrajectoryLab trajectory export v1.0\n")
        stream.write("# provenance=" + json.dumps(trajectory.provenance, sort_keys=True) + "\n")
        stream.write(f"# sha256={trajectory.checksum_sha256}\n")
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        for index, time_s in enumerate(trajectory.time_s):
            position = trajectory.position_m[index]
            velocity = trajectory.velocity_m_s[index]
            writer.writerow(
                [
                    f"{time_s:.12e}",
                    *(f"{value:.12e}" for value in position),
                    *(f"{value:.12e}" for value in velocity),
                    f"{trajectory.speed_m_s[index]:.12e}",
                    f"{trajectory.relative_speed_m_s[index]:.12e}",
                    f"{trajectory.mach[index]:.12e}",
                    f"{trajectory.kinetic_energy_j[index]:.12e}",
                    f"{trajectory.reynolds[index]:.12e}",
                    f"{trajectory.cd[index]:.12e}",
                ]
            )
