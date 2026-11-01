# Gran Turismo 3

[Adjustable chase camera for USA v1.10 (PBPX-95503 / 8AA991B0)](Adjustable%20chase%20camera/README.md) provides selectable height, pitch, distance, spring and damping without changing field of view.

## September 28, 2000 prototype (SCPS-99999)

To fix graphical artifacts when using Hardware Mode in PCSX2, add these lines to the bottom of `<PCSX2-directory>\resources\GameIndex.yaml`:
```yaml
SCPS-99999:
    gsHWFixes:
    halfPixelOffset: 5 # Fixes edge bleed and lines.
    autoFlush: 1 # Partially fixes the sun occlusion and lens flare.
    getSkipCount: "GSC_PolyphonyDigitalGames" # Fixes post-processing.
```

PCSX2 updates overwrite this file, so you need to re-add those lines after each update.
