#!/usr/bin/env python3
"""Generate the 'EXIF Overlay' Fusion Title template (.setting) for DaVinci Resolve."""
import sys

ICON_DIR = "Templates:Edit/Titles/EXIF Overlay Icons/"

ROWS = [
    # key,       label,      default text,        size,  style
    ("Camera",   "camera",   "Sony A7 IV",        0.034, "Bold"),
    ("Lens",     "lens",     "FE 35mm F1.4 GM",   0.028, "Semibold"),
    ("Focal",    "focal",    "35mm",              0.028, "Regular"),
    ("ISO",      "iso",      "ISO 400",           0.028, "Regular"),
    ("Shutter",  "shutter",  "1/250s",            0.028, "Regular"),
    ("Aperture", "aperture", "f/2.8",             0.028, "Regular"),
]

X_ICON, X_TEXT = 0.055, 0.078
Y_BOTTOM, SPACING = 0.09, 0.055
ICON_PX, ICON_SCALE = 256, 0.15  # 256px icon * 0.15 = ~38px at 1920 wide
N = len(ROWS)


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def anim(i):
    """Lua prelude computing eased intro (ei), outro (eo) and alpha (a) for row i."""
    return (
        ":local r=comp:GetPrefs('Comp.FrameFormat.Rate') "
        "local s=Controls.Stagger local d=Controls.Duration "
        f"local t=(time-comp.GlobalStart)/r local te=(comp.GlobalEnd+1-time)/r "
        f"local p=math.max(0,math.min(1,(t-0.1-{i}*s)/d)) "
        f"local q=math.max(0,math.min(1,(te-0.05-{N - 1 - i}*s*0.6)/(d*0.7))) "
        "local ei=1-(1-p)^3 local eo=1-(1-q)^3 local a=ei*eo "
    )


def y(i):
    return Y_BOTTOM + (N - 1 - i) * SPACING


tools = []
pos = 0


def tool(name, body, x=None, ypos=0):
    global pos
    if x is None:
        x = pos
        pos += 110
    tools.append(f"\t\t\t\t{name} = {body.rstrip()},\n")
    tools[-1] = tools[-1].replace("__POS__", f"{{ {x}, {ypos} }}")


# Controls / transparent base
tool("Controls", """Background {
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tInputs = {
\t\t\t\t\t\tGlobalOut = Input { Value = 119, },
\t\t\t\t\t\tWidth = Input { Value = 1920, },
\t\t\t\t\t\tHeight = Input { Value = 1080, },
\t\t\t\t\t\tUseFrameFormatSettings = Input { Value = 1, },
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
\t\t\t\t\t\tTopLeftRed = Input { Value = 0, },
\t\t\t\t\t\tTopLeftGreen = Input { Value = 0, },
\t\t\t\t\t\tTopLeftBlue = Input { Value = 0, },
\t\t\t\t\t\tTopLeftAlpha = Input { Value = 0, },
\t\t\t\t\t\tStagger = Input { Value = 0.12, },
\t\t\t\t\t\tDuration = Input { Value = 0.55, },
\t\t\t\t\t\tTextRed = Input { Value = 1, },
\t\t\t\t\t\tTextGreen = Input { Value = 1, },
\t\t\t\t\t\tTextBlue = Input { Value = 1, },
\t\t\t\t\t\tIconRed = Input { Value = 1, },
\t\t\t\t\t\tIconGreen = Input { Value = 0.784, },
\t\t\t\t\t\tIconBlue = Input { Value = 0.341, },
\t\t\t\t\t\tIconSize = Input { Value = 1, },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t\tUserControls = ordered() {
\t\t\t\t\t\tStagger = { LINKS_Name = "Stagger (s)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0.12, INP_MinScale = 0, INP_MaxScale = 0.5, INP_MinAllowed = 0, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tDuration = { LINKS_Name = "Reveal Duration (s)", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 0.55, INP_MinScale = 0.05, INP_MaxScale = 2, INP_MinAllowed = 0.01, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tTextRed = { LINKS_Name = "Text Color", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 1, IC_ControlID = 0, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tTextGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 1, IC_ControlID = 1, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tTextBlue = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 1, IC_ControlID = 2, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tIconRed = { LINKS_Name = "Icon Color", LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 1, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 2, IC_ControlID = 0, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tIconGreen = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 0.784, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 2, IC_ControlID = 1, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tIconBlue = { LINKID_DataType = "Number", INPID_InputControl = "ColorControl", INP_Default = 0.341, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = 2, IC_ControlID = 2, ICS_ControlPage = "Controls", },
\t\t\t\t\t\tIconSize = { LINKS_Name = "Icon Size", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", INP_Default = 1, INP_MinScale = 0.25, INP_MaxScale = 2, INP_MinAllowed = 0, ICS_ControlPage = "Controls", },
\t\t\t\t\t},
\t\t\t\t}""")

