"""Turn the photos selected in the Media Pool into a stack of framed photos on one clip at the playhead.

Each photo gets a white border and a soft shadow, is tilted a little and slides in from a random side
on top of the previous ones, over a four-corner gradient. Everything lives in one Fusion composition
on one clip; the timing has no keyframes and is set on the comp's Controls node.

Install into ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit/
and run it from Workspace > Scripts on the Edit page.
"""
import math
import os
import random
import re
import subprocess
import tempfile

# --- Settings ---------------------------------------------------------------------------------
VIDEO_TRACK = 2
MAX_PHOTOS = 15
SECONDS_PER_PHOTO = 3.0    # time between two photos
HOLD_SECONDS = 1.0         # extra time after the last photo's interval
SLIDE_SECONDS = 0.8        # how long a photo takes to slide in
SLIDE_DISTANCE = 1.1       # start offset relative to the frame size; 0 = fade in instead of sliding
SLIDE_FIRST = False        # also slide in the first photo (otherwise it is there from the start)
DIRECTIONS = ("left", "right", "top", "bottom")   # sides photos slide in from, picked at random
MAX_TILT = 6.0             # degrees; 0 = no rotation
SPIN_IN = 8.0              # extra rotation in degrees while sliding, settles to the tilt
SCATTER = 0.025            # random offset from the center, relative to the frame size
PHOTO_SIZE = 0.78          # photo height (or width) relative to the frame
BORDER_WIDTH = 0.013       # relative to the frame height (~28 px at 2160)
BORDER_COLOR = (1, 1, 1)
GRADIENT = {               # four-corner gradient behind the photos
    "TopLeft": (0.369, 0.369, 0.369),
    "TopRight": (0.569, 0.569, 0.569),
    "BottomLeft": (0.259, 0.259, 0.259),
    "BottomRight": (0.129, 0.129, 0.129),
}
SHADOW_STRENGTH, SHADOW_SOFTNESS, SHADOW_DISTANCE = 0.85, 30, 0.006
# Photos larger than the frame are loaded from copies scaled down to fit it, kept in a folder next to
# the originals: a stack of full-size camera files crashed Resolve.
COPY_FOLDER = "Photo Stack {width}x{height}"
# -----------------------------------------------------------------------------------------------

try:
    resolve
except NameError:
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
fusion = resolve.Fusion()

LOADER_FORMATS = {".jpg": "JpegFormat", ".jpeg": "JpegFormat", ".png": "PNGFormat", ".tif": "TiffFormat",
                  ".tiff": "TiffFormat", ".exr": "OpenEXRFormat", ".dpx": "DPXFormat"}


def message(text):
    print(text)
    try:
        bmd
    except NameError:
        return
    ui = fusion.UIManager
    disp = bmd.UIDispatcher(ui)
    win = disp.AddWindow({"ID": "PhotoStackMsg", "WindowTitle": "Photo Stack", "Geometry": [400, 300, 460, 160]}, [
        ui.VGroup([
            ui.Label({"Text": text, "WordWrap": True, "Alignment": {"AlignHCenter": True, "AlignVCenter": True}}),
            ui.HGroup({"Weight": 0}, [ui.HGap(), ui.Button({"ID": "OK", "Text": "OK"})]),
        ]),
    ])
    win.On.OK.Clicked = lambda ev: disp.ExitLoop()
    win.On.PhotoStackMsg.Close = lambda ev: disp.ExitLoop()
    win.Show()
    disp.RunLoop()
    win.Hide()


def drop_frames(tc, fps):
    """Frame numbers skipped per minute in drop-frame timecode (shown with ';'), else 0."""
    return round(fps) // 15 if ";" in tc and round(fps) != fps else 0


