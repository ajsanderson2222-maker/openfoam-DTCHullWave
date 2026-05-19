"""Render CFD field images using pvpython (ParaView offscreen rendering)."""
from paraview.simple import *
from PIL import Image
import glob, os

CASE    = os.path.dirname(os.path.abspath(__file__))
VTK_DIR = f'{CASE}/VTK'
SURF    = f'{CASE}/postProcessing/surfaces'

VIEW_W, VIEW_H = 1400, 500

# Exact camera matching the midplane image: side view along -y, x-z plane
def apply_camera(v):
    v.CameraPosition           = [2.0, -60.0, 0.2]
    v.CameraFocalPoint         = [2.0,   0.0, 0.2]
    v.CameraViewUp             = [0, 0, 1]
    v.CameraParallelProjection = 1
    v.CameraParallelScale      = 3.0
    v.ViewSize                 = [VIEW_W, VIEW_H]
    v.Background               = [1, 1, 1]
    v.OrientationAxesVisibility = 0

def save(path):
    SaveScreenshot(path, GetRenderView(), ImageResolution=[VIEW_W, VIEW_H])
    print(f'saved: {path}')

# ── 1. Midplane α.water at t = 5 s ───────────────────────────────────────────
mid    = LegacyVTKReader(FileNames=[f'{VTK_DIR}/midPlane/midPlane_2518.vtk'])
midDsp = Show(mid)
ColorBy(midDsp, ('POINTS', 'alpha.water'))

lut_a = GetColorTransferFunction('alpha.water')
lut_a.ApplyPreset('Cool to Warm', True)
lut_a.RescaleTransferFunction(0.0, 1.0)

cb_a = GetScalarBar(lut_a, GetRenderView())
cb_a.Title = 'alpha.water'
cb_a.ComponentTitle = ''
cb_a.Visibility = 1

v = GetRenderView()
apply_camera(v)
Render()
save(f'{CASE}/wave_pattern_midplane.png')
Delete(mid); del mid

# ── 2. GIF: interface side view t = 1–6 s ─────────────────────────────────────
# Use a Calculator to expose z as a scalar field so we can colour by
# wave elevation — same visual idea as the alpha midplane image.

gif_times = list(range(1, 7))

# Pass 1: find global z range across all frames for a fixed colour scale
z_lo, z_hi = 1e9, -1e9
for t in gif_times:
    src = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    src.UpdatePipeline()
    b = src.GetDataInformation().GetBounds()  # xmin xmax ymin ymax zmin zmax
    z_lo = min(z_lo, b[4])
    z_hi = max(z_hi, b[5])
    Delete(src)

# Set up LUT once — reused for every frame
lut_z = GetColorTransferFunction('z_elevation')
lut_z.ApplyPreset('Cool to Warm', True)
lut_z.RescaleTransferFunction(z_lo, z_hi)

cb_z = GetScalarBar(lut_z, GetRenderView())
cb_z.Title = 'Free surface elevation [m]'
cb_z.ComponentTitle = ''
cb_z.Orientation = 'Horizontal'
cb_z.WindowLocation = 'Lower Center'
cb_z.Visibility = 1

frames = []
for t in gif_times:
    src  = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    calc = Calculator(Input=src)
    calc.ResultArrayName = 'z_elevation'
    calc.Function = 'coordsZ'
    calc.UpdatePipeline()

    dsp = Show(calc)
    ColorBy(dsp, ('POINTS', 'z_elevation'))
    # Apply the shared LUT (don't let ParaView auto-rescale)
    dsp.LookupTable = lut_z
    cb_z.Visibility = 1

    # Time label
    txt = Text()
    txt.Text = f't = {t} s'
    tDsp = Show(txt)
    tDsp.FontSize = 24
    tDsp.Bold = 1
    tDsp.Color = [0, 0, 0]
    tDsp.WindowLocation = 'Upper Right Corner'

    apply_camera(GetRenderView())
    Render()

    tmp = f'{CASE}/_frame_{t}.png'
    save(tmp)
    frames.append(Image.open(tmp).copy())

    Hide(calc); Delete(calc); Delete(src)
    Hide(txt);  Delete(txt)

out = f'{CASE}/wave_animation.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=700, loop=0)
print(f'wave_animation.gif saved ({len(frames)} frames)')

for f in glob.glob(f'{CASE}/_frame_*.png'):
    os.remove(f)
