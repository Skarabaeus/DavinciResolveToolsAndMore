"""Add the photos selected in the Media Pool to the timeline at the playhead, one after another.

Each photo gets the Photo Frame look (scaled, border, shadow, four-corner gradient), an EXIF Overlay
filled in from the photo's metadata, and a camera shutter sound underneath.

Install into ~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Edit/
and run it from Workspace > Scripts on the Edit page.
"""
import os
import re
import tempfile

# --- Settings ---------------------------------------------------------------------------------
VIDEO_TRACK = 2
AUDIO_TRACK = 1
SOUND_FILE = "/Users/stefan/youtube/audio/sfx/pixabay/camera-13695.mp3"  # "" for no sound
OVERLAY_DELAY = 1.8        # seconds after the photo starts
OVERLAY_SECONDS = 5.0      # how long the overlay stays (0 = until the photo ends)
ICON_COLOR = (0, 0.976, 0)
TEXT_COLOR = (1, 1, 1)

PHOTO_FRAME_SETTING = "Templates:Edit/Effects/Photo Frame.setting"
EXIF_OVERLAY_SETTING = "Templates:Edit/Titles/EXIF Overlay.setting"

# Camera models as stored in EXIF -> how they should read on screen
CAMERA_NAMES = {
    "ILCE-7M4": "Sony A7 IV",
    "ILCE-7RM5": "Sony A7R V",
}
BRANDS = {
    "NIKON": "Nikon", "SONY": "Sony", "CANON": "Canon", "FUJIFILM": "Fujifilm", "OLYMPUS": "Olympus",
    "OM": "OM System", "PANASONIC": "Panasonic", "LEICA": "Leica", "PENTAX": "Pentax", "RICOH": "Ricoh",
    "HASSELBLAD": "Hasselblad", "APPLE": "Apple",
}
# -----------------------------------------------------------------------------------------------

try:
    resolve
except NameError:
    import DaVinciResolveScript as dvr
    resolve = dvr.scriptapp("Resolve")
fusion = resolve.Fusion()


def message(text):
    print(text)
    try:
        bmd
    except NameError:
        return
    ui = fusion.UIManager
    disp = bmd.UIDispatcher(ui)
    win = disp.AddWindow({"ID": "AddPhotosMsg", "WindowTitle": "Add Photos", "Geometry": [400, 300, 460, 160]}, [
        ui.VGroup([
            ui.Label({"Text": text, "WordWrap": True, "Alignment": {"AlignHCenter": True, "AlignVCenter": True}}),
            ui.HGroup({"Weight": 0}, [ui.HGap(), ui.Button({"ID": "OK", "Text": "OK"})]),
        ]),
    ])
    win.On.OK.Clicked = lambda ev: disp.ExitLoop()
    win.On.AddPhotosMsg.Close = lambda ev: disp.ExitLoop()
    win.Show()
    disp.RunLoop()
    win.Hide()


def tc_to_frame(tc, fps):
    h, m, s, f = (int(x) for x in re.split("[:;.]", tc))
    return ((h * 60 + m) * 60 + s) * round(fps) + f


