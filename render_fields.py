"""Render CFD field images using pvpython (ParaView offscreen rendering)."""
from paraview.simple import *
import os

CASE = os.path.dirname(os.path.abspath(__file__))
VTK_DIR = f'{CASE}/VTK'
SURF_DIR = f'{CASE}/postProcessing/surfaces'

# ── helpers ───────────────────────────────────────────────────────────────────
def setup_view(w=1400, h=600, bg=(1,1,1)):
    v = GetRenderView()
    v.ViewSize = [w, h]
    v.Background = list(bg)
    v.OrientationAxesVisibility = 0
    return v

def save(path, v=None):
    if v is None:
        v = GetRenderView()
    SaveScreenshot(path, v, ImageResolution=v.ViewSize)
    print(f'saved: {path}')

# ── 1. Midplane: alpha.water ──────────────────────────────────────────────────
mid = LegacyVTKReader(FileNames=[f'{VTK_DIR}/midPlane/midPlane_2518.vtk'])
midDisp = Show(mid)
ColorBy(midDisp, ('POINTS', 'alpha.water'))

lut = GetColorTransferFunction('alpha.water')
lut.ApplyPreset('Cool to Warm', True)
lut.RescaleTransferFunction(0.0, 1.0)

cb = GetScalarBar(lut, GetRenderView())
cb.Title = 'alpha water'
cb.ComponentTitle = ''
cb.Visibility = 1

v = setup_view(1400, 500)
v.CameraPosition    = [0, -60, 0]
v.CameraFocalPoint  = [0, 0, 0]
v.CameraViewUp      = [0, 0, 1]
v.CameraParallelProjection = 1
v.CameraParallelScale = 4.5
ResetCamera()
# zoom to region of interest
v.CameraParallelScale = 3.0
v.CameraFocalPoint = [2.0, 0.0, 0.2]

Render()
save(f'{CASE}/wave_pattern_midplane.png')
Delete(mid); del mid

# ── 2. Hull surface: pressure ─────────────────────────────────────────────────
hull = LegacyVTKReader(FileNames=[f'{VTK_DIR}/hull/hull_2518.vtk'])
hullDisp = Show(hull)
ColorBy(hullDisp, ('POINTS', 'p'))

lut2 = GetColorTransferFunction('p')
lut2.ApplyPreset('Cool to Warm', True)
lut2.RescaleTransferFunction(-50, 2600)

cb2 = GetScalarBar(lut2, GetRenderView())
cb2.Title = 'p [Pa]'
cb2.ComponentTitle = ''
cb2.Visibility = 1

v2 = setup_view(1200, 500)
# Side view: look along -y axis at the hull
v2.CameraPosition   = [3.0, -5.0, 0.25]
v2.CameraFocalPoint = [3.0,  0.0, 0.25]
v2.CameraViewUp     = [0, 0, 1]
v2.CameraParallelProjection = 1
v2.CameraParallelScale = 0.45
Render()
save(f'{CASE}/hull_pressure.png')
Delete(hull); del hull

# ── 3. GIF frames: interface free surface coloured by elevation ───────────────
from PIL import Image

gif_times = [1, 2, 3, 4, 5, 6]
frames = []

for t in gif_times:
    path = f'{SURF_DIR}/{t}/interface.vtk'
    src = LegacyVTKReader(FileNames=[path])
    disp = Show(src)

    # colour by z-elevation
    ColorBy(disp, ('POINTS', 'p_rgh'))
    lut3 = GetColorTransferFunction('p_rgh')
    lut3.ApplyPreset('Cool to Warm', True)
    lut3.RescaleTransferFunction(-500, 3000)

    cb3 = GetScalarBar(lut3, GetRenderView())
    cb3.Title = 'p_rgh [Pa]'
    cb3.ComponentTitle = ''
    cb3.Visibility = 1

    v3 = setup_view(1300, 550, bg=(1,1,1))
    # top-down view
    v3.CameraPosition   = [3.0, 0.0, 30.0]
    v3.CameraFocalPoint = [3.0, 0.0,  0.0]
    v3.CameraViewUp     = [-1, 0, 0]
    v3.CameraParallelProjection = 1
    v3.CameraParallelScale = 3.5

    # Add text annotation for time
    txt = Text()
    txt.Text = f't = {t} s    U = 1.668 m/s    Fr = 0.223'
    txtDisp = Show(txt)
    txtDisp.FontSize = 18
    txtDisp.Color = [0, 0, 0]
    txtDisp.WindowLocation = 'Upper Center'

    Render()
    tmp = f'{CASE}/_frame_{t}.png'
    save(tmp, v3)
    frames.append(Image.open(tmp))

    Delete(txt); Delete(src)

out = f'{CASE}/wave_animation.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=700, loop=0)
print(f'wave_animation.gif saved ({len(frames)} frames)')

# clean temp frames
import glob
for f in glob.glob(f'{CASE}/_frame_*.png'):
    os.remove(f)
