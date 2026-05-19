"""Generate GIF of the free-surface wave pattern evolution (t = 0–6 s)."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as tri
import matplotlib.cm as cm
import vtk, os
from PIL import Image

CASE = os.path.dirname(os.path.abspath(__file__))
SURF = f'{CASE}/postProcessing/surfaces'

# One frame per integer second (t=0 has geometry but may be flat)
times = [1, 2, 3, 4, 5, 6]

def read_interface(t):
    path = f'{SURF}/{t}/interface.vtk'
    r = vtk.vtkPolyDataReader()
    r.SetFileName(path)
    r.ReadAllScalarsOn()
    r.Update()
    d = r.GetOutput()
    pts = np.array([d.GetPoints().GetPoint(i) for i in range(d.GetNumberOfPoints())])
    arr = d.GetPointData().GetArray('p_rgh')
    p   = np.array([arr.GetValue(i) for i in range(arr.GetNumberOfTuples())]) if arr else None
    # triangulate cells
    tris = []
    for i in range(d.GetNumberOfCells()):
        cell = d.GetCell(i)
        ids  = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]
        ct   = cell.GetCellType()
        if ct == 5:
            tris.append(ids)
        elif ct == 9:
            tris.append([ids[0], ids[1], ids[2]])
            tris.append([ids[0], ids[2], ids[3]])
    return pts, np.array(tris, dtype=int), p

# Determine shared colour limits from all frames
print('Reading frames...')
all_p = []
frames_data = []
for t in times:
    pts, tris, p = read_interface(t)
    frames_data.append((t, pts, tris, p))
    if p is not None:
        all_p.append(p)

p_all = np.concatenate(all_p)
p_min, p_max = np.percentile(p_all, 2), np.percentile(p_all, 98)

# Hull outline for reference (from hull VTK at t=5)
import vtk as _vtk
_r = _vtk.vtkPolyDataReader()
_r.SetFileName(f'{CASE}/VTK/hull/hull_2518.vtk')
_r.Update()
_d = _r.GetOutput()
hull_pts = np.array([_d.GetPoints().GetPoint(i) for i in range(_d.GetNumberOfPoints())])
hull_x = hull_pts[:, 0]
hull_y = hull_pts[:, 1]

frames = []
for t, pts, tris, p in frames_data:
    x = pts[:, 0]
    y = pts[:, 1]   # spanwise (0 at symmetry, positive to starboard)
    z = pts[:, 2]   # vertical

    fig, ax = plt.subplots(figsize=(13, 5.5))

    # Top-down view: x (bow→stern) vs y (spanwise), coloured by wave elevation z
    triang = tri.Triangulation(x, y, tris)
    im = ax.tricontourf(triang, z, levels=50, cmap='RdBu_r',
                        vmin=np.percentile(z, 2), vmax=np.percentile(z, 98))
    plt.colorbar(im, ax=ax, label='Free-surface elevation z [m]', shrink=0.85)

    # Hull footprint (waterplane outline) — project hull onto x-y
    ax.scatter(hull_x, hull_y, s=0.3, c='k', alpha=0.15, rasterized=True)

    ax.set_xlim(-5, 8)
    ax.set_ylim(-2, 0.1)
    ax.set_xlabel('x [m]  (0 = bow,  positive → stern)')
    ax.set_ylabel('y [m]  (0 = centreline)')
    ax.set_title(f'DTC Hull — free-surface wave pattern  |  t = {t} s  '
                 f'(U = 1.668 m/s, Fr = 0.223)')
    ax.set_aspect('equal')
    ax.invert_yaxis()   # port on top (conventional ship view)
    ax.annotate('BOW', xy=(0, 0), xytext=(0.5, 0.05), textcoords='axes fraction',
                ha='center', fontsize=9, color='navy',
                arrowprops=dict(arrowstyle='->', color='navy'))

    plt.tight_layout()
    fig.canvas.draw()
    buf = np.frombuffer(fig.canvas.buffer_rgba(), dtype=np.uint8)
    buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (4,))[:, :, :3]
    frames.append(Image.fromarray(buf))
    plt.close()
    print(f'  frame t={t}s done')

out = f'{CASE}/wave_animation.gif'
frames[0].save(out, save_all=True, append_images=frames[1:],
               duration=700, loop=0)
print(f'wave_animation.gif saved  ({len(frames)} frames)')
