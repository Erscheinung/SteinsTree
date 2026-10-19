# Headless playtests

`harness.py` drives a built ROM in [PyBoy](https://github.com/Baekalfen/PyBoy):

- presses buttons and takes screenshots;
- reads GB Studio story variables;
- reads the player's tile position;
- walks shortest paths over a scene's collision map.

```
python3 -m pip install pyboy pillow numpy
```

## Build a ROM headlessly (optional)
GB Studio's own CLI can be built from source:

1. Clone `chrismaltby/gb-studio` at the tag matching your GB Studio version.
2. Run `yarn install`, then `yarn make:cli`.
3. Copy `appData/engine` and `buildTools/<platform>` from the installed app's
   `app.asar`.
4. Run `node out/cli/gb-studio-cli.js make:rom Dernier.json game.gb`.

Keep `build/rom/dernier.sym` and `globals.i` from the build folder next to the
ROM: the harness uses them to find `_script_memory`, `_actors` and the
variable slots.

## Example
```python
from harness import Game
g = Game("game.gb", "dernier.sym", "out/")
g.wait(700); g.press("start"); g.press("a")   # title -> New Game
g.clear()                                     # advance dialogue
print(g.var("Chapter"), g.player_tile())
g.shot("prologue")
```
The pause menu's **Chapters** entry jumps to any part of the game, which keeps
routes short. `dialog_open()`, `clear()` and `settle()` handle text timing.
