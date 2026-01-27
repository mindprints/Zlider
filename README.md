# Zlider - Presentation Zlideshow Tool

Zlider is a lightweight desktop presenter that lets you line up browser tabs, images, PDFs, MP3s, desktop applications, or any launchable file and navigate them one at a time from a single control window. The intuitive dual-mode interface (full editor + compact mini mode) keeps navigation out of the way during presentations while providing full control.

## Highlights and Features

- **Single-window controller** - Click `Start` to enter presentation mode, keep the app on top, and steer every zlide without juggling extra windows.
- **One-at-a-time playback** - Zlides open individually with optional auto-close of the previous zlide for a cleaner workflow.
- **Flexible media support** - Mix browser URLs, local files, and desktop applications; Zlider defers to your OS associations so anything that opens normally will work here.
- **Live zlide list** - Reorder, rename, or double-click any entry to jump to it. The active zlide is prefixed with `▶` and highlighted.
- **Mini mode** - Available both before and during presentation. Toggle `▼ Mini` or press `Esc` to shrink the controller to a compact always-on-top strip.
- **Auto-close mode** - Optionally close the previous zlide automatically when navigating (works with apps, files, and browser windows).
- **Quick Launch** - Open all zlides or selected zlides with a single click, plus a "Close All" button to clean up.
- **Presentation timer** - Track elapsed time during your presentation with a built-in timer.
- **Status feedback** - Window title, list frame header, and status bar show the current file and progress.

## Requirements

- Python 3.10+ with Tkinter (bundled with the regular installers on Windows and macOS).

Windows launches files with `os.startfile`, macOS uses `open`, and Linux uses `xdg-open`, so the same `.zlides` file works everywhere as long as the target assets exist.

## Running Zlider

```bash
python zlider.py
```

1. Click **New** for a blank zlideshow or **Open** to load an existing `.zlides` file.
2. Use **Add Browser Zlide**, **Add File Zlide**, or **Add Application** to build your run of show.
3. Arrange entries with **Move Up/Down**, rename them with **Edit**, and save to a `.zlides` file.
4. Hit **▶ Start** to switch into presentation mode.

## Creating and Managing Zlides

| Zlide Type | Icon | Description |
|------------|------|-------------|
| **Browser** | 🌐 | Opens a URL in your default browser (auto-prefixes `https://` when missing) |
| **File** | 📄 | Opens any local file with its default application (images, PDFs, MP3s, etc.) |
| **Application** | 🖥️ | Launches a desktop application (.exe, .lnk shortcuts, .app) |

### Zlide Management
- **Reordering** - Keep your narrative intact with the Move Up/Down buttons
- **Editing/Deleting** - Update titles or remove entries; changes are reflected immediately
- **Multi-select** - Use Ctrl+click or Shift+click to select multiple zlides for batch operations
- **Saving** - `.zlides` files are simple JSON so they play nicely with version control

### File Format (v1.1)

```json
{
  "version": "1.1",
  "settings": {
    "auto_close_mode": false
  },
  "zlides": [
    { "id": 123, "type": "browser", "title": "Launch Video", "data": "https://example.com" },
    { "id": 456, "type": "file", "title": "Intro Song", "data": "D:/Media/intro.mp3" },
    { "id": 789, "type": "app", "title": "PowerPoint", "data": "C:/path/to/presentation.lnk" }
  ]
}
```

## Quick Launch

The Quick Launch section provides batch operations:

| Button | Action |
|--------|--------|
| **🚀 Open All Zlides** | Opens every zlide in the list at once (confirmation for 5+ items) |
| **📂 Open Selected** | Opens only the currently highlighted zlides |
| **❌ Close All Opened** | Closes all tracked opened processes |

## Settings

### Auto-Close Previous Zlide
Enable the **🔄 Auto-close previous** checkbox to automatically close the previous zlide when navigating during a presentation:

- **Browser zlides**: Opens each URL in a new browser window (not tab) for reliable closing
- **Applications**: Terminates the launched process
- **Files**: Closes if opened via subprocess

The 🔄 indicator appears in the toolbar: **red** when active, **gray** when disabled.

## Presenting

1. Press **▶ Start** to enter presentation mode with navigation controls
2. The window becomes always-on-top and displays:
   - **Timer** - Elapsed time (MM:SS format)
   - **Auto-close indicator** - 🔄 shows mode status
   - **Navigation** - `◀◀` (first), `◀ Prev`, counter, `Next ▶`, `▶▶` (last)
   - **Mode controls** - `▼ Mini`, `■ End`
3. Each navigation action opens exactly one zlide
4. Double-click any list entry to jump directly to that zlide
5. Click **■ End** to exit presentation mode and return to the editor

## Mini Mode

Mini mode is available **both before and during presentations**:

### Editing Mini Mode
```
┌────────────────────────────────────────────────────────┐
│  📋 filename                              X zlides     │
│  [🚀 Open All] [📂 Selected] | [▶ Start] | [▲ Full]   │
└────────────────────────────────────────────────────────┘
```
- Shows zlideshow name and zlide count
- Quick access to Open All, Open Selected, and Start
- Click **▲ Full** or press **Esc** to expand

### Presentation Mini Mode
```
┌────────────────────────────────────────────────────────────────────┐
│                        current zlide                    next ▶     │
│  00:00 🔄 | [◀◀][◀]    1/6    [▶][▶▶] | [▲ Full] [■ End]         │
└────────────────────────────────────────────────────────────────────┘
```
- Shows current, previous, and next zlide names
- Full navigation controls with timer
- Click **▲ Full** or press **Esc** to expand

## Keyboard Shortcuts

| Key | Action | Mode |
|-----|--------|------|
| **←** / **→** | Previous / Next zlide | Presentation |
| **Home** / **End** | Jump to first / last zlide | Presentation |
| **Space** | Advance to next zlide | Presentation |
| **Escape** | Toggle mini mode | Both |
| **Double-click** | Jump to clicked zlide | Both |

## Sample Workflow

1. **Build** - Create a zlideshow with dashboards, websites, apps, and local media
2. **Rehearse** - Run through the deck, confirming each zlide opens cleanly
3. **Present** - Use mini mode so the audience sees only your content while you control the pace
4. **Cleanup** - Use "Close All Opened" to close everything when done

## Window Title & Display

Zlider shows the current zlideshow name in multiple places:
- **Window title bar**: `Zlider - filename`
- **List frame header**: `Zlideshow: filename (X zlides)`
- **Mini mode**: `📋 filename` with zlide count

## Technical Notes

- **Cross-platform**: Works on Windows, macOS, and Linux
- **Process tracking**: Tracks subprocess.Popen objects for auto-close and close-all functionality
- **Browser handling**: Uses `--new-window` flag for Chrome, Edge, Firefox to open separate windows instead of tabs
- **Settings persistence**: Auto-close mode is saved with the zlideshow file

## Changelog

### v1.1 (Current)
- Added auto-close previous zlide feature
- Added Quick Launch section (Open All, Open Selected, Close All)
- Added desktop application (.exe, .lnk) support as zlide type
- Mini mode now available before starting presentation
- Added presentation timer
- Window title and list frame show zlideshow name
- Settings saved in zlideshow file
- Improved compact mode transitions
- Enhanced process tracking for cleanup

### v1.0
- Initial release with basic presentation functionality
- Browser and file zlide support
- Single-window controller with mini mode

---

Have feedback or feature requests? File an issue on the repository.
