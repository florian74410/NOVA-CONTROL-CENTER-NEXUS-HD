# NEXUS HD design assets

The three uploaded ElectroBlueNEON reference boards are the art-direction source for the V1 Qt-native renderer. They were **not** directly embedded as fixed-size sprites because their UI text, arrows, grid layout and mixed-alpha surfaces are baked into the composites.

V1 recreates the common visual grammar with scalable Qt gradients, neon accents, PCB tracings and widget state styling. Source PNG atlases and cleaned 9-slice elements should be added in a later dedicated art-asset commit after slicing, verifying true transparency, and removing baked labels. Keep source sheets separate from production widgets.

## Planned layout
- `SourceSheets/` — original boards, untouched
- `ElectroBlueNEON/Controls,Windows,Menus,Effects/` — RGBA slices
- `RougeERROR/Controls,Windows,Menus,Effects/` — RGBA slices
- `Animations/` — verified frame strips and metadata
- `Old/` — rejected but useful references

**No remote app modules or SSH credentials belong in this directory.**
