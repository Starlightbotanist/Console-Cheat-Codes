# Adjustable chase camera

For **Gran Turismo 3 A-Spec USA v1.10**, serial **PBPX-95503**, CRC **8AA991B0**. Other releases require different addresses.

Copy `8AA991B0.pnach` to PCSX2's cheats folder, enable cheats, restart the game, and select chase view (R1 with default controls). Merge with an existing file of that name if you need to retain unrelated cheats. Enable only one camera modification.

Keep exactly **one patch line active in each of the five settings sections**. Add `//` to the selected line and remove `//` from another choice. Leave the fixed code unchanged. Restart the game after edits; older save states can restore old RAM until the cheat reapplies.

| Setting | Default | Choices |
|---|---:|---|
| Height | 2.5 | 0.5 to 5, steps of 0.25 |
| Pitch down | 12.5 degrees | Up 10 to down 20, steps of 2.5 degrees |
| Distance | 6 | 4 to 12, steps of 0.5 |
| Horizontal spring | 60 | 10 to 500, with closer choices around ordinary values |
| Horizontal damping | 16 | 4 to 44, with closer choices around ordinary values |

Height and distance use the game's camera origin and world units. Spring controls horizontal follow strength; damping reduces oscillation. Stock horizontal motion is spring 30/damping 10. Vertical follow and road shake remain native. **Field of view is unchanged.**

The fixed code selects the editable chase slot when model-specific cameras exist, preserves the native bumper path, and applies pitch before local translation so pitch does not orbit the camera around the car.

Validated with PCSX2 2.7.510, Altezza RS200, Super Speedway, and controlled saved-state camera matrices: height/distance translate by the requested amounts, pitch rotates without appreciable position change, bumper output and FOV match native output, and spring/damping combinations reach the camera consumer. The default selection is height 2.5/pitch down 12.5/distance 6/spring 60/damping 16. Other cars/tracks, split screen, replay cameras, hardware, and controlled performance are unmeasured.

Implementation navigation reference: [GT3FreeCam](https://github.com/xan1242/GT3FreeCam). Its v1.00 tool is not required or included; this patch targets the v1.10 disc above.
