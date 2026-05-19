"""Generate resistance history and convergence plots from log/postProcessing data."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import re, os

CASE = os.path.dirname(os.path.abspath(__file__))

U_ship = 1.668
rho    = 998.8
nu     = 1.09e-6
L_pp   = 5.720
g      = 9.81
Fr     = U_ship / np.sqrt(g * L_pp)
Re     = U_ship * L_pp / nu

# ── Parse rigid-body forces ───────────────────────────────────────────────────
forces_file = f'{CASE}/postProcessing/rigidBodyForces/0/rigidBodyForces.dat'
float_re = re.compile(r'[-+]?\d+\.\d+e[+-]\d+')

times, Fx_pres, Fx_visc = [], [], []
Fz_pres, Fz_visc       = [], []
My_pres, My_visc        = [], []
with open(forces_file) as f:
    for line in f:
        if line.startswith('#') or not line.strip():
            continue
        floats = float_re.findall(line)
        if len(floats) < 14:
            continue
        times.append(float(line.split()[0]))
        Fx_pres.append(float(floats[3]))   # pressure drag
        Fx_visc.append(float(floats[6]))   # viscous drag
        Fz_pres.append(float(floats[5]))   # pressure vertical force
        Fz_visc.append(float(floats[8]))   # viscous vertical force
        My_pres.append(float(floats[10]))  # pressure pitch moment
        My_visc.append(float(floats[13]))  # viscous pitch moment

times      = np.array(times)
Fx_pres    = np.array(Fx_pres);  Fx_visc = np.array(Fx_visc)
Fz_pres    = np.array(Fz_pres);  Fz_visc = np.array(Fz_visc)
My_pres    = np.array(My_pres);  My_visc = np.array(My_visc)

resistance = -(Fx_pres + Fx_visc)          # positive = drag
Rp = -Fx_pres;  Rv = -Fx_visc
Fz = Fz_pres + Fz_visc                     # net vertical (heave) force
My = My_pres + My_visc                     # net pitch moment

mask      = times > 0.1
mask_mean = times > 4.0
R_mean  = resistance[mask_mean].mean() if mask_mean.any() else float('nan')
Rp_mean = Rp[mask_mean].mean()         if mask_mean.any() else float('nan')
Rv_mean = Rv[mask_mean].mean()         if mask_mean.any() else float('nan')

# ── Resistance time history ───────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.plot(times[mask], resistance[mask], 'k-',  lw=1.2, label='Total resistance')
ax.plot(times[mask], Rp[mask],         'b--', lw=0.9, label='Pressure component')
ax.plot(times[mask], Rv[mask],         'r:',  lw=0.9, label='Viscous component')
if not np.isnan(R_mean):
    ax.axhline(R_mean, color='k', lw=1.2, ls='--', alpha=0.5,
               label=f'Mean (t > 4 s): {R_mean:.1f} N')
ax.axvspan(0.1, 1.5, color='gray', alpha=0.08, label='Startup transient')
ax.set_xlabel('Simulation time [s]')
ax.set_ylabel('Resistance force [N]')
ax.set_title(f'DTC Hull — wave resistance  |  U = {U_ship} m/s,  Fr = {Fr:.3f},  Re = {Re:.2e}')
ax.legend(fontsize=9)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CASE}/resistance_history.png', dpi=150)
plt.close()
print(f'resistance_history.png  (mean R = {R_mean:.1f} N, pressure {Rp_mean:.1f} N, viscous {Rv_mean:.1f} N)')

# ── Ship loads vs time ───────────────────────────────────────────────────────
fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
fig.suptitle(f'DTC Hull — ship loads vs time  |  Fr = {Fr:.3f},  Re = {Re:.2e}', fontsize=13)

# Resistance (Fx)
ax = axes[0]
ax.plot(times[mask], resistance[mask], 'k-',  lw=1.2, label='Total')
ax.plot(times[mask], Rp[mask],         'b--', lw=0.9, label='Pressure')
ax.plot(times[mask], Rv[mask],         'r:',  lw=0.9, label='Viscous')
ax.axhline(R_mean, color='k', lw=1, ls='-.', alpha=0.5, label=f'Mean {R_mean:.1f} N')
ax.set_ylabel('Resistance Fx [N]')
ax.legend(fontsize=8, ncol=4)
ax.grid(alpha=0.3)

# Vertical force (Fz) — net hydrodynamic lift/sink
ax = axes[1]
Fz_plot = Fz[mask]
ax.plot(times[mask], Fz_plot, 'g-', lw=1.2, label='Net vertical force Fz')
ax.axhline(Fz[mask_mean].mean(), color='g', lw=1, ls='-.', alpha=0.5,
           label=f'Mean {Fz[mask_mean].mean():.1f} N')
ax.set_ylabel('Vertical force Fz [N]')
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3)

# Pitch moment (My)
ax = axes[2]
ax.plot(times[mask], My[mask], 'm-', lw=1.2, label='Net pitch moment My')
ax.axhline(My[mask_mean].mean(), color='m', lw=1, ls='-.', alpha=0.5,
           label=f'Mean {My[mask_mean].mean():.1f} N·m')
ax.set_ylabel('Pitch moment My [N·m]')
ax.set_xlabel('Simulation time [s]')
ax.legend(fontsize=8, ncol=2)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(f'{CASE}/ship_loads.png', dpi=150)
plt.close()
print('ship_loads.png')

# ── Convergence ───────────────────────────────────────────────────────────────
log_path = f'{CASE}/log.foamRun'
res = {'p_rgh': [], 'alpha.water': [], 'Ux': []}
with open(log_path) as f:
    for line in f:
        for key in ('p_rgh', 'alpha.water', 'Ux'):
            if f'Solving for {key},' in line:
                m = re.search(r'Final residual = ([\d.eE+\-]+)', line)
                if m:
                    res[key].append(float(m.group(1)))

t_end = times[-1] if len(times) else 6.54
fig, ax = plt.subplots(figsize=(9, 4))
labels = {'p_rgh': 'p_rgh', 'alpha.water': 'α_water', 'Ux': 'Ux'}
for key, label in labels.items():
    arr = res[key]
    if arr:
        ax.semilogy(np.linspace(0, t_end, len(arr)), arr, label=label, lw=0.8)
ax.set_xlabel('Simulation time [s]')
ax.set_ylabel('Final residual')
ax.set_title('Solver residuals — DTCHullWave')
ax.legend()
ax.grid(True, which='both', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{CASE}/convergence.png', dpi=150)
plt.close()
print('convergence.png')

print(f'\nFr = {Fr:.3f}  Re = {Re:.2e}')
print(f'Mean total resistance (t > 4 s): {R_mean:.1f} N')
print(f'  Pressure {Rp_mean:.1f} N  |  Viscous {Rv_mean:.1f} N')
