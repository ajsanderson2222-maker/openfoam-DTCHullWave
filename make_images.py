"""Generate wave pattern and hull pressure images from VTK output."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as tri
from matplotlib.tri import TriAnalyzer
import vtk
import os

CASE = os.path.dirname(os.path.abspath(__file__))
VTK_DIR = f'{CASE}/VTK'

def read_polydata(path):
    r = vtk.vtkPolyDataReader()
    r.SetFileName(path)
    r.ReadAllScalarsOn()
    r.ReadAllVectorsOn()
    r.Update()
    return r.GetOutput()

def get_points(d):
    pts = d.GetPoints()
    n = pts.GetNumberOfPoints()
    return np.array([pts.GetPoint(i) for i in range(n)])

def get_point_array(d, name):
    arr = d.GetPointData().GetArray(name)
    if arr is None:
        return None
    return np.array([arr.GetValue(i) for i in range(arr.GetNumberOfTuples())])

def make_triang(x, y, max_area_ratio=3.0):
    """Build a clean 2-D Delaunay triangulation and mask oversized triangles.

    Using scipy Delaunay on the projected 2-D points avoids the artefacts
    from VTK 3-D connectivity projected onto a plane (long-range spurious
    triangles that create white holes everywhere).  Oversized triangles that
    fill concave gaps are then masked by area threshold.
    """
    from scipy.spatial import Delaunay
    pts2d = np.column_stack([x, y])
    d = Delaunay(pts2d)
    triang = tri.Triangulation(x, y, d.simplices)
    # mask triangles much larger than the median (concave-hull gap-fillers)
    t = d.simplices
    ax, ay = x[t[:,1]]-x[t[:,0]], y[t[:,1]]-y[t[:,0]]
    bx, by = x[t[:,2]]-x[t[:,0]], y[t[:,2]]-y[t[:,0]]
    areas = 0.5 * np.abs(ax*by - ay*bx)
    threshold = max_area_ratio * np.median(areas)
    triang.set_mask(areas > threshold)
    return triang

def get_connectivity(d):
    """Return (ntri, 3) int array of triangulated cell connectivity."""
    tris = []
    for i in range(d.GetNumberOfCells()):
        cell = d.GetCell(i)
        ct = cell.GetCellType()
        ids = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]
        if ct == 5:   # VTK_TRIANGLE
            tris.append(ids)
        elif ct == 9:  # VTK_QUAD → split into 2 triangles
            tris.append([ids[0], ids[1], ids[2]])
            tris.append([ids[0], ids[2], ids[3]])
    return np.array(tris, dtype=int)

# ── Mid-plane: wave pattern (alpha.water) ─────────────────────────────────────
mid = read_polydata(f'{VTK_DIR}/midPlane/midPlane_2518.vtk')
pts_m = get_points(mid)
x_m = pts_m[:, 0]
z_m = pts_m[:, 2]
alpha_m = get_point_array(mid, 'alpha.water')
p_m     = get_point_array(mid, 'p')
tris_m  = get_connectivity(mid)

triang_m = make_triang(x_m, z_m)

fig, axes = plt.subplots(2, 1, figsize=(14, 8))
fig.suptitle('DTC Hull — symmetry plane (y = 0) at t = 5 s', fontsize=13)

# Alpha: free surface position
ax = axes[0]
im = ax.tricontourf(triang_m, alpha_m, levels=50, cmap='RdBu_r', vmin=0, vmax=1)
ax.tricontour(triang_m, alpha_m, levels=[0.5], colors='k', linewidths=1.2)
plt.colorbar(im, ax=ax, label='α_water')
ax.set_xlim(-8, 8)    # zoom around hull
ax.set_ylim(-1.5, 1.5)
ax.set_xlabel('x [m]  (−x = upstream)')
ax.set_ylabel('z [m]')
ax.set_title('Water volume fraction α  (contour line at α = 0.5 marks free surface)')
ax.set_aspect('equal')
ax.axvline(0, color='gray', lw=0.5, ls='--', alpha=0.5)
ax.axvline(6.16, color='gray', lw=0.5, ls='--', alpha=0.5)
ax.text(3.1, 1.3, 'hull extent', ha='center', fontsize=8, color='gray')

# Pressure on mid-plane (near-surface cells only: alpha between 0.1 and 0.9)
ax2 = axes[1]
# Show full domain pressure (dynamic pressure relative to hydrostatic)
im2 = ax2.tricontourf(triang_m, p_m, levels=50, cmap='coolwarm')
plt.colorbar(im2, ax=ax2, label='p [Pa]')
ax2.tricontour(triang_m, alpha_m, levels=[0.5], colors='k', linewidths=1.2, linestyles='--')
ax2.set_xlim(-8, 8)
ax2.set_ylim(-1.5, 1.5)
ax2.set_xlabel('x [m]')
ax2.set_ylabel('z [m]')
ax2.set_title('Pressure p  (dashed line = free surface α = 0.5)')
ax2.set_aspect('equal')

plt.tight_layout()
plt.savefig(f'{CASE}/wave_pattern.png', dpi=150)
plt.close()
print('wave_pattern.png saved')

# ── Wide-view wave pattern (full domain) ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 5))
im = ax.tricontourf(triang_m, alpha_m, levels=50, cmap='RdBu_r', vmin=0, vmax=1)
ax.tricontour(triang_m, alpha_m, levels=[0.5], colors='k', linewidths=0.8)
plt.colorbar(im, ax=ax, label='α_water')
ax.set_xlim(x_m.min(), x_m.max())
ax.set_ylim(-3, 2)
ax.set_xlabel('x [m]  (−x = upstream,  0 = bow)')
ax.set_ylabel('z [m]')
ax.set_title('DTC Hull — wave pattern across full domain (symmetry plane, t = 5 s)')
plt.tight_layout()
plt.savefig(f'{CASE}/wave_pattern_full.png', dpi=150)
plt.close()
print('wave_pattern_full.png saved')

# ── Hull surface: pressure distribution ───────────────────────────────────────
hull = read_polydata(f'{VTK_DIR}/hull/hull_2518.vtk')
pts_h = get_points(hull)
x_h = pts_h[:, 0]
y_h = pts_h[:, 1]
z_h = pts_h[:, 2]
p_h = get_point_array(hull, 'p')
tris_h = get_connectivity(hull)

# Side view: project onto x-z plane (port side, y < 0 dominant)
triang_h = make_triang(x_h, z_h)

fig, ax = plt.subplots(figsize=(12, 4))
im = ax.tricontourf(triang_h, p_h, levels=60, cmap='coolwarm')
plt.colorbar(im, ax=ax, label='p [Pa]')
ax.set_xlabel('x [m]  (0 = bow, 6.16 = stern)')
ax.set_ylabel('z [m]')
ax.set_title('DTC Hull surface — pressure distribution (side view, t = 5 s)')
ax.set_aspect('equal')
plt.tight_layout()
plt.savefig(f'{CASE}/hull_pressure.png', dpi=150)
plt.close()
print('hull_pressure.png saved')
