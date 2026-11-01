# TrajectoryLab iteration 1 — scientific/build audit

Audit snapshot: 2026-10-30. Source revision: see Git history in this archive.

## Build pipeline

| Requirement | Status | Evidence / limitation |
|---|---|---|
| One root `build.py` | Implemented | No shell/Makefile/CI wrapper is required. |
| Python >= 3.11 check | Implemented | `check_python()` runs before any package work. |
| No administrator rights | Implemented | A project-local `.venv` is created when the script is launched with a base interpreter. |
| Dependency installation | Implemented, environment-blocked here | Missing modules trigger `python -m pip install -e ".[build]"`. PyPI DNS resolution failed in this execution environment. |
| Full pytest gate | Implemented, not fully executable here | `pytest` runs before PyInstaller unless `--skip-tests` is supplied. The suite intentionally fails collection when Pint is missing; it does not skip Pint tests. |
| PyInstaller onedir default / `--onefile` | Implemented, not smoke-tested here | PyInstaller is not installed and package installation cannot reach PyPI. |
| `--noupx`, `--collect-all pint`, data folders | Implemented | Command construction includes required flags and `examples/`, `models_examples/`, `docs/`. |
| QtSvg collection for iteration 2 | Implemented conditionally | `PySide6.QtSvg` is collected when PySide6 is installed in the build environment. |
| Frozen `--help` smoke test | Implemented, not run here | Runs after PyInstaller and prevents publishing a failed binary. |
| Reproducible ZIP envelope | Implemented / unit-tested | Fixed ZIP timestamp, sorted names, normalized modes and compression level. Byte equality still requires identical payload bytes and Python/zlib toolchain; this does not claim that arbitrary PyInstaller/native binaries are bitwise reproducible across toolchains. |
| Successful clean-machine EXE build | **Blocked** | No Pint or PyInstaller installed; `pip install` failed with `Temporary failure in name resolution`. No binary or Windows smoke-test log can honestly be supplied. |

## Scientific checklist

