# DTCHullWave — OpenFOAM 13 Ship Wave Resistance

Simulation of the **DTC (Duisburg Test Case) container ship** advancing through calm water using the `interFoam` solver. The hull undergoes free heave and pitch (2-DOF rigid-body motion). Wave resistance and rigid-body dynamics are computed from a Reynolds-Averaged simulation with a VOF free surface.

---

## Physical Setup

| Parameter | Value |
|---|---|
| Hull | DTC container ship (model scale) |
| Ship speed U | 1.668 m/s |
| Froude number Fr | 0.223 |
| Reynolds number Re | 8.75 × 10⁶ |
| Water density ρ | 998.8 kg/m³ |
| Kinematic viscosity ν | 1.09 × 10⁻⁶ m²/s |
| Incident waves | Stokes 2nd order, λ = 3 m, a = 0.04 m |
| Wave direction | Head seas (into bow) |
| DOF | Free heave + pitch (Euler-implicit rigid-body motion) |

The simulation uses a half-domain with a symmetry plane at y = 0 (port–starboard symmetry).

---

## Mesh

| Parameter | Value |
|---|---|
| Total cells | ~960,000 |
| Base mesh | blockMesh hexahedral background |
| Hull refinement | snappyHexMesh surface + boundary layers |
| Free-surface refinement | Refined band around z ≈ 0 waterline |
| Boundary layers | 3 layers on hull surface |

The mesh was generated with `blockMesh` → `surfaceFeatures` → `snappyHexMesh` → `refineMesh` → `renumberMesh`.

---

## Physics Models

### Free Surface — Volume of Fluid (VOF)

`alpha.water` transports the water volume fraction. MULES compression keeps the interface sharp. Air above and water below are treated as incompressible Newtonian fluids.

### Turbulence

k–ω SST (incompressible) for the water phase.

### Rigid-Body Motion

The hull is free to heave (z) and pitch (rotation about y). The `rigidBodyMotion` dynamic mesh solver moves the hull each time step, and the mesh deforms accordingly. Forces and moments are written to `postProcessing/rigidBodyForces/`.

---

## Solver Setup

| Setting | Value |
|---|---|
| Solver | `interFoam` |
| Time discretisation | Euler implicit |
| Pressure–velocity | PIMPLE (3 outer iterations) |
| Simulated time | 6.54 s (killed; t = 20 s target) |
| Time step | Adaptive (Co < 0.5) |

---

## Results

### Resistance Time History

**Total, pressure, and viscous resistance vs time:**
![Resistance history](resistance_history.png)

| Quantity | Value |
|---|---|
| Mean total resistance (t > 4 s) | **22.0 N** |
| Pressure component | 8.5 N (39%) |
| Viscous component | 13.5 N (61%) |

The solution settles by t ≈ 2–3 s. After that, small oscillations remain due to the Stokes wave field interacting with the hull and causing periodic heave/pitch excitation. The viscous component dominates at this relatively low Froude number (Fr = 0.223), consistent with the sub-critical hull speed where wave-making resistance is modest.

### Convergence

**Solver residuals for p_rgh, α_water, and Ux:**
![Convergence](convergence.png)

### Wave Pattern Evolution

**Free-surface elevation (top-down view) from t = 1–6 s:**
![Wave animation](wave_animation.gif)

The bow wave builds during the first ~2 s as the flow establishes; by t ≈ 3 s the Kelvin wake is stationary. The characteristic diverging and transverse wave system is visible aft of the hull.

### Wave Pattern — Symmetry Plane (y = 0)

**Water volume fraction and pressure at t = 5 s (zoomed around hull):**
![Wave pattern](wave_pattern.png)

**Full-domain wave pattern:**
![Wave pattern full](wave_pattern_full.png)

The free surface (α = 0.5 contour, black line) shows the characteristic bow wave building up ahead of the hull and the Kelvin wake developing downstream. The pressure field reflects the high-pressure stagnation zone at the bow and the low-pressure trough along the hull waterline.

### Hull Surface Pressure

**Pressure distribution on the hull surface (side view, t = 5 s):**
![Hull pressure](hull_pressure.png)

High pressure at the bow stagnation point drives the wave-making resistance; the negative pressure region along the midbody and stern contributes to form drag.

---

## Running the Case

```bash
source /opt/openfoam13/etc/bashrc
cd openfoam-DTCHullWave
./Allmesh               # blockMesh + snappyHexMesh + refineMesh + setWaves
decomposePar
mpirun -np 8 foamRun -parallel > log.foamRun 2>&1 &
reconstructPar
python3 post_process.py
```

---

## References

el Moctar, O., Shigunov, V., & Zorn, T. (2012). Duisburg Test Case: Post-panamax container ship for benchmarking. *Ship Technology Research*, 59(3), 50–64.

OpenFOAM Foundation (2024). *DTCHullWave tutorial*, `$FOAM_TUTORIALS/incompressibleVoF/DTCHullWave`.
