import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import re, os

CASE = os.path.dirname(os.path.abspath(__file__))

# ── Ship / case parameters ────────────────────────────────────────────────────
U_ship  = 1.668        # m/s (from setWavesDict UxMean)
rho     = 998.8        # kg/m³ (physicalProperties.water)
nu      = 1.09e-6      # m²/s
L_pp    = 5.720        # DTC hull Lpp [m] (model scale 1:1 from tutorial)
# Froude number Fr = U / sqrt(g*L)
g       = 9.81
Fr      = U_ship / np.sqrt(g * L_pp)
Re      = U_ship * L_pp / nu

# ── Parse rigid-body forces ───────────────────────────────────────────────────
forces_file = f'{CASE}/postProcessing/rigidBodyForces/0/rigidBodyForces.dat'

times, Fx_pres, Fx_visc = [], [], []
# All floats per line (scientific notation):
#   [0-2] CofR, [3-5] pressure F(x,y,z), [6-8] viscous F(x,y,z), [9-11] pressure M, [12-14] viscous M
float_re = re.compile(r'[-+]?\d+\.\d+e[+-]\d+')

with open(forces_file) as f:
    for line in f:
        if line.startswith('#') or not line.strip():
            continue
        floats = float_re.findall(line)
        if len(floats) < 9:
            continue
        t = float(line.split()[0])
        times.append(t)
        Fx_pres.append(float(floats[3]))   # pressure Fx
        Fx_visc.append(float(floats[6]))   # viscous Fx

times   = np.array(times)
Fx_pres = np.array(Fx_pres)
Fx_visc = np.array(Fx_visc)
Fx_total = Fx_pres + Fx_visc          # drag (negative = resistance in -x direction)
resistance = -Fx_total                 # positive resistance force [N]

# Smooth: drop the first 0.1 s of startup transient
mask = times > 0.1
t_plot = times[mask]
R_plot = resistance[mask]
Rp_plot = -Fx_pres[mask]
Rv_plot = -Fx_visc[mask]

# Mean over t > 4 s (settled)
mask_mean = times > 4.0
R_mean = resistance[mask_mean].mean() if mask_mean.any() else np.nan
Rp_mean = (-Fx_pres[mask_mean]).mean() if mask_mean.any() else np.nan
Rv_mean = (-Fx_visc[mask_mean]).mean() if mask_mean.any() else np.nan

# ── Resistance time history ───────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(t_plot, R_plot,  'k-',  lw=1.2, label='Total resistance')
ax.plot(t_plot, Rp_plot, 'b--', lw=0.9, label='Pressure component')
ax.plot(t_plot, Rv_plot, 'r:',  lw=0.9, label='Viscous component')
if not np.isnan(R_mean):
    ax.axhline(R_mean,  color='k', lw=1.2, ls='--', alpha=0.5, label=f'Mean (t>4s): {R_mean:.1f} N')
ax.axvspan(0.1, 1.5, color='gray', alpha=0.08, label='Startup transient')
ax.set_xlabel('Simulation time [s]')
ax.set_ylabel('Resistance force [N]')
ax.set_title(f'DTC Hull Wave Resistance  |  U = {U_ship} m/s,  Fr = {Fr:.3f},  Re = {Re:.2e}')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CASE}/resistance_history.png', dpi=150)
plt.close()
print(f'resistance_history.png saved  (mean R = {R_mean:.1f} N, pressure {Rp_mean:.1f} N, viscous {Rv_mean:.1f} N)')

# ── Wave pattern note ─────────────────────────────────────────────────────────
# Field files are binary format; wave pattern contour requires ParaView or
# foamToVTK conversion. The interface.vtk surface is available at:
# postProcessing/surfaces/5/interface.vtk
print('Wave pattern: fields are binary — use ParaView to visualise interface.vtk')

# ── Convergence ───────────────────────────────────────────────────────────────
log_path = f'{CASE}/log.foamRun'
res = {'p_rgh': [], 'alpha.water': [], 'Ux': []}
with open(log_path) as f:
    for line in f:
        if 'Solving for p_rgh,' in line:
            m = re.search(r'Final residual = ([\d.eE+\-]+)', line)
            if m: res['p_rgh'].append(float(m.group(1)))
        if 'Solving for alpha.water,' in line:
            m = re.search(r'Final residual = ([\d.eE+\-]+)', line)
            if m: res['alpha.water'].append(float(m.group(1)))
        if 'Solving for Ux,' in line:
            m = re.search(r'Final residual = ([\d.eE+\-]+)', line)
            if m: res['Ux'].append(float(m.group(1)))

fig, ax = plt.subplots(figsize=(9, 4))
labels = {'p_rgh': 'p_rgh', 'alpha.water': 'α_water', 'Ux': 'Ux'}
t_end = times[-1] if len(times) else 6.54
for key, label in labels.items():
    arr = res[key]
    if arr:
        xi = np.linspace(0, t_end, len(arr))
        ax.semilogy(xi, arr, label=label, lw=0.8)
ax.set_xlabel('Simulation time [s]')
ax.set_ylabel('Final residual')
ax.set_title('Solver residuals — DTCHullWave')
ax.legend(); ax.grid(True, which='both', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CASE}/convergence.png', dpi=150)
plt.close()
print('convergence.png saved')
print(f'\nKey results:')
print(f'  Fr = {Fr:.3f},  Re = {Re:.2e}')
print(f'  Mean total resistance (t>4s): {R_mean:.1f} N')
print(f'  Pressure: {Rp_mean:.1f} N  |  Viscous: {Rv_mean:.1f} N')