| ID | Status | Change / current behavior | Regression test | Formula / reference |
|---|---|---|---|---|
| A1* | Fixed and tested | ISA uses `H=hR/(R+h)` for geometric input; `at_geopotential()` makes layer-boundary tests explicit. `T=216.65 K` at geopotential 11 km and 20 km; sea-level density is 1.225 kg/m³ within numerical rounding. | `test_isa_geopotential_tropopause_and_isothermal_layer_exact_values`, `test_isa_geometric_altitude_is_converted_to_geopotential`, `test_isa_reference_sea_level` | U.S. Standard Atmosphere 1976, NASA NTRS Appendix A: <https://ntrs.nasa.gov/citations/20050207438>. **Important:** `at(11_000)` means 11 km geometric and therefore is slightly warmer than 216.65 K; the exact 216.65 K boundary is at 11 km geopotential. |
| A2* | Fixed and tested | Sutherland three-parameter law uses `μ0=1.716e-5 Pa·s`, `T0=273.15 K`, `S=110.4 K`. | `test_sutherland_three_parameter_reference_values` | Sutherland law: <https://doc.comsol.com/6.3/doc/com.comsol.help.cfd/cfd_ug_fluidflow_high_mach.08.43.html>; parameter values also documented in 40 CFR §1065.640 (regulatory table rounds `T0` and `S`): <https://www.law.cornell.edu/cfr/text/40/1065.640>. |
| A3 | Fixed and tested | Exponential atmosphere returns `T(h)=T0-Lh`; viscosity and sound speed are recomputed from that temperature. | `test_exponential_temperature_is_altitude_dependent` | Explicit project model: `ρ(h)=ρ0 exp(-h/H)`, `T(h)=T0-Lh`. |
| A4 | Core verified; Pint boundary blocked | `AtmosphereState.viscosity` and `FlowState.viscosity` are SI dynamic viscosity in Pa·s; schema boundary converts to `Pa*s`. | `test_flow_atmosphere_viscosity_is_dynamic_si_pa_seconds`; Pint-only: `test_dynamic_viscosity_is_converted_to_pa_seconds_at_the_boundary`, `test_dynamic_viscosity_rejects_nonviscosity_dimensions`, `test_dynamic_viscosity_requires_an_explicit_unit` | Sutherland/transport-property references under A2. Pint tests were not executed because Pint could not be installed. |
| B1* | Fixed and tested | Reynolds number is `ρ |u_rel| d / μ` using sphere diameter. | `test_reynolds_number_uses_diameter_not_radius` | Standard spherical-particle Reynolds definition: *The Civil Engineering Handbook*, Eq. 9.136: <https://www.uceb.eu/DATA/Books/THE%20CIVIL%20ENGINEERING%20HANDBOOK.pdf>. |
| B2 | Verified and tested | CGW piecewise branches are joined with a narrow C1 smoothstep blend; tabular interpolation is continuous at data knots. | `test_cgw_join_continuity_at_every_piecewise_boundary`, `test_tabular_model_is_continuous_at_nodes` | CGW Table 5.2 reproduction: <https://pychemqt.readthedocs.io/en/latest/lib.drag.html>, <https://fluids.readthedocs.io/fluids.drag.html>. The smoothstep join is a documented numerical regularization, not a claim that the source table itself specifies blending. |
| B3 | Verified and tested | `describe()['validity']` carries inclusive/exclusive bounds; simulation emits `DragModelApplicabilityWarning` outside them. | `test_applicability_warning_uses_exact_open_and_closed_metadata_bounds`, `test_tabular_metadata_range_matches_data_and_warns_outside` | Applicability intervals are correlation-specific; CGW source under B2 and Schiller–Naumann under B4. |
| B4 | Verified and tested | Default table interpolation is log-log; linear axes remain selectable and are labelled in metadata. | `test_tabular_default_is_log_log_and_preserves_power_law` | User-selected interpolation policy; the log-log interpolant exactly preserves a power law between tabulated points. |
| B5 | Verified and tested | `error` is default; `clamp` and `extrapolate` are explicit alternatives. Out-of-table values still raise an applicability warning. | `test_tabular_linear_and_extrapolation_policies` | Table range is the measured/data-supported interval; extrapolated values remain marked as outside that interval. |
| B6 | Verified with a necessary physical exception | `validate_cd()` defaults to finite `0 < Cd < 100`; third-party Python subclasses cannot relax that ceiling. Exact built-in Stokes/Schiller–Naumann/CGW and tabular models use a finite model-specific overflow guard because valid low-Re `24/Re` values exceed 100. A universal `<100` ceiling would invalidate the requested Stokes model. | `test_cd_validator_default_contract_is_zero_to_100`, `test_python_plugin_cannot_override_strict_cd_ceiling`, `test_stokes_can_exceed_cd_100_in_its_physical_domain` | Stokes `Cd=24/Re` and its physical low-Re limit: *The Civil Engineering Handbook*, Eq. 9.137; <https://www.uceb.eu/DATA/Books/THE%20CIVIL%20ENGINEERING%20HANDBOOK.pdf>. |
| C1* | Verified and tested | RK4 recomputes atmosphere, relative velocity, Reynolds number and Cd within each of k1/k2/k3/k4 RHS evaluations. | `test_rk4_fourth_order_convergence_with_stagewise_atmosphere_and_drag` (halving step gives approximately 16× error reduction) | Classical fourth-order Runge–Kutta; stage-wise evaluation follows the RK4 Butcher tableau. |
| C2 | Verified and tested | DOP853 dense output is rooted with `brentq` on descending `y=0` between reported samples; impact time/state are appended. | `test_dop853_finds_ground_impact_with_brent_root_between_samples` | SciPy `solve_ivp` dense output: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html>; scalar root finder: <https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html>. |
| C3 | Verified and tested | DOP853 accepts scalar or six-component `atol`; vectors are shape- and positivity-validated. | `test_dop853_accepts_componentwise_atol_vector`, `test_dop853_rejects_wrong_atol_vector_shape` | SciPy `solve_ivp` supports array-like absolute tolerances; reference under C2. |
| C4 | Verified and tested | Gravity-only RK4 mechanical energy regression tolerance is `1e-6 J`, avoiding an unjustified `1e-12` requirement. | `test_mechanical_energy_conserved_without_drag` | RK4 truncation error is fourth order; tolerance is regression-specific, not a physical constant. |
| D1 | Verified and tested | Coordinates are `(x,y,z)`, y is vertical positive upward, gravity defaults to `(0,-g,0)`, angle is measured from horizontal in x-y plane. | `test_vacuum_45_degree_range_matches_analytic_formula`, `test_vacuum_reference_matches_analytic_position` | Vacuum range `R=v² sin(2θ)/g`; documented in `docs/physics.md`. |
| D2 | Verified and tested | Terminal speed uses effective mass `m_eff=(ρp-ρf)4πr³/3`, equivalent to `m_eff g/(6πμr)`. | `test_stokes_terminal_velocity_matches_effective_mass_formula` | Stokes terminal settling relation: *The Civil Engineering Handbook*, Eq. 9.138; and pyoomph Stokes-law derivation: <https://pyoomph.readthedocs.io/en/stable/tutorial/spatial/stokes/stokeslaw.html>. |
| D3 | Fixed and tested | Checksum quantizes each trajectory column relative to its maximum magnitude on a `1e-9` grid, serializes a normalized scale, then hashes canonical JSON with SHA-256. | `test_quantized_checksum_is_stable_to_sub_quantum_float_noise`, `test_seed_and_checksum_are_recorded` | Project-defined numerical regression checksum; it is deliberately not a promise of cross-platform bitwise equivalence. |

## Test execution record

- `python -m py_compile ...`: passed for project source, tests and `build.py`.
- `python build.py --help`: passed; expected three optional switches are present.
- `pytest -q --ignore=tests/test_io.py --ignore=tests/test_units.py`: **47 passed**.
- Core coverage with those same Pint-dependent modules excluded: **87.69%** (threshold 80%).
- Full `pytest -q`: **blocked at collection** by `ModuleNotFoundError: No module named 'pint'` in `tests/test_io.py` and `tests/test_units.py`. This is intentional fail-fast behavior, not a skipped test.
- `pip install 'pint>=0.24,<1'` and the builder's `pip install -e ".[build]"`: failed because this environment could not resolve PyPI (`Temporary failure in name resolution`).
- PyInstaller, Ruff and mypy are not installed in this environment. A native frozen executable build and `--help` smoke-test log therefore cannot be truthfully reported.

## Commit log for this audit pass

- `fix(core/drag): enforce strict plugin Cd limits`
- `fix(build): package reproducible distribution archive`
- Previous iteration-1 fixes are retained in Git history, including ISA conversion, diameter-based Re, DOP853 impact localization, y-up coordinates and build metadata handling.
