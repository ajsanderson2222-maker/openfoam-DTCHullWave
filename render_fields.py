"""Render CFD field images using pvpython (ParaView offscreen rendering)."""
from paraview.simple import *
from PIL import Image
import glob, os

CASE    = os.path.dirname(os.path.abspath(__file__))
VTK_DIR = f'{CASE}/VTK'
SURF    = f'{CASE}/postProcessing/surfaces'

# Shared camera: side view looking along -y, showing x–z plane
# Matches the midplane image perspective so the GIF is consistent.
CAM_POS    = [0.0, -60.0, 0.0]
CAM_FOCAL  = [2.0,   0.0, 0.2]
CAM_UP     = [0, 0, 1]
CAM_SCALE  = 3.0          # parallel scale [m] — controls zoom
VIEW_W, VIEW_H = 1400, 500

def make_view():
    v = GetRenderView()
    v.ViewSize                 = [VIEW_W, VIEW_H]
    v.Background               = [1, 1, 1]
    v.OrientationAxesVisibility = 0
    v.CameraPosition           = CAM_POS
    v.CameraFocalPoint         = CAM_FOCAL
    v.CameraViewUp             = CAM_UP
    v.CameraParallelProjection = 1
    v.CameraParallelScale      = CAM_SCALE
    return v

def save(path):
    v = GetRenderView()
    SaveScreenshot(path, v, ImageResolution=[VIEW_W, VIEW_H])
    print(f'saved: {path}')

# ── 1. Midplane α.water at t = 5 s ───────────────────────────────────────────
mid    = LegacyVTKReader(FileNames=[f'{VTK_DIR}/midPlane/midPlane_2518.vtk'])
midDsp = Show(mid)
ColorBy(midDsp, ('POINTS', 'alpha.water'))

lut = GetColorTransferFunction('alpha.water')
lut.ApplyPreset('Cool to Warm', True)
lut.RescaleTransferFunction(0.0, 1.0)

cb = GetScalarBar(lut, GetRenderView())
cb.Title = 'alpha water'
cb.ComponentTitle = ''
cb.Visibility = 1

make_view()
Render()
save(f'{CASE}/wave_pattern_midplane.png')
Delete(mid); del mid

# ── 2. GIF: free-surface interface side view t = 1–6 s ───────────────────────
# The interface.vtk is the α = 0.5 isosurface. Rendered from the same
# side camera as the midplane image, coloured by p_rgh, it shows the
# wave elevation profile evolving along the hull.

# Establish consistent colour limits across all frames
all_p = []
for t in range(1, 7):
    src = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    src.UpdatePipeline()
    arr = src.GetPointDataInformation().GetArray('p_rgh')
    if arr:
        all_p.extend([arr.GetRange()[0], arr.GetRange()[1]])
    Delete(src)

p_lo = min(all_p) if all_p else -500
p_hi = max(all_p) if all_p else 3000

frames = []
for t in range(1, 7):
    src    = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    srcDsp = Show(src)
    ColorBy(srcDsp, ('POINTS', 'p_rgh'))

    lut2 = GetColorTransferFunction('p_rgh')
    lut2.ApplyPreset('Cool to Warm', True)
    lut2.RescaleTransferFunction(p_lo, p_hi)

    cb2 = GetScalarBar(lut2, GetRenderView())
    cb2.Title = 'p_rgh [Pa]'
    cb2.ComponentTitle = ''
    cb2.Visibility = 1

    txt       = Text()
    txt.Text  = f't = {t} s    U = 1.668 m/s    Fr = 0.223'
    txtDsp    = Show(txt)
    txtDsp.FontSize       = 18
    txtDsp.Color          = [0, 0, 0]
    txtDsp.WindowLocation = 'Upper Center'

    make_view()
    Render()
    tmp = f'{CASE}/_frame_{t}.png'
    save(tmp)
    frames.append(Image.open(tmp).copy())   # copy so file can be removed
    Delete(txt); Delete(src)

out = f'{CASE}/wave_animation.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=700, loop=0)
print(f'wave_animation.gif saved ({len(frames)} frames)')

for f in glob.glob(f'{CASE}/_frame_*.png'):
    os.remove(f)
