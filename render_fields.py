"""Render CFD field images using pvpython (ParaView offscreen rendering)."""
from paraview.simple import *
from PIL import Image
import glob, os

CASE    = os.path.dirname(os.path.abspath(__file__))
VTK_DIR = f'{CASE}/VTK'
SURF    = f'{CASE}/postProcessing/surfaces'

ALL_LUTS = []   # track every LUT created so we can hide all bars reliably

def hide_all_colorbars():
    """Hide scalar bars for every LUT created in this session."""
    v = GetRenderView()
    for lut in ALL_LUTS:
        try:
            GetScalarBar(lut, v).Visibility = 0
        except Exception:
            pass

def save(path, w=1400, h=500):
    SaveScreenshot(path, GetRenderView(), ImageResolution=[w, h])
    print(f'saved: {path}')

# ── 1. Midplane α.water at t = 5 s ───────────────────────────────────────────
mid    = LegacyVTKReader(FileNames=[f'{VTK_DIR}/midPlane/midPlane_2518.vtk'])
midDsp = Show(mid)
ColorBy(midDsp, ('POINTS', 'alpha.water'))

lut_a = GetColorTransferFunction('alpha.water')
lut_a.ApplyPreset('Cool to Warm', True)
lut_a.RescaleTransferFunction(0.0, 1.0)
ALL_LUTS.append(lut_a)

cb_a = GetScalarBar(lut_a, GetRenderView())
cb_a.Title = 'alpha.water'
cb_a.ComponentTitle = ''
cb_a.Orientation = 'Horizontal'
cb_a.WindowLocation = 'Lower Center'

v = GetRenderView()
v.ViewSize                  = [1400, 500]
v.Background                = [1, 1, 1]
v.OrientationAxesVisibility = 0
v.CameraPosition            = [2.0, -60.0, 0.2]
v.CameraFocalPoint          = [2.0,   0.0, 0.2]
v.CameraViewUp              = [0, 0, 1]
v.CameraParallelProjection  = 1
v.CameraParallelScale       = 3.0

hide_all_colorbars()
cb_a.Visibility = 1
Render()
save(f'{CASE}/wave_pattern_midplane.png', 1400, 500)
Delete(mid); del mid

# ── 2. Hull surface pressure — isometric view ─────────────────────────────────
hull_p   = LegacyVTKReader(FileNames=[f'{VTK_DIR}/hull/hull_2518.vtk'])
hullpDsp = Show(hull_p)
ColorBy(hullpDsp, ('POINTS', 'p'))

lut_p = GetColorTransferFunction('p')
lut_p.ApplyPreset('Cool to Warm', True)
lut_p.RescaleTransferFunction(0, 2500)
ALL_LUTS.append(lut_p)

cb_p = GetScalarBar(lut_p, GetRenderView())
cb_p.Title = 'Pressure [Pa]'
cb_p.ComponentTitle = ''
cb_p.Orientation = 'Horizontal'
cb_p.WindowLocation = 'Lower Center'

# Isometric from bow (x≈6.16) — camera in +x, -y, +z direction
# Hull centre ≈ (3.0, -0.2, 0.28); bow at x≈6.16, stern at x≈0
vp = GetRenderView()
vp.ViewSize                  = [1400, 700]
vp.Background                = [1, 1, 1]
vp.OrientationAxesVisibility = 0
vp.CameraParallelProjection  = 1
vp.CameraPosition            = [10.0, -4.0, 3.5]
vp.CameraFocalPoint          = [ 3.0, -0.2, 0.28]
vp.CameraViewUp              = [0, 0, 1]
vp.CameraParallelScale       = 1.4   # zoomed out to show full hull

hide_all_colorbars()
cb_p.Visibility = 1
Render()
save(f'{CASE}/hull_pressure_iso.png', 1400, 700)

# Side view: zoomed out to show full hull length
vp.ViewSize            = [1400, 500]
vp.CameraPosition      = [ 3.0, -10.0, 0.28]
vp.CameraFocalPoint    = [ 3.0,   0.0, 0.28]
vp.CameraViewUp        = [0, 0, 1]
vp.CameraParallelScale = 1.5

side_txt = Text(); side_txt.Text = 'SIDE VIEW  (port)'
sDsp = Show(side_txt); sDsp.FontSize = 20; sDsp.Bold = 1
sDsp.Color = [0,0,0]; sDsp.WindowLocation = 'Upper Left Corner'

hide_all_colorbars()
cb_p.Visibility = 1
Render()
save(f'{CASE}/hull_pressure_side.png', 1400, 500)
Hide(side_txt); Delete(side_txt)

