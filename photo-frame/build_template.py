#!/usr/bin/env python3
"""Generate the 'Photo Frame' Fusion Effect template (.setting) for DaVinci Resolve."""
import sys

CANVAS_W, CANVAS_H = 3840, 2160   # output size; Resolve fits it into the timeline, so only the aspect matters
PHOTO_SIZE = 0.9                  # photo height (or width) relative to the canvas
BORDER_WIDTH = 0.013              # relative to canvas height (~28 px at 2160)
BORDER_COLOR = (1, 1, 1)
GRADIENT = {                      # four-corner gradient behind the photo (sampled from the example project)
    "TopLeft": (0.369, 0.369, 0.369),
    "TopRight": (0.569, 0.569, 0.569),
    "BottomLeft": (0.259, 0.259, 0.259),
    "BottomRight": (0.129, 0.129, 0.129),
}
SHADOW_STRENGTH, SHADOW_SOFTNESS, SHADOW_DISTANCE = 0.85, 30, 0.005

# Fit factor of the photo inside the canvas, and border width in pixels
FIT = ("Frame.PhotoSize*math.min(Frame.Width/PhotoIn.Output.Width, Frame.Height/PhotoIn.Output.Height)")
BORDER = "Frame.BorderWidth*Frame.Height"

tools = []


def tool(name, body, x, y=0):
    tools.append(f"\t\t\t\t{name} = {body.rstrip()},\n".replace("__POS__", f"{{ {x}, {y} }}"))


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def slider(name, label, default, lo, hi):
    return (f'\t\t\t\t\t\t{name} = {{ LINKS_Name = "{label}", LINKID_DataType = "Number", INPID_InputControl = "SliderControl", '
            f'INP_Default = {default}, INP_MinScale = {lo}, INP_MaxScale = {hi}, INP_MinAllowed = 0, ICS_ControlPage = "Controls", }},\n')


def color(prefix, label, rgb, group):
    out = ""
    for i, (ch, v) in enumerate(zip(("Red", "Green", "Blue"), rgb)):
        nm = f'LINKS_Name = "{label}", ' if i == 0 else ""
        out += (f'\t\t\t\t\t\t{prefix}{ch} = {{ {nm}LINKID_DataType = "Number", INPID_InputControl = "ColorControl", '
                f'INP_Default = {v}, INP_MinScale = 0, INP_MaxScale = 1, IC_ControlGroup = {group}, IC_ControlID = {i}, ICS_ControlPage = "Controls", }},\n')
    return out


gradient_inputs = "".join(
    f"\t\t\t\t\t\t{corner}{ch} = Input {{ Value = {v}, }},\n"
    for corner, rgb in GRADIENT.items() for ch, v in zip(("Red", "Green", "Blue"), rgb)
) + "".join(f"\t\t\t\t\t\t{corner}Alpha = Input {{ Value = 1, }},\n" for corner in GRADIENT)

# Frame: the four-corner gradient canvas; also holds the custom controls
tool("Frame", f"""Background {{
\t\t\t\t\tCtrlWZoom = false,
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGlobalOut = Input {{ Value = 119, }},
\t\t\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\t\t\tWidth = Input {{ Value = {CANVAS_W}, }},
\t\t\t\t\t\tHeight = Input {{ Value = {CANVAS_H}, }},
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\t\t\tType = Input {{ Value = FuID {{ "Corner" }}, }},
{gradient_inputs}\t\t\t\t\t\tPhotoSize = Input {{ Value = {PHOTO_SIZE}, }},
\t\t\t\t\t\tBorderWidth = Input {{ Value = {BORDER_WIDTH}, }},
\t\t\t\t\t\tBorderRed = Input {{ Value = {BORDER_COLOR[0]}, }},
\t\t\t\t\t\tBorderGreen = Input {{ Value = {BORDER_COLOR[1]}, }},
\t\t\t\t\t\tBorderBlue = Input {{ Value = {BORDER_COLOR[2]}, }},
\t\t\t\t\t\tShadowStrength = Input {{ Value = {SHADOW_STRENGTH}, }},
\t\t\t\t\t\tShadowSoftness = Input {{ Value = {SHADOW_SOFTNESS}, }},
\t\t\t\t\t\tShadowDistance = Input {{ Value = {SHADOW_DISTANCE}, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t\tUserControls = ordered() {{
{slider("PhotoSize", "Photo Size", PHOTO_SIZE, 0.1, 1)}{slider("BorderWidth", "Border Width", BORDER_WIDTH, 0, 0.05)}{color("Border", "Border Color", BORDER_COLOR, 1)}{slider("ShadowStrength", "Shadow Strength", SHADOW_STRENGTH, 0, 1)}{slider("ShadowSoftness", "Shadow Softness", SHADOW_SOFTNESS, 0, 100)}{slider("ShadowDistance", "Shadow Distance", SHADOW_DISTANCE, 0, 0.05)}\t\t\t\t\t}},
\t\t\t\t}}""", 0, 0)

