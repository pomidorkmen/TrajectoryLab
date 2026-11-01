# Physical models, equations and assumptions

## Scope and geometry

TrajectoryLab iteration 1 models translational motion of one rigid sphere in a
continuum fluid. It is intended for low-speed laboratory and sports-object
experiments and software verification. It is not a general-purpose solver for
arbitrary body shapes, rarefied gas, or high-speed compressible flow.

The local Cartesian frame is `(x, y, z)`: `x` and `z` are horizontal, and `y`
is vertical and positive upward. The state is
`(x, y, z, vx, vy, vz)`. Gravity points in the negative `y` direction by
default: `g = (0, -9.80665, 0) m/s^2`. An angle measured from the horizontal
plane is represented in the `x-y` plane by
`vx = v*cos(theta)` and `vy = v*sin(theta)`; positive `theta` means launch
upward. The default ground plane is `y=0`.

For a sphere of diameter `d`, mass `m`, frontal area `A = pi*d^2/4` and
volume `V = pi*d^3/6`, the equation of motion with buoyancy and drag is

`m * dv/dt = m*g - rho*V*g - 0.5*rho*Cd*A*|u_rel|*u_rel`,

where `u_rel = v - v_air`. Buoyancy is included when a drag model is active.
With drag disabled, the solver is a gravity-only reference and buoyancy is
also disabled. The kinetic-energy column is ground-frame translational energy,
`0.5*m*|v|^2`.

For vacuum motion launched and landing at the same height,
`R = v^2*sin(2*theta)/g0` and `t_flight = 2*v*sin(theta)/g0`, where `g0`
is the positive magnitude of gravitational acceleration.

## Atmosphere models

Every atmosphere returns `(rho, T, mu, a)` in SI units:

- Constant: constant density and temperature. Dynamic viscosity is either a
  user-specified constant or Sutherland viscosity at the selected temperature.
- Exponential: `rho(h)=rho0*exp(-h/H)` and a configurable temperature lapse
  `T(h)=T0-L*h`. Density and temperature are independent experimental laws;
  this is not a hydrostatically self-consistent multilayer atmosphere.
- ISA: dry-air troposphere to 11 km geopotential altitude, then an isothermal
  lower-stratosphere layer to 20 km geopotential altitude.

The ISA public `at(h)` input is **geometric altitude**. It is converted to
geopotential altitude before evaluating standard-atmosphere layers:

`H = h*R/(R+h)`, with `R = 6,356,766 m`.

Therefore `T=216.65 K` is the exact ISA layer-boundary value at
`H=11,000 m` geopotential altitude (or at the corresponding geometric height
`h = 11,019.0678... m`). Calling `at(11,000 m)` means 11 km geometric altitude
and consequently gives a temperature slightly above 216.65 K. The explicit
`at_geopotential()` method is provided for reference-table heights already
expressed in geopotential metres. Sea-level reference density is 1.225 kg/m^3
within normal ISA rounding.

Dynamic viscosity is **dynamic** viscosity `mu` in Pa*s throughout the core.
ISA, exponential atmosphere and the default constant-atmosphere viscosity use
the three-parameter Sutherland law:

`mu(T) = mu0*(T/T0)^(3/2)*(T0+S)/(T+S)`,

with `mu0=1.716e-5 Pa*s`, `T0=273.15 K`, and `S=110.4 K`. The speed of sound
uses `a=sqrt(gamma*R_air*T)` for dry air with `gamma=1.4` and
`R_air=287.05287 J/(kg*K)`.

## Reynolds and Mach numbers

The particle Reynolds number uses the **sphere diameter**, not its radius:

`Re = rho*|u_rel|*d/mu`.

Here `rho` is kg/m^3, `|u_rel|` is m/s, `d` is m, and `mu` is Pa*s. Mach is
reported as `|u_rel|/a`; in the current low-speed scope it is diagnostic only,
not a compressibility correction.

## Drag correlations

All built-in correlations in this iteration are reference models for a rigid
sphere using the sphere frontal area. Validity intervals are recorded in
model metadata, including open/closed endpoints. A simulation emits a Python
warning when the current Reynolds number leaves the stated interval; it does
not silently clamp the correlation.

- Stokes: `Cd=24/Re`, for `0 < Re < 1` (creeping-flow limit).
- Schiller--Naumann: `Cd=(24/Re)*(1+0.15*Re^0.687)`, for `0 < Re < 800`.
- Clift--Grace--Weber: piecewise smooth-sphere standard curve to `Re=3e5`.
  The source branch formulae are joined with a narrow C1 smoothstep blend over
  +/-0.5% around rounded table breakpoints to remove discontinuities introduced
  by rounded coefficients. The blending policy is part of the model metadata.
- Constant Cd: user-specified dimensionless coefficient, for controlled
  comparisons; the user must document the physical range for their specimen.