prev = "Controls"
for i, (key, icon, text, size, style) in enumerate(ROWS):
    xcol = 110 * (i + 1)
    tool(f"Text{key}", f"""TextPlus {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGlobalOut = Input {{ Value = 119, }},
\t\t\t\t\t\tWidth = Input {{ Value = 1920, }},
\t\t\t\t\t\tHeight = Input {{ Value = 1080, }},
\t\t\t\t\t\tUseFrameFormatSettings = Input {{ Value = 1, }},
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\t\t\tCenter = Input {{ Value = {{ {X_TEXT}, {y(i):.4f} }}, }},
\t\t\t\t\t\tStyledText = Input {{ Value = {lua_str(text)}, }},
\t\t\t\t\t\tFont = Input {{ Value = "Open Sans", }},
\t\t\t\t\t\tStyle = Input {{ Value = "{style}", }},
\t\t\t\t\t\tSize = Input {{ Value = {size}, }},
\t\t\t\t\t\tVerticalJustificationNew = Input {{ Value = 3, }},
\t\t\t\t\t\tHorizontalLeftCenterRight = Input {{ Value = -1, }},
\t\t\t\t\t\tHorizontalJustificationNew = Input {{ Value = 3, }},
\t\t\t\t\t\tRed1 = Input {{ Value = 1, Expression = "Controls.TextRed", }},
\t\t\t\t\t\tGreen1 = Input {{ Value = 1, Expression = "Controls.TextGreen", }},
\t\t\t\t\t\tBlue1 = Input {{ Value = 1, Expression = "Controls.TextBlue", }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=xcol, ypos=-99)

    tool(f"Icon{key}", f"""Loader {{
\t\t\t\t\tClips = {{
\t\t\t\t\t\tClip {{
\t\t\t\t\t\t\tID = "Clip1",
\t\t\t\t\t\t\tFilename = "{ICON_DIR}{icon}.png",
\t\t\t\t\t\t\tFormatID = "PNGFormat",
\t\t\t\t\t\t\tStartFrame = -1,
\t\t\t\t\t\t\tLengthSetManually = true,
\t\t\t\t\t\t\tTrimIn = 0,
\t\t\t\t\t\t\tTrimOut = 0,
\t\t\t\t\t\t\tExtendFirst = 0,
\t\t\t\t\t\t\tExtendLast = 100000,
\t\t\t\t\t\t\tLoop = 0,
\t\t\t\t\t\t\tAspectMode = 0,
\t\t\t\t\t\t\tDepth = 0,
\t\t\t\t\t\t\tTimeCode = 0,
\t\t\t\t\t\t\tGlobalStart = 0,
\t\t\t\t\t\t\tGlobalEnd = 100000
\t\t\t\t\t\t}}
\t\t\t\t\t}},
\t\t\t\t\tInputs = {{
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\t\t\tGlobalOut = Input {{ Value = 100000, }},
\t\t\t\t\t\tHoldLastFrame = Input {{ Value = 100000, }},
\t\t\t\t\t\tPostMultiplyByAlpha = Input {{ Value = 1, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=xcol, ypos=-198)

    tool(f"Tint{key}", f"""ColorGain {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGainRed = Input {{ Value = 1, Expression = "Controls.IconRed", }},
\t\t\t\t\t\tGainGreen = Input {{ Value = 1, Expression = "Controls.IconGreen", }},
\t\t\t\t\t\tGainBlue = Input {{ Value = 1, Expression = "Controls.IconBlue", }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "Icon{key}", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=xcol + 55, ypos=-165)

    a = anim(i)
    text_center = a + "return Point(0.5-(1-ei)*0.025-(1-eo)*0.012, 0.5)"
    text_blend = a + "return a"
    # back-ease overshoot on the icon pop
    icon_size = (a + "local c=1.70158 local b=1+(c+1)*(p-1)^3+c*(p-1)^2 "
                 f"return {ICON_SCALE}*Controls.IconSize*Controls.Output.Width/1920*math.max(0,b)*(0.6+0.4*eo)")
    icon_angle = a + "return (1-ei)*-35"

    tool(f"MergeText{key}", f"""Merge {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBlend = Input {{ Value = 1, Expression = {lua_str(text_blend)}, }},
\t\t\t\t\t\tBackground = Input {{ SourceOp = "{prev}", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "Text{key}", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, Expression = {lua_str(text_center)}, }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=xcol, ypos=0)

    tool(f"MergeIcon{key}", f"""Merge {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBlend = Input {{ Value = 1, Expression = {lua_str(text_blend)}, }},
\t\t\t\t\t\tBackground = Input {{ SourceOp = "MergeText{key}", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "Tint{key}", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ Value = {{ {X_ICON}, {y(i):.4f} }}, }},
\t\t\t\t\t\tSize = Input {{ Value = {ICON_SCALE}, Expression = {lua_str(icon_size)}, }},
\t\t\t\t\t\tAngle = Input {{ Value = 0, Expression = {lua_str(icon_angle)}, }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=xcol + 55, ypos=33)
    prev = f"MergeIcon{key}"

endx = 110 * (N + 1)
tool("Layout", f"""Transform {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tCenter = Input {{ Value = {{ 0.5, 0.5 }}, }},
\t\t\t\t\t\tPivot = Input {{ Value = {{ {X_ICON - 0.02}, {Y_BOTTOM - 0.03} }}, }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "{prev}", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=endx, ypos=33)

tool("ShadowBlur", f"""Blur {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tXBlurSize = Input {{ Value = 4, }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "Layout", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=endx, ypos=99)

tool("ShadowTint", f"""ColorGain {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGainRed = Input {{ Value = 0, }},
\t\t\t\t\t\tGainGreen = Input {{ Value = 0, }},
\t\t\t\t\t\tGainBlue = Input {{ Value = 0, }},
\t\t\t\t\t\tGainAlpha = Input {{ Value = 0.75, }},
\t\t\t\t\t\tInput = Input {{ SourceOp = "ShadowBlur", Source = "Output", }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=endx + 110, ypos=99)

tool("DropShadow", f"""Merge {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBackground = Input {{ SourceOp = "ShadowTint", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "Layout", Source = "Output", }},
\t\t\t\t\t\tCenter = Input {{ Value = {{ 0.4988, 0.5022 }}, }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", x=endx + 110, ypos=33)

# Published controls
inputs = []
n = 1


def inst(src_op, src, name=None, extra=""):
    global n
    nm = f', Name = "{name}"' if name else ""
    inputs.append(f'\t\t\t\tInput{n} = InstanceInput {{ SourceOp = "{src_op}", Source = "{src}"{nm}{extra}, }},\n')
    n += 1


for key, _, text, _, _ in ROWS:
    inst(f"Text{key}", "StyledText", key, f", Default = {lua_str(text)}")
inst("Layout", "Center", "Position", ", DefaultX = 0.5, DefaultY = 0.5")
inst("Layout", "Size", "Scale", ", Default = 1")
inst("Controls", "TextRed", "Text Color", ", ControlGroup = 20, Default = 1")
inst("Controls", "TextGreen", None, ", ControlGroup = 20, Default = 1")
inst("Controls", "TextBlue", None, ", ControlGroup = 20, Default = 1")
inst("Controls", "IconRed", "Icon Color", ", ControlGroup = 21, Default = 1")
inst("Controls", "IconGreen", None, ", ControlGroup = 21, Default = 0.784")
inst("Controls", "IconBlue", None, ", ControlGroup = 21, Default = 0.341")
inst("Controls", "IconSize", "Icon Size", ", Default = 1")
inst("Controls", "Stagger", "Stagger (s)", ", Default = 0.12")
inst("Controls", "Duration", "Reveal Duration (s)", ", Default = 0.55")
inst("ShadowTint", "GainAlpha", "Shadow Strength", ", Default = 0.75")
inst("ShadowBlur", "XBlurSize", "Shadow Softness", ", Default = 4")

setting = (
    "{\n\tTools = ordered() {\n\t\tEXIFOverlay = MacroOperator {\n"
    "\t\t\tCtrlWZoom = false,\n"
    "\t\t\tInputs = ordered() {\n" + "".join(inputs) + "\t\t\t},\n"
    "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput { SourceOp = \"DropShadow\", Source = \"Output\", },\n\t\t\t},\n"
    "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 }, },\n"
    "\t\t\tTools = ordered() {\n" + "".join(tools) + "\t\t\t},\n"
    "\t\t},\n\t},\n\tActiveTool = \"EXIFOverlay\"\n}\n"
)

out = sys.argv[1] if len(sys.argv) > 1 else "EXIF Overlay.setting"
with open(out, "w") as f:
    f.write(setting)
print("wrote", out)