# PhotoIn: pass-through for the clip image, so expressions can read its size
tool("PhotoIn", """Transform {
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 0, -66)

card_w = f":return PhotoIn.Output.Width*{FIT}+2*{BORDER}"
card_h = f":return PhotoIn.Output.Height*{FIT}+2*{BORDER}"
tool("Card", f"""Background {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tGlobalOut = Input {{ Value = 119, }},
\t\t\t\t\t\tUseFrameFormatSettings = Input {{ Value = 0, }},
\t\t\t\t\t\tWidth = Input {{ Value = 1920, Expression = {lua_str(card_w)}, }},
\t\t\t\t\t\tHeight = Input {{ Value = 1080, Expression = {lua_str(card_h)}, }},
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input {{ Value = FuID {{ "SLog2" }}, }},
\t\t\t\t\t\tTopLeftRed = Input {{ Value = 1, Expression = "Frame.BorderRed", }},
\t\t\t\t\t\tTopLeftGreen = Input {{ Value = 1, Expression = "Frame.BorderGreen", }},
\t\t\t\t\t\tTopLeftBlue = Input {{ Value = 1, Expression = "Frame.BorderBlue", }},
\t\t\t\t\t\tTopLeftAlpha = Input {{ Value = 1, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", 110, -99)

# Clear: transparent canvas so the shadow blur isn't clipped at the card's edges
tool("Clear", """Background {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tGlobalOut = Input { Value = 119, },
\t\t\t\t\t\tUseFrameFormatSettings = Input { Value = 0, },
\t\t\t\t\t\tWidth = Input { Value = 1920, Expression = "Frame.Width", },
\t\t\t\t\t\tHeight = Input { Value = 1080, Expression = "Frame.Height", },
\t\t\t\t\t\t["Gamut.SLogVersion"] = Input { Value = FuID { "SLog2" }, },
\t\t\t\t\t\tTopLeftAlpha = Input { Value = 0, },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 110, 99)

tool("CardLayer", """Merge {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tBackground = Input { SourceOp = "Clear", Source = "Output", },
\t\t\t\t\t\tForeground = Input { SourceOp = "Card", Source = "Output", },
\t\t\t\t\t\tPerformDepthMerge = Input { Value = 0, },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 220, 99)

tool("FrameShadowBlur", """Blur {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tXBlurSize = Input { Value = 30, Expression = "Frame.ShadowSoftness*Frame.Height/1080", },
\t\t\t\t\t\tInput = Input { SourceOp = "CardLayer", Source = "Output", },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 330, 99)

tool("FrameShadowTint", """ColorGain {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tGainRed = Input { Value = 0, },
\t\t\t\t\t\tGainGreen = Input { Value = 0, },
\t\t\t\t\t\tGainBlue = Input { Value = 0, },
\t\t\t\t\t\tGainAlpha = Input { Value = 0.85, Expression = "Frame.ShadowStrength", },
\t\t\t\t\t\tInput = Input { SourceOp = "FrameShadowBlur", Source = "Output", },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 440, 99)

tool("MergeShadow", """Merge {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tBackground = Input { SourceOp = "Frame", Source = "Output", },
\t\t\t\t\t\tForeground = Input { SourceOp = "FrameShadowTint", Source = "Output", },
\t\t\t\t\t\tCenter = Input { Value = { 0.5, 0.495 }, Expression = "Point(0.5, 0.5-Frame.ShadowDistance)", },
\t\t\t\t\t\tPerformDepthMerge = Input { Value = 0, },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 440, 0)

tool("MergeCard", """Merge {
\t\t\t\t\tInputs = {
\t\t\t\t\t\tBackground = Input { SourceOp = "MergeShadow", Source = "Output", },
\t\t\t\t\t\tForeground = Input { SourceOp = "Card", Source = "Output", },
\t\t\t\t\t\tPerformDepthMerge = Input { Value = 0, },
\t\t\t\t\t},
\t\t\t\t\tViewInfo = OperatorInfo { Pos = __POS__ },
\t\t\t\t}""", 550, 0)

# Merge places the foreground 1:1 in pixels, so Size = fit factor; Lanczos keeps the big downscale clean
tool("MergePhoto", f"""Merge {{
\t\t\t\t\tInputs = {{
\t\t\t\t\t\tBackground = Input {{ SourceOp = "MergeCard", Source = "Output", }},
\t\t\t\t\t\tForeground = Input {{ SourceOp = "PhotoIn", Source = "Output", }},
\t\t\t\t\t\tSize = Input {{ Value = 1, Expression = {lua_str(":return " + FIT)}, }},
\t\t\t\t\t\tFilterMethod = Input {{ Value = 8, }},
\t\t\t\t\t\tPerformDepthMerge = Input {{ Value = 0, }},
\t\t\t\t\t}},
\t\t\t\t\tViewInfo = OperatorInfo {{ Pos = __POS__ }},
\t\t\t\t}}""", 660, 0)

# Published controls
inputs = ['\t\t\t\tMainInput1 = InstanceInput { SourceOp = "PhotoIn", Source = "Input", },\n']
n = 1


def inst(src, name=None, extra=""):
    global n
    nm = f', Name = "{name}"' if name else ""
    inputs.append(f'\t\t\t\tInput{n} = InstanceInput {{ SourceOp = "Frame", Source = "{src}"{nm}{extra}, }},\n')
    n += 1


inst("PhotoSize", "Photo Size", f", Default = {PHOTO_SIZE}")
inst("BorderWidth", "Border Width", f", Default = {BORDER_WIDTH}")
for i, ch in enumerate(("Red", "Green", "Blue")):
    inst(f"Border{ch}", "Border Color" if i == 0 else None, f", ControlGroup = 10, Default = {BORDER_COLOR[i]}")
for g, (corner, rgb) in enumerate(GRADIENT.items()):
    label = "Gradient " + corner.replace("Top", "Top ").replace("Bottom", "Bottom ")
    for i, ch in enumerate(("Red", "Green", "Blue")):
        inst(f"{corner}{ch}", label if i == 0 else None, f", ControlGroup = {11 + g}, Default = {rgb[i]}")
inst("ShadowStrength", "Shadow Strength", f", Default = {SHADOW_STRENGTH}")
inst("ShadowSoftness", "Shadow Softness", f", Default = {SHADOW_SOFTNESS}")
inst("ShadowDistance", "Shadow Distance", f", Default = {SHADOW_DISTANCE}")
inst("Width", "Canvas Width", f", Default = {CANVAS_W}")
inst("Height", "Canvas Height", f", Default = {CANVAS_H}")

setting = (
    "{\n\tTools = ordered() {\n\t\tPhotoFrame = MacroOperator {\n"
    "\t\t\tCtrlWZoom = false,\n"
    "\t\t\tInputs = ordered() {\n" + "".join(inputs) + "\t\t\t},\n"
    "\t\t\tOutputs = {\n\t\t\t\tMainOutput1 = InstanceOutput { SourceOp = \"MergePhoto\", Source = \"Output\", },\n\t\t\t},\n"
    "\t\t\tViewInfo = GroupInfo { Pos = { 0, 0 }, },\n"
    "\t\t\tTools = ordered() {\n" + "".join(tools) + "\t\t\t},\n"
    "\t\t},\n\t},\n\tActiveTool = \"PhotoFrame\"\n}\n"
)

out = sys.argv[1] if len(sys.argv) > 1 else "Photo Frame.setting"
with open(out, "w") as f:
    f.write(setting)
print("wrote", out)