def frame_to_tc(frame, fps):
    n = round(fps)
    return "%02d:%02d:%02d:%02d" % (frame // (n * 3600), frame // (n * 60) % 60, frame // n % 60, frame % n)


# --- EXIF formatting ----------------------------------------------------------------------------

def number(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return f"{x:g}"


def camera_name(model, maker):
    model, maker = (model or "").strip(), (maker or "").strip()
    if model in CAMERA_NAMES:
        return CAMERA_NAMES[model]
    if not model:
        return ""
    brand_key = maker.split()[0].upper() if maker else ""
    brand = BRANDS.get(brand_key, maker.split()[0].title() if maker else "")
    first = model.split()[0]
    if first.upper() in BRANDS or (brand_key and first.upper() == brand_key):
        return " ".join([BRANDS.get(first.upper(), brand)] + model.split()[1:])
    return f"{brand} {model}".strip()


def exif_rows(mpi):
    p = mpi.GetClipProperty()
    focal, iso, aperture = number(p.get("Focal Point (mm)")), number(p.get("ISO")), number(p.get("Camera Aperture"))
    shutter = (p.get("Shutter Speed") or "").replace(" ", "")
    if shutter and not shutter.endswith("s"):
        shutter += "s"
    return {
        "Camera": camera_name(p.get("Camera Type"), p.get("Camera Manufacturer")),
        "Lens": (p.get("Lens Type") or "").strip(),
        "Focal": f"{focal}mm" if focal else "",
        "ISO": f"ISO {iso}" if iso else "",
        "Shutter": shutter,
        "Aperture": f"f/{aperture}" if aperture else "",
    }


# --- Composition ----------------------------------------------------------------------------------

def macro_block(path):
    """Return the 'Name = MacroOperator { ... }' text from a generated .setting file."""
    text = open(fusion.MapPath(path)).read()
    start = text.index("Tools = ordered() {") + len("Tools = ordered() {")
    depth, i, in_str = 1, start, False
    while depth:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 1
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    return text[start:i - 1].strip().rstrip(",")


def build_comp(width, height):
    frame = macro_block(PHOTO_FRAME_SETTING)
    frame = frame.replace("Width = Input { Value = 3840, },", f"Width = Input {{ Value = {width}, }},")
    frame = frame.replace("Height = Input { Value = 2160, },", f"Height = Input {{ Value = {height}, }},")
    # Clip comps run at the photo's resolution, so the overlay gets an explicit canvas size
    overlay = macro_block(EXIF_OVERLAY_SETTING)
    overlay = overlay.replace("UseFrameFormatSettings = Input { Value = 1, },", "UseFrameFormatSettings = Input { Value = 0, },")
    overlay = overlay.replace("Width = Input { Value = 1920, },", f"Width = Input {{ Value = {width}, }},")
    overlay = overlay.replace("Height = Input { Value = 1080, },", f"Height = Input {{ Value = {height}, }},")
    comp = (
        "Composition {\n\tTools = ordered() {\n"
        "\t\tMediaIn1 = MediaIn { ViewInfo = OperatorInfo { Pos = { -220, 0 } }, },\n"
        f"\t\t{frame},\n"
        f"\t\t{overlay},\n"
        "\t\tOverlayMerge = Merge {\n\t\t\tInputs = {\n"
        "\t\t\t\tBackground = Input { SourceOp = \"MergePhoto\", Source = \"Output\", },\n"
        "\t\t\t\tForeground = Input { SourceOp = \"DropShadow\", Source = \"Output\", },\n"
        "\t\t\t\tPerformDepthMerge = Input { Value = 0, },\n"
        "\t\t\t},\n\t\t\tViewInfo = OperatorInfo { Pos = { 220, 0 } },\n\t\t},\n"
        "\t\tMediaOut1 = MediaOut {\n\t\t\tInputs = {\n"
        "\t\t\t\tIndex = Input { Value = \"0\", },\n"
        "\t\t\t\tInput = Input { SourceOp = \"OverlayMerge\", Source = \"Output\", },\n"
        "\t\t\t},\n\t\t\tViewInfo = OperatorInfo { Pos = { 330, 0 } },\n\t\t},\n"
        "\t},\n}\n"
    )
    path = os.path.join(tempfile.gettempdir(), "Photo Frame + EXIF.comp")
    with open(path, "w") as f:
        f.write(comp)
    return path


def fill_comp(comp, rows):
    comp.Lock()
    comp.FindTool("PhotoIn").ConnectInput("Input", comp.FindTool("MediaIn1"))
    for key, value in rows.items():
        comp.FindTool("Text" + key).SetInput("StyledText", value)
    controls = comp.FindTool("Controls")
    controls.SetInput("Delay", OVERLAY_DELAY)
    controls.SetInput("Length", OVERLAY_SECONDS)
    for ch, i in (("Red", 0), ("Green", 1), ("Blue", 2)):
        controls.SetInput("Icon" + ch, ICON_COLOR[i])
        controls.SetInput("Text" + ch, TEXT_COLOR[i])
    if not any(rows.values()):
        comp.FindTool("OverlayMerge").SetInput("Blend", 0)
    comp.Unlock()


# --- Timeline -------------------------------------------------------------------------------------

def find_clip(folder, path):
    for clip in folder.GetClipList() or []:
        if clip.GetClipProperty("File Path") == path:
            return clip
    for sub in folder.GetSubFolderList() or []:
        found = find_clip(sub, path)
        if found:
            return found
    return None


def occupied(tl, kind, track, start, end, ignore=None):
    for item in tl.GetItemListInTrack(kind, track) or []:
        if ignore and item.GetUniqueId() == ignore.GetUniqueId():
            continue
        if item.GetStart() < end and item.GetEnd() > start:
            return True
    return False


def main():
    project = resolve.GetProjectManager().GetCurrentProject()
    tl = project and project.GetCurrentTimeline()
    if not tl:
        return message("Open a timeline first.")
    mp = project.GetMediaPool()
    photos = [c for c in mp.GetSelectedClips() or [] if c.GetClipProperty("Type") == "Still"]
    if not photos:
        return message("Select one or more photos in the Media Pool first.")
    photos.sort(key=lambda c: c.GetName())

    sound = None
    if SOUND_FILE:
        sound = find_clip(mp.GetRootFolder(), SOUND_FILE)
        if not sound:
            imported = mp.ImportMedia([SOUND_FILE]) or []
            sound = imported[0] if imported else None
        if not sound:
            return message(f"Could not import the sound file:\n{SOUND_FILE}")

    for kind, track in (("video", VIDEO_TRACK), ("audio", AUDIO_TRACK)):
        while tl.GetTrackCount(kind) < track:
            tl.AddTrack(kind, "stereo") if kind == "audio" else tl.AddTrack(kind)

    fps = float(tl.GetSetting("timelineFrameRate"))
    width, height = int(tl.GetSetting("timelineResolutionWidth")), int(tl.GetSetting("timelineResolutionHeight"))
    comp_path = build_comp(width, height)
    pos = tc_to_frame(tl.GetCurrentTimecode(), fps)
    added = 0

    for mpi in photos:
        if occupied(tl, "video", VIDEO_TRACK, pos, pos + 1):
            break
        item = mp.AppendToTimeline([{"mediaPoolItem": mpi, "trackIndex": VIDEO_TRACK, "mediaType": 1, "recordFrame": pos}])
        item = item[0] if item else None
        # Resolve never overwrites on append; it moves or shortens the clip instead. Undo that and stop.
        if not item or item.GetStart() != pos or occupied(tl, "video", VIDEO_TRACK, item.GetStart(), item.GetEnd(), item):
            if item:
                tl.DeleteClips([item])
            break
        end = item.GetEnd()
        comp = item.ImportFusionComp(comp_path)
        if comp:
            fill_comp(comp, exif_rows(mpi))
        if sound and not occupied(tl, "audio", AUDIO_TRACK, pos, pos + 1):
            clip = mp.AppendToTimeline([{"mediaPoolItem": sound, "trackIndex": AUDIO_TRACK, "mediaType": 2, "recordFrame": pos}])
            clip = clip[0] if clip else None
            if clip and (clip.GetStart() != pos or occupied(tl, "audio", AUDIO_TRACK, clip.GetStart(), clip.GetEnd(), clip)):
                tl.DeleteClips([clip])
        pos = end
        added += 1

    tl.SetCurrentTimecode(frame_to_tc(pos, fps))
    if added < len(photos):
        message(f"Added {added} of {len(photos)} photos. Track V{VIDEO_TRACK} is not free at the playhead "
                f"for the rest; make room and run the script again with the remaining photos selected.")
    else:
        print(f"Added {added} photos")


main()
