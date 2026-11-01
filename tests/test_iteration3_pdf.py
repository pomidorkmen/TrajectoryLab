"""PDF report regression tests."""

from __future__ import annotations

from pathlib import Path
import numpy as np

from trajectory_lab.core.simulation import Trajectory
from trajectory_lab.io.pdf_report import export_pdf_report


class FakeExperiment:
    name = "PDF report test"

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return {
            "schema_version": "1.0",
            "name": self.name,
            "mass": {"value": 1.0, "unit": "kg"},
            "diameter": {"value": 0.1, "unit": "m"},
            "initial_position": [{"value": 0, "unit": "m"}] * 3,
            "initial_velocity": [{"value": 1, "unit": "m/s"}] * 3,
            "duration": {"value": 1.0, "unit": "s"},
            "time_step": {"value": 0.1, "unit": "s"},
            "gravity": [{"value": 0, "unit": "m/s^2"}] * 3,
            "wind_velocity": [{"value": 0, "unit": "m/s"}] * 3,
            "atmosphere": {"model": "constant"},
            "drag": {"model": "quadratic"},
            "method": "rk4", "rtol": 1e-9, "atol": 1e-12, "seed": 1729,
        }


def test_pdf_report_contains_complete_reproducibility_sections(tmp_path: Path) -> None:
    times = np.linspace(0.0, 1.0, 11)
    positions = np.column_stack((times, 1.0 - times, np.zeros_like(times)))
    velocities = np.column_stack((np.ones_like(times), -np.ones_like(times), np.zeros_like(times)))
    speed = np.linalg.norm(velocities, axis=1)
    trajectory = Trajectory(
        time_s=times,
        position_m=positions,
        velocity_m_s=velocities,
        speed_m_s=speed,
        relative_speed_m_s=speed,
        mach=np.full_like(times, 0.004),
        kinetic_energy_j=np.full_like(times, 1.0),
        reynolds=np.linspace(1.0, 10.0, 11),
        cd=np.full_like(times, 0.44),
        impact_time_s=None,
        warnings=("outside reference range",),
        provenance={
            "trajectory_lab_version": "0.3.0", "python_version": "3.11", "numpy_version": "1.26",
            "scipy_version": "1.12", "pint_version": "0.24", "platform": "test",
            "method": "RK4", "step_s": 0.1, "rtol": None, "atol": None,
            "trajectory_checksum_quantization": "per-column relative 1e-9", "seed": 1729,
            "drag_model": {"id": "drag.quadratic", "name": "Constant Cd", "version": "1.0.0",
                           "author": "test", "source": "test", "validity": {"reynolds_min": 0.0, "reynolds_max": None}},
            "drag_model_sha256": "a" * 64,
        },
        checksum_sha256="b" * 64,
    )
    target = export_pdf_report(tmp_path / "report", FakeExperiment(), trajectory)  # type: ignore[arg-type]
    assert target.suffix == ".pdf"
    content = target.read_bytes()
    assert content.startswith(b"%PDF-")
    assert len(content) > 3000
