# Photo Stack for DaVinci Resolve

A script that turns up to 20 photos into a stack. Each photo is shown smaller with a white border and a soft shadow. It is tilted a little and slides in from a random side on top of the photos before it, over a four-corner gradient.

Tested with DaVinci Resolve Studio 21.1.1 on macOS.

## Files

| File | Purpose |
|---|---|
| `Photo Stack.py` | The script. Its settings are at the top of the file. |

## Installation

From the `photo-stack` folder:

```bash
R="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion"; mkdir -p "$R/Scripts/Edit" && cp "Photo Stack.py" "$R/Scripts/Edit/"
```

The script shows up in the **Workspace → Scripts** menu on the Edit page. If it doesn't, restart Resolve.

## Usage

1. In the Media Pool, select up to 20 photos.
2. On the timeline, put the playhead where the stack should start.
3. Run **Workspace → Scripts → Photo Stack**.

The script puts one clip on **V2** at the playhead. The photos appear in file-name order, one every 3 seconds, and the last one stays for 4 seconds (3 seconds plus a 1-second hold). The first photo is there from the start, and every later photo slides in. Afterwards the playhead sits at the end of the clip.

Each run picks new random tilts, offsets and slide directions. Run it again if you don't like the result.

The script never overwrites anything. If V2 isn't free for the whole length of the stack, it stops and says how much space it needs.

The script also leaves a Fusion clip named `Photo Stack - <first photo> (<n> photos)` in the Media Pool. The timeline clip is made from it, so keep it.

Photos larger than the timeline frame are not loaded at full size. The script writes copies scaled down to fit the frame into a folder next to the originals, named after the timeline resolution (for example `Photo Stack 3840x2160/`), and the stack loads those. Keep that folder with the photos. Copies are reused on later runs and rewritten when the original is newer. If the first photo was scaled, its copy is also imported into the current Media Pool bin, because the Fusion clip is built from it.

### Changing the stack afterwards

Everything lives in the clip's Fusion composition. Select the clip, open the **Fusion** page, and select the **Controls** node:

| Control | Default | Description |
|---|---|---|
| Seconds per Photo | 3 | Time from one photo to the next. The clip doesn't change length with it, so trim or re-run as needed. |
| Slide Duration | 0.8 | Seconds a photo takes to slide in. |
| Slide Distance | 1.1 | How far off-screen a photo starts, relative to the frame size. 0 makes photos fade in instead. |
| Slide In First Photo | off | Also animate the first photo. |
| Max Tilt | 6 | Largest tilt in degrees. Tilts alternate left and right. 0 keeps all photos straight. |
| Spin While Sliding | 8 | Extra rotation in degrees while a photo slides; it settles to the photo's tilt. |
| Scatter | 0.025 | Random offset from the center, relative to the frame size. |
| Photo Size | 0.78 | Size of a photo (without border) relative to the frame. |
| Border Width, Border Color | 0.013, white | Border width relative to the frame height. |
| Shadow Strength, Softness, Distance | 0.85, 30, 0.006 | Same as Photo Frame. |
| Hide Covered After | 6 | A photo stops being drawn once this many photos have landed on top of it, which keeps large stacks fast. Raise it if a hidden photo visibly pops out, e.g. a landscape photo under only portrait ones or with a large Scatter. 0 never hides photos. |
| Color tab | grays | The four corner colors of the gradient background. |

The tilt, offset and slide direction of each photo are fixed numbers inside the expressions on its `Stack<n>` node (`Center` and `Angle`), and Max Tilt and Scatter scale them. To swap a photo, change the file name on its `Load<n>` node. Use a file no larger than the frame (see the scaled copies above).

### Script settings

These are at the top of `Photo Stack.py` and become the defaults of the controls above. Re-copy the script after changing them.

| Setting | Default | Description |
|---|---|---|
| `VIDEO_TRACK` | 2 | Target track. Missing tracks are created. |
| `MAX_PHOTOS` | 20 | Maximum number of selected photos. |
| `SECONDS_PER_PHOTO`, `HOLD_SECONDS` | 3.0, 1.0 | Clip length = photos × seconds per photo + hold. |
| `DIRECTIONS` | all four sides | Sides photos slide in from. They are picked at random, never the same side twice in a row. |
| everything else | | Defaults of the Controls node (see above). |

## How it works

- **Host clip:** the scripting API can't set how long a still is on the timeline, because Resolve always uses the *Standard still duration* preference. A Fusion clip, though, can be placed at any length. The script creates a temporary timeline and fills it with copies of the first photo until it is long enough. It turns those into a Fusion clip and deletes the temporary timeline. It then places the Fusion clip on the real timeline cut to the exact length and loads the stack composition onto it with `TimelineItem.ImportFusionComp`. The composition ignores the clip's own image.
- **Composition:** the script writes the composition at runtime because the number of photos varies. For each photo it builds `Load<n>` (a Loader with the photo file), a border card, a padded transparent canvas with a blurred, darkened copy of the card as the shadow, and the photo merged onto the card. A `Hold<n>` node (TimeSpeed with speed 0) freezes that branch at one frame, so the photo is decoded and downscaled once rather than on every frame.
- **Scaled copies:** a stack of 15 camera files of up to 45 MP crashed Resolve inside Fusion. Photos larger than the frame are therefore scaled down with macOS `sips` first (JPEG, PNG and TIFF; other formats are loaded as they are).
- **Animation:** each `Stack<n>` Merge places the framed photo on the stack so far. Its `Center`, `Angle` and `Blend` are Lua expressions of `time` and the Controls values, with an ease-out cubic slide and no keyframes. Photo *n* starts at *n* × Seconds per Photo after the clip's first frame. The comp's global range is the whole Fusion clip, not the cut length, so it can't be used to fit the timing to the clip length.
- **Speed:** in testing, a UHD render with 6 photos ran at about 19 fps.
- **Supported files:** the photos are read by Fusion Loaders, which were tested with JPEG. Loaders can't read RAW files, so export those to JPEG first.
