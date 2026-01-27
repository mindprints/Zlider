# Zlider - Presentation Zlideshow POC

Zlider is a lightweight desktop presenter that lets you line up browser tabs, images, PDFs, MP3s, or any launchable file and open them one at a time from a single control window. The latest redesign (versions 15-20) removed the external controller, added a full presentation toolbar, and introduced a compact mini mode so navigation never gets in the way of the show.

## Highlights and features

- **Single-window controller** - Click `Start` to enter presentation mode, keep the app on top, and steer every zlide without juggling extra windows.
- **One-at-a-time playback** - Zlides open individually (no more batch launches), eliminating the sync issues seen in the early proof of concept.
- **Flexible media support** - Mix browser URLs and local files; Zlider defers to your OS associations so anything that opens normally will work here.
- **Live zlide list** - Reorder, rename, or double-click any entry to jump to it. The active zlide is prefixed with `>` and highlighted in blue.
- **Mini mode** - Toggle `Mini` or press `Esc` to shrink the controller to a 400x60 always-on-top strip that keeps the navigation buttons and counter visible.
- **Status feedback** - A status bar and console logs confirm what is currently presenting, which is handy while rehearsing or debugging.

## Requirements

- Python 3.10+ with Tkinter (bundled with the regular installers on Windows and macOS).
- [`pynput`](https://pypi.org/project/pynput/) for upcoming keyboard automation helpers. Install it with:

  ```bash
  pip install pynput
  ```

Windows launches files with `os.startfile`, macOS uses `open`, and Linux uses `xdg-open`, so the same `.zlides` file works everywhere as long as the target assets exist.

## Running Zlider

```bash
python zlider.py
```

1. Click **New** for a blank zlideshow or **Open** to load an existing `.zlides` file.
2. Use **Add Browser Zlide** (auto-prefixes `https://` when missing) or **Add File Zlide** to build your run of show.
3. Arrange entries with **Move Up/Down**, rename them with **Edit**, and save to a `.zlides` file whenever you like.
4. Hit **Start** to switch into presentation mode.

## Creating and Managing Zlides

- **Browser zlide** - Provide a URL and Zlider will load it with your default browser when that zlide becomes active.
- **File zlide** - Point to any local file; the OS opens it with its default application (images, PDFs, MP3s, slides, etc.).
- **Reordering** - Keep your narrative intact with the Move buttons; the preview list always reflects the current order.
- **Editing/Deleting** - Update titles or remove entries in place; changes are reflected immediately.
- **Saving** - `.zlides` files are simple JSON so they play nicely with version control.

Example snippet:

```json
{
  "version": "1.0",
  "zlides": [
    { "id": 123, "type": "browser", "title": "Launch Video", "data": "https://example.com" },
    { "id": 456, "type": "file", "title": "Intro Song", "data": "D:/Media/intro.mp3" }
  ]
}
```

## Presenting

- Press **Start** to rebuild the toolbar with navigation controls, highlight the first zlide, and pin Zlider above other windows.
- Toolbar actions: `<<` (jump to first), `< Prev`, `Next >`, `>>` (jump to last), `Mini/Full`, and `End`.
- Each navigation action opens exactly one zlide, so content appears the moment you advance to it.
- Double-click any item in the list during a presentation to jump directly to that point in the deck.
- A counter such as `3/7` plus the blue highlight makes it clear where you are in the running order.
- Click **End** to exit presentation mode and return to the full editor.

## Keyboard and Mouse Shortcuts

- Left / Right arrows - previous / next zlide.
- Home / End - jump to first / last zlide.
- Space - advance to the next zlide.
- Escape - toggle mini mode while presenting.
- Double-click list entry - jump to that zlide (works both in and out of presentation mode).

## Mini Mode Workflow

1. Start presenting, then click **Mini** or press `Esc`.
2. The window collapses to a 400x60 bar that shows `<< | < | 3/7 | > | >> | Full | End` and stays on top.
3. Use either the compact buttons or the keyboard shortcuts to keep advancing while the full list stays hidden.
4. Click **Full** or press `Esc` again when you need to expand back to the editor.

## Sample Flow

1. Build a zlideshow with a mix of dashboards, websites, and local media.
2. Rehearse by running through the entire deck, confirming each zlide opens cleanly.
3. During a live session, stay in mini mode so the audience only sees the launched content while you control the pace.
4. Jump out of order when needed by double-clicking a list entry, then return to normal progression.

## Roadmap and Ideas

- Optional automation to close the previously opened zlide (especially for browser tabs) when advancing.
- Thumbnail or metadata previews inside the zlide list for quicker scanning.
- Saved presets so Zlider can auto-load a favorite `.zlides` file on launch.
- Import/export helpers for trading decks with collaborators.

Have feedback or feature requests? File an issue or drop notes in `Zlider_Claude_coversation.txt` before the next iteration.