- Tabular: user-supplied `Cd(Re)`. Default interpolation is log-log: linear
  interpolation in `log(Re)` versus `log(Cd)`. Optional modes are linear axes
  and shape-preserving cubic PCHIP in log-log space. Out-of-range behavior is
  explicit: `clamp`, `extrapolate`, or `error`; the default is `error`.

The Stokes asymptote makes `Cd=24/Re` larger than 100 at sufficiently small
Re. Consequently Python plugin/custom-subclass output is strictly validated
with `0 < Cd < 100`; overriding a model attribute cannot relax this plugin
contract. Exact first-party low-Re correlations and tabular reference models
use a larger finite numerical guard because imposing the plugin ceiling on
Stokes would reject mathematically valid creeping-flow values and contradict
the stated correlation.

## Terminal settling speed

For a sphere settling under gravity in a quiescent fluid in the Stokes regime,
the buoyancy-corrected effective mass is
`m_eff = (rho_p-rho_f)*(4*pi*r^3/3)`. Balancing effective weight with
Stokes drag gives

`v_t = m_eff*g/(6*pi*mu*r)`.

This form makes the meaning of `m` explicit: it is the particle mass minus
the displaced-fluid mass, not bare particle mass. The equivalent density form
is `v_t = 2*(rho_p-rho_f)*g*r^2/(9*mu)`.

## Simulation time and terminal events

`duration_s` is the **maximum simulation time**, not a mandatory duration when
an event stop is enabled. With `stop_at_ground=True`, the run terminates at the
first descending crossing of the local ground plane `y=0`; with the option
disabled, it continues to the configured maximum time, even if the abstract
trajectory goes below the ground plane. This latter mode is useful for numerical
experiments and must not be interpreted as a physical model of soil or obstacle
penetration.

Both RK4 and DOP853 apply the same event direction (descending only) and return
a localized event state rather than rounding the impact to the next stored
sample. If the maximum time is not divisible by the requested output step, a
short final interval is used. The output step is the actual fixed integration
step for RK4; for DOP853 it defines the requested output grid while the solver
chooses internal adaptive steps using `rtol` and `atol`.

The apogee is interpolated within each stored interval from position and
vertical velocity using cubic Hermite segments. For constant acceleration the
interpolant reproduces the analytic apex even when it falls between saved
samples. For variable acceleration it is a local dense-output approximation;
refine the step or tolerances when the exact peak is scientifically important.

## Numerical methods and reproducibility

- RK4 uses a fixed output step, with a shorter final step when needed. The
  right-hand side re-evaluates local atmosphere and drag coefficient at all
  four RK stages.
- DOP853 uses SciPy's adaptive DOP853 method and supports scalar or
  component-wise absolute tolerances. Ground impact is located between output
  samples using dense solution output and Brent's root finder on the vertical ground-plane event `y(t)=0`.
- The checksum first normalizes each trajectory column by its maximum absolute
  value, quantizes normalized values on a relative 1e-9 grid, and serializes
  the scale to 10 significant digits before SHA-256. It is a tolerant
  regression checksum, not a promise of bitwise identity across Python,
  NumPy, SciPy, CPU, or OS builds.
- JSON exports include Python, NumPy, SciPy, Pint and TrajectoryLab versions,
  OS description, integrator settings, model metadata and seed.

## Explicit limitations

The current solver has no orientation state. Its drag equations assume a rigid
sphere with a diameter and frontal area. A non-spherical body (for example, a
feather, plate or irregular fragment) is outside the model's applicability
unless a validated shape/orientation model is added.

The solver does not model rarefaction, slip flow, non-Newtonian fluids,
humidity effects, heat transfer, particle deformation, rotation, lift, added
mass, Basset history force, wall effects, particle-particle interactions,
turbulence fluctuations, or variable gravity / Earth curvature. The ISA
implementation is dry-air and only covers the documented lower-atmosphere
layers. Wind is a constant vector in iteration 1.

## Reference sources

1. U.S. Standard Atmosphere geopotential-height relation and lower-atmosphere
   layer constants: NOAA/NASA standard-atmosphere references; the conversion
   uses `H=h*R/(R+h)` with `R=6,356,766 m`.
2. Sutherland viscosity law: Sutherland (1893), and standard dry-air transport
   property implementations using `mu0=1.716e-5 Pa*s`, `T0=273.15 K`,
   `S=110.4 K`.
3. Schiller, L. & Naumann, A. (1933), drag coefficient correlation for
   spherical particles.
4. Clift, R., Grace, J. R. & Weber, M. E. (1978), *Bubbles, Drops, and
   Particles*, Academic Press, standard sphere drag curve.
5. Stokes creeping-flow solution for drag on a sphere (1851); terminal speed
   follows by balancing effective weight and Stokes drag.
6. NASA Glenn Research Center, "Drag of a Sphere",
   https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-of-a-sphere/.
