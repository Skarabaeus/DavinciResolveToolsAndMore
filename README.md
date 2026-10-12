# DaVinci Resolve Tools and More

A collection of templates, scripts and other tools for DaVinci Resolve. Each tool lives in its own folder and has its own README with installation and usage instructions.

## Tools

| Tool | Type | Description |
|---|---|---|
| [EXIF Overlay](exif-overlay/) | Fusion Title template | Animated overlay that shows a photo's camera, lens, focal length, ISO, shutter speed and aperture, each with an icon and a staggered reveal. |
| [Photo Frame](photo-frame/) | Fusion Effect template + script | Frames a photo with a border, shadow and gradient background. The Add Photos script puts selected photos on the timeline with the frame, a filled-in EXIF Overlay and a camera sound. |
| [Photo Stack](photo-stack/) | Script | Turns up to 15 selected photos into one clip where framed, tilted photos slide in and stack up over a gradient. |

## Requirements

Tested with DaVinci Resolve Studio 21.1.1 on macOS. Check each tool's README for anything else it needs.

## Where Resolve looks for user files

These are Resolve's user folders on macOS. Each tool's README says exactly which folder it goes in.

| Kind | Folder |
|---|---|
| Fusion templates (titles, effects, transitions, generators) | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates/Edit/` |
| Scripts (Workspace → Scripts menu) | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/` |
| LUTs | `/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT/` (system-wide, not in your home folder) |

## Adding a new tool

1. Create a folder for it at the top level, named in lowercase with dashes (for example `my-new-tool/`).
2. Add a `README.md` in that folder covering what the tool does, how it works, and how to install it.
3. Add a row for it to the [Tools](#tools) table above.