# Bow-on view: mirror hull across y=0 to show full ship width
hull_mirror  = Reflect(Input=hull_p)
hull_mirror.Plane = 'Y Max'   # reflect across y=0 (symmetry plane)
hull_mirror.UpdatePipeline()
mirrorDsp = Show(hull_mirror)
ColorBy(mirrorDsp, ('POINTS', 'p'))
mirrorDsp.LookupTable = lut_p

vp.ViewSize            = [900, 700]
vp.CameraPosition      = [10.0,  0.0, 0.28]
vp.CameraFocalPoint    = [ 3.0,  0.0, 0.28]
vp.CameraViewUp        = [0, 0, 1]
vp.CameraParallelScale = 0.50

bow2_txt = Text(); bow2_txt.Text = 'BOW-ON VIEW  (full ship mirrored)'
b2Dsp = Show(bow2_txt); b2Dsp.FontSize = 20; b2Dsp.Bold = 1
b2Dsp.Color = [0,0,0]; b2Dsp.WindowLocation = 'Upper Left Corner'

hide_all_colorbars()
cb_p.Visibility = 1
Render()
save(f'{CASE}/hull_pressure_bow.png', 900, 700)
Hide(bow2_txt); Delete(bow2_txt)
Hide(mirrorDsp); Delete(hull_mirror)

Delete(hull_p); del hull_p

# ── 3. GIF: interface side view t = 1–6 ──────────────────────────────────────
gif_times = list(range(1, 7))

# Global z range for consistent colour scale across frames
z_lo, z_hi = 1e9, -1e9
for t in gif_times:
    src = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    src.UpdatePipeline()
    b = src.GetDataInformation().GetBounds()
    z_lo = min(z_lo, b[4])
    z_hi = max(z_hi, b[5])
    Delete(src)

lut_z = GetColorTransferFunction('z_elevation')
lut_z.ApplyPreset('Cool to Warm', True)
lut_z.RescaleTransferFunction(z_lo, z_hi)
ALL_LUTS.append(lut_z)

cb_z = GetScalarBar(lut_z, GetRenderView())
cb_z.Title = 'Free surface elevation [m]'
cb_z.ComponentTitle = ''
cb_z.Orientation = 'Horizontal'
cb_z.WindowLocation = 'Lower Center'

# Hull shown as solid grey throughout GIF
hull    = LegacyVTKReader(FileNames=[f'{VTK_DIR}/hull/hull_2518.vtk'])
hullDsp = Show(hull)
hullDsp.AmbientColor   = [0.35, 0.35, 0.35]
hullDsp.DiffuseColor   = [0.35, 0.35, 0.35]
hullDsp.ColorArrayName = ['POINTS', '']

frames = []
for t in gif_times:
    src  = LegacyVTKReader(FileNames=[f'{SURF}/{t}/interface.vtk'])
    calc = Calculator(Input=src)
    calc.ResultArrayName = 'z_elevation'
    calc.Function        = 'coordsZ'
    calc.UpdatePipeline()

    dsp = Show(calc)
    ColorBy(dsp, ('POINTS', 'z_elevation'))
    dsp.LookupTable = lut_z

    txt = Text()
    txt.Text = f't = {t} s'
    tDsp = Show(txt)
    tDsp.FontSize       = 24
    tDsp.Bold           = 1
    tDsp.Color          = [0, 0, 0]
    tDsp.WindowLocation = 'Upper Right Corner'

    gv = GetRenderView()
    gv.ViewSize                  = [1400, 500]
    gv.Background                = [1, 1, 1]
    gv.OrientationAxesVisibility = 0
    gv.CameraPosition            = [2.0, -60.0, 0.2]
    gv.CameraFocalPoint          = [2.0,   0.0, 0.2]
    gv.CameraViewUp              = [0, 0, 1]
    gv.CameraParallelProjection  = 1
    gv.CameraParallelScale       = 3.0

    hide_all_colorbars()
    cb_z.Visibility = 1
    Render()

    tmp = f'{CASE}/_frame_{t}.png'
    save(tmp, 1400, 500)
    frames.append(Image.open(tmp).copy())

    Hide(calc); Delete(calc); Delete(src)
    Hide(txt);  Delete(txt)

out = f'{CASE}/wave_animation.gif'
frames[0].save(out, save_all=True, append_images=frames[1:], duration=700, loop=0)
print(f'wave_animation.gif saved ({len(frames)} frames)')

for f in glob.glob(f'{CASE}/_frame_*.png'):
    os.remove(f)