def tc_to_frame(tc, fps):
    h, m, s, f = (int(x) for x in re.split("[:;.]", tc))
    minutes = h * 60 + m
    return ((h * 60 + m) * 60 + s) * round(fps) + f - drop_frames(tc, fps) * (minutes - minutes // 10)


def frame_to_tc(frame, fps, drop):
    n = round(fps)
    if drop:
        per_10min = n * 600 - drop * 9
        tens, rest = divmod(frame, per_10min)
        frame += drop * 9 * tens + (drop * ((rest - drop) // (n * 60 - drop)) if rest > drop else 0)
    sep = ";" if drop else ":"
    return "%02d:%02d:%02d%s%02d" % (frame // (n * 3600), frame // (n * 60) % 60, frame // n % 60, sep, frame % n)


def fitted_copy(path, width, height):
    """Return a copy of the photo scaled down to fit width x height, or the photo itself if it already fits.

    The copy goes into a folder next to the photo and is reused while it is newer than the photo.
    """
    fmt = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".tif": "tiff", ".tiff": "tiff"}.get(os.path.splitext(path)[1].lower())
    if not fmt:
        return path
    out = os.path.join(os.path.dirname(path), COPY_FOLDER.format(width=width, height=height), os.path.basename(path))
    try:
        if os.path.exists(out) and os.path.getmtime(out) >= os.path.getmtime(path):
            return out
        info = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", path],
                              capture_output=True, text=True, check=True).stdout
        w, h = (int(re.search(rf"{k}: (\d+)", info).group(1)) for k in ("pixelWidth", "pixelHeight"))
        scale = min(width / w, height / h)
        if scale >= 1:
            return path
        os.makedirs(os.path.dirname(out), exist_ok=True)
        quality = ["-s", "formatOptions", "best"] if fmt == "jpeg" else []
        subprocess.run(["sips", "-s", "format", fmt, *quality, "-Z", str(math.ceil(max(w, h) * scale)), path, "--out", out],
                       capture_output=True, check=True)
        return out
    except (OSError, subprocess.CalledProcessError, AttributeError):
        return path


# --- Composition ----------------------------------------------------------------------------------

def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slider(name, label, default, lo, hi, page="Controls"):
    return (f'\t\t\t\t{name} = {{ LINKS_Name = "{label}", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", '
            f'INP_Default = {default}, INP_MinScale = {lo}, INP_MaxScale = {hi}, ICS_ControlPage = "{page}", }},\n')


def checkbox(name, label, default, page="Controls"):
    return (f'\t\t\t\t{name} = {{ LINKS_Name = "{label}", LINKID_DataType = "Number", INPID_InputControl = "CheckboxControl", '
            f'INP_Integer = true, INP_Default = {default}, ICS_ControlPage = "{page}", }},\n')


def color(prefix, label, rgb, group):
    out = ""
    for i, (ch, v) in enumerate(zip(("Red", "Green", "Blue"), rgb)):
        nm = f'LINKS_Name = "{label}", ' if i == 0 else ""
        out += (f'\t\t\t\t{prefix}{ch} = {{ {nm}LINKID_DataType = "Number", INPID_InputControl = "ColorControl", '
                f'INP_Default = {v}, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = {group}, IC_ControlID = {i}, ICS_ControlPage = "Controls", }},\n')
    return out


def controls_tool(width, height):
    values = {
        "Interval": SECONDS_PER_PHOTO, "SlideSeconds": SLIDE_SECONDS, "SlideDistance": SLIDE_DISTANCE,
        "SlideFirst": int(SLIDE_FIRST), "MaxTilt": MAX_TILT, "SpinIn": SPIN_IN, "Scatter": SCATTER,
        "PhotoSize": PHOTO_SIZE, "BorderWidth": BORDER_WIDTH, "BorderRed": BORDER_COLOR[0],
        "BorderGreen": BORDER_COLOR[1], "BorderBlue": BORDER_COLOR[2], "ShadowStrength": SHADOW_STRENGTH,
        "ShadowSoftness": SHADOW_SOFTNESS, "ShadowDistance": SHADOW_DISTANCE,
    }
    inputs = "".join(f"\t\t\t\t{k} = Input {{ Value = {v}, }},\n" for k, v in values.items())
    inputs += "".join(f"\t\t\t\t{corner}{ch} = Input {{ Value = {v}, }},\n"
                      for corner, rgb in GRADIENT.items() for ch, v in zip(("Red", "Green", "Blue"), rgb))
    inputs += "".join(f"\t\t\t\t{corner}Alpha = Input {{ Value = 1, }},\n" for corner in GRADIENT)
    user_controls = (
        slider("Interval", "Seconds per Photo", SECONDS_PER_PHOTO, 0.5, 10)
        + slider("SlideSeconds", "Slide Duration", SLIDE_SECONDS, 0, 3)
        + slider("SlideDistance", "Slide Distance", SLIDE_DISTANCE, 0, 2)
        + checkbox("SlideFirst", "Slide In First Photo", int(SLIDE_FIRST))
        + slider("MaxTilt", "Max Tilt", MAX_TILT, 0, 20)
        + slider("SpinIn", "Spin While Sliding", SPIN_IN, 0, 45)
        + slider("Scatter", "Scatter", SCATTER, 0, 0.2)
        + slider("PhotoSize", "Photo Size", PHOTO_SIZE, 0.1, 1)
        + slider("BorderWidth", "Border Width", BORDER_WIDTH, 0, 0.05)
        + color("Border", "Border Color", BORDER_COLOR, 1)
        + slider("ShadowStrength", "Shadow Strength", SHADOW_STRENGTH, 0, 1)
        + slider("ShadowSoftness", "Shadow Softness", SHADOW_SOFTNESS, 0, 100)
        + slider("ShadowDistance", "Shadow Distance", SHADOW_DISTANCE, 0, 0.05)
    )
    return f"""\t\tControls = Background {{
\t\t\tCtrlWZoom = false,
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = 100000, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tWidth = Input {{ Value = {width}, }},
\t\t\t\tHeight = Input {{ Value = {height}, }},
\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\tType = Input {{ Value = FuID {{ "Corner" }}, }},
{inputs}\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ 0, -165 }} }},
\t\t\tUserControls = ordered() {{
{user_controls}\t\t\t}},
\t\t}},
"""


def photo_tools(i, path, rnd, prev, direction):
    """Tools for photo i: a static framed card (frozen in time so it is built once), merged onto `prev`."""
    x = 110 * (i + 1)
    load, card, pad, card_pad, blur, tint, shadow, card_shadow, photo, hold, stack = (
        f"{n}{i}" for n in ("Load", "Card", "Pad", "CardPad", "ShadowBlur", "ShadowTint", "Shadow", "CardShadow",
                            "Photo", "Hold", "Stack"))
    fit = f"Controls.PhotoSize*math.min(Controls.Width/{load}.Output.Width, Controls.Height/{load}.Output.Height)"
    border = "Controls.BorderWidth*Controls.Height"
    margin = "(3*Controls.ShadowSoftness/1080+Controls.ShadowDistance)*Controls.Height"
    fmt = LOADER_FORMATS.get(os.path.splitext(path)[1].lower(), "")
    fmt = f'\t\t\t\t\tFormatID = "{fmt}",\n' if fmt else ""

    dx, dy = {"left": (-1, 0), "right": (1, 0), "top": (0, 1), "bottom": (0, -1)}[direction]
    tilt = rnd.uniform(0.35, 1) * (1 if i % 2 else -1)
    jx, jy = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
    spin = -dx if dx else rnd.choice((-1, 1))
    first = "true" if i == 0 else "false"
    prelude = (
        ":local r=comp:GetPrefs('Comp.FrameFormat.Rate') local t=(time-comp.GlobalStart)/r "
        f"local t0={i}*Controls.Interval local d=math.max(Controls.SlideSeconds,0.001) "
        f"local still={first} and Controls.SlideFirst<0.5 "
        "local p=still and 1 or math.max(0,math.min(1,(t-t0)/d)) local e=1-(1-p)^3 "
        "local v=(still or t>=t0) and 1 or 0 "
    )
    center = prelude + (f"local k=(1-e)*Controls.SlideDistance "
                        f"return Point(0.5+{jx:.4f}*Controls.Scatter+{dx}*k, 0.5+{jy:.4f}*Controls.Scatter+{dy}*k)")
    angle = prelude + f"return {tilt:.4f}*Controls.MaxTilt+(1-e)*{spin}*Controls.SpinIn"
    blend = prelude + "return (Controls.SlideDistance>0) and v or v*e"

    return f"""\t\t{load} = Loader {{
\t\t\tClips = {{
\t\t\t\tClip {{
\t\t\t\t\tID = "Clip1",
\t\t\t\t\tFilename = {lua_str(path)},
{fmt}\t\t\t\t\tStartFrame = -1,
\t\t\t\t\tLengthSetManually = true,
\t\t\t\t\tTrimIn = 0,
\t\t\t\t\tTrimOut = 0,
\t\t\t\t\tExtendFirst = 0,
\t\t\t\t\tExtendLast = 100000,
\t\t\t\t\tLoop = 0,
\t\t\t\t\tAspectMode = 0,
\t\t\t\t\tDepth = 0,
\t\t\t\t\tTimeCode = 0,
\t\t\t\t\tGlobalStart = 0,
\t\t\t\t\tGlobalEnd = 100000
\t\t\t\t}}
\t\t\t}},
\t\t\tInputs = {{
\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\tGlobalOut = Input {{ Value = 100000, }},
\t\t\t\tHoldLastFrame = Input {{ Value = 100000, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 330 }} }},
\t\t}},
\t\t{card} = Background {{
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = 100000, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tWidth = Input {{ Value = 1920, Expression = {lua_str(f":return {load}.Output.Width*{fit}+2*{border}")}, }},
\t\t\t\tHeight = Input {{ Value = 1080, Expression = {lua_str(f":return {load}.Output.Height*{fit}+2*{border}")}, }},
\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\tTopLeftRed = Input {{ Value = 1, Expression = "Controls.BorderRed", }},
\t\t\t\tTopLeftGreen = Input {{ Value = 1, Expression = "Controls.BorderGreen", }},
\t\t\t\tTopLeftBlue = Input {{ Value = 1, Expression = "Controls.BorderBlue", }},
\t\t\t\tTopLeftAlpha = Input {{ Value = 1, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 297 }} }},
\t\t}},
\t\t{pad} = Background {{
\t\t\tInputs = {{
\t\t\t\tGlobalOut = Input {{ Value = 100000, }},
\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\tWidth = Input {{ Value = 1920, Expression = {lua_str(f":return {card}.Width+2*{margin}")}, }},
\t\t\t\tHeight = Input {{ Value = 1080, Expression = {lua_str(f":return {card}.Height+2*{margin}")}, }},
\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\tTopLeftAlpha = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 264 }} }},
\t\t}},
\t\t{card_pad} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "{pad}", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{card}", Source = "Output", }},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 231 }} }},
\t\t}},
\t\t{blur} = Blur {{
\t\t\tInputs = {{
\t\t\t\tXBlurSize = Input {{ Value = 30, Expression = "Controls.ShadowSoftness*Controls.Height/1080", }},
\t\t\t\tInput = Input {{ SourceOp = "{card_pad}", Source = "Output", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 198 }} }},
\t\t}},
\t\t{tint} = ColorGain {{
\t\t\tInputs = {{
\t\t\t\tGainRed = Input {{ Value = 0, }},
\t\t\t\tGainGreen = Input {{ Value = 0, }},
\t\t\t\tGainBlue = Input {{ Value = 0, }},
\t\t\t\tGainAlpha = Input {{ Value = 0.85, Expression = "Controls.ShadowStrength", }},
\t\t\t\tInput = Input {{ SourceOp = "{blur}", Source = "Output", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 165 }} }},
\t\t}},
\t\t{shadow} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "{pad}", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{tint}", Source = "Output", }},
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, Expression = {lua_str(f"Point(0.5, 0.5-Controls.ShadowDistance*Controls.Height/{pad}.Height)")}, }},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 132 }} }},
\t\t}},
\t\t{card_shadow} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "{shadow}", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{card}", Source = "Output", }},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 99 }} }},
\t\t}},
\t\t{photo} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "{card_shadow}", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{load}", Source = "Output", }},
\t\t\t\tSize = Input {{ Value = 1, Expression = {lua_str(":return " + fit)}, }},
\t\t\t\tFilterMethod = Input {{ Value = 8, }},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 66 }} }},
\t\t}},
\t\t{hold} = TimeSpeed {{
\t\t\tInputs = {{
\t\t\t\tSpeed = Input {{ Value = 0, }},
\t\t\t\tInterpolateBetweenFrames = Input {{ Value = 0, }},
\t\t\t\tInput = Input {{ SourceOp = "{photo}", Source = "Output", }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 33 }} }},
\t\t}},
\t\t{stack} = Merge {{
\t\t\tInputs = {{
\t\t\t\tBackground = Input {{ SourceOp = "{prev}", Source = "Output", }},
\t\t\t\tForeground = Input {{ SourceOp = "{hold}", Source = "Output", }},
\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, Expression = {lua_str(center)}, }},
\t\t\t\tAngle = Input {{ Value = 0, Expression = {lua_str(angle)}, }},
\t\t\t\tBlend = Input {{ Value = 1, Expression = {lua_str(blend)}, }},
\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t}},
\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {x}, 0 }} }},
\t\t}},
"""


def build_comp(paths, width, height):
    rnd = random.Random()
    body, prev, last_dir = "", "Controls", None
    for i, path in enumerate(paths):
        direction = rnd.choice([d for d in DIRECTIONS if d != last_dir] or list(DIRECTIONS))
        body += photo_tools(i, path, rnd, prev, direction)
        prev, last_dir = f"Stack{i}", direction
    comp = (
        "Composition {\n\tTools = ordered() {\n"
        "\t\tMediaIn1 = MediaIn { ViewInfo = OperatorInfo { Pos = { -110, -165 } }, },\n"
        + controls_tool(width, height) + body +
        "\t\tMediaOut1 = MediaOut {\n\t\t\tInputs = {\n"
        "\t\t\t\tIndex = Input { Value = \"0\", },\n"
        f"\t\t\t\tInput = Input {{ SourceOp = \"{prev}\", Source = \"Output\", }},\n"
        f"\t\t\t}},\n\t\t\tViewInfo = OperatorInfo {{ Pos = {{ {110 * (len(paths) + 1)}, -165 }} }},\n\t\t}},\n"
        "\t},\n}\n"
    )
    path = os.path.join(tempfile.gettempdir(), "Photo Stack.comp")
    with open(path, "w") as f:
        f.write(comp)
    return path


# --- Timeline -------------------------------------------------------------------------------------

def occupied(tl, track, start, end):
    return any(item.GetStart() < end and item.GetEnd() > start for item in tl.GetItemListInTrack("video", track) or [])


def find_clip(folder, path):
    """Return the Media Pool item for the file at `path` in `folder` or its subfolders, or None."""
    for clip in folder.GetClipList() or []:
        if clip.GetClipProperty("File Path") == path:
            return clip
    for sub in folder.GetSubFolderList() or []:
        clip = find_clip(sub, path)
        if clip:
            return clip
    return None


def make_host_clip(project, mp, still, frames, name):
    """Return a Media Pool Fusion clip at least `frames` long.

    Scripts can't set the length of a still on the timeline (it is always the Standard still duration),
    but a Fusion clip can be cut to any length. Build one from copies of a photo on a temporary timeline.
    """
    current = project.GetCurrentTimeline()
    existing = {project.GetTimelineByIndex(i + 1).GetName() for i in range(project.GetTimelineCount())}
    tmp_name, n = "Photo Stack (temp)", 1
    while tmp_name in existing:
        n += 1
        tmp_name = f"Photo Stack (temp {n})"
    tmp = mp.CreateEmptyTimeline(tmp_name)
    if not tmp:
        return None
    try:
        project.SetCurrentTimeline(tmp)
        items, pos = [], tmp.GetStartFrame()
        while pos - tmp.GetStartFrame() < frames:
            added = mp.AppendToTimeline([{"mediaPoolItem": still, "trackIndex": 1, "mediaType": 1, "recordFrame": pos}])
            if not added:
                return None
            items.append(added[0])
            pos = added[0].GetEnd()
        clip = tmp.CreateFusionClip(items)
        mpi = clip and clip.GetMediaPoolItem()
        if mpi:
            mpi.SetName(name)
        return mpi
    finally:
        project.SetCurrentTimeline(current)
        mp.DeleteTimelines([tmp])


def main():
    project = resolve.GetProjectManager().GetCurrentProject()
    tl = project and project.GetCurrentTimeline()
    if not tl:
        return message("Open a timeline first.")
    mp = project.GetMediaPool()
    photos = [c for c in mp.GetSelectedClips() or [] if c.GetClipProperty("Type") == "Still"]
    if not photos:
        return message("Select the photos for the stack in the Media Pool first.")
    if len(photos) > MAX_PHOTOS:
        return message(f"{len(photos)} photos are selected. A stack takes at most {MAX_PHOTOS}.")
    photos.sort(key=lambda c: c.GetName())

    fps = float(tl.GetSetting("timelineFrameRate"))
    width, height = int(tl.GetSetting("timelineResolutionWidth")), int(tl.GetSetting("timelineResolutionHeight"))
    frames = round((len(photos) * SECONDS_PER_PHOTO + HOLD_SECONDS) * fps)
    tc = tl.GetCurrentTimecode()
    pos = tc_to_frame(tc, fps)

    while tl.GetTrackCount("video") < VIDEO_TRACK:
        tl.AddTrack("video")
    if occupied(tl, VIDEO_TRACK, pos, pos + frames):
        return message(f"Track V{VIDEO_TRACK} needs {frames / fps:.1f} s of free space at the playhead.")

    paths = [fitted_copy(c.GetClipProperty("File Path"), width, height) for c in photos]
    # build the host clip from the small copy too; the full-size photo makes it as heavy as the stack was
    still = photos[0]
    if paths[0] != photos[0].GetClipProperty("File Path"):
        still = find_clip(mp.GetRootFolder(), paths[0]) or (mp.ImportMedia([paths[0]]) or [still])[0]
    host = make_host_clip(project, mp, still, frames, f"Photo Stack - {photos[0].GetName()} ({len(photos)} photos)")
    if not host:
        return message("Could not create the clip for the stack.")
    item = mp.AppendToTimeline([{"mediaPoolItem": host, "trackIndex": VIDEO_TRACK, "mediaType": 1,
                                 "startFrame": 0, "endFrame": frames, "recordFrame": pos}])
    item = item[0] if item else None
    # Resolve never overwrites on append; it moves or shortens the clip instead
    if not item or item.GetStart() != pos or item.GetEnd() != pos + frames:
        if item:
            tl.DeleteClips([item])
        mp.DeleteClips([host])
        return message(f"Could not place the stack on V{VIDEO_TRACK} at the playhead.")
    if not item.ImportFusionComp(build_comp(paths, width, height)):
        return message("The stack clip was added, but its Fusion composition could not be loaded.")
    tl.SetCurrentTimecode(frame_to_tc(pos + frames, fps, drop_frames(tc, fps)))
    print(f"Added a stack of {len(photos)} photos")


main()
