"""
Zlider - A presentation tool for managing and presenting zlides (browser tabs, files, and apps).
"""
import json
import os
import platform
import subprocess
import tkinter as tk
import webbrowser
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Optional, Callable, Union
import shutil


class ZlideType(Enum):
    """Types of zlides that can be added to a presentation."""
    BROWSER = "browser"
    FILE = "file"
    APP = "app"


class Colors:
    """Color constants for the UI theme."""
    DARK_BG = '#2b2b2b'
    DARK_BTN = '#3c3c3c'
    DARK_BTN_ACTIVE = '#4c4c4c'
    HIGHLIGHT_BLUE = '#4da6ff'
    TIMER_GREEN = '#00ff00'
    MUTED_TEXT = '#888888'
    SEPARATOR = '#555555'
    END_BTN = '#8b0000'
    END_BTN_ACTIVE = '#a00000'
    CURRENT_ZLIDE_BG = 'lightblue'
    TIMER_LABEL_FG = 'green'
    COUNTER_LABEL_FG = 'blue'
    AUTO_CLOSE_ON = '#ff6b6b'
    AUTO_CLOSE_OFF = '#666666'


@dataclass
class Zlide:
    """Represents a single zlide in a presentation."""
    type: str
    title: str
    data: str  # URL for browser, path for file/app
    id: int = field(default_factory=lambda: id(object()))

    def to_dict(self) -> dict:
        """Convert zlide to dictionary for serialization."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> 'Zlide':
        """Create a Zlide from a dictionary."""
        try:
            return Zlide(
                type=d["type"],
                title=d["title"],
                data=d["data"],
                id=d.get("id", id(object()))
            )
        except KeyError as e:
            raise ValueError(f"Missing required field: {e}") from e


class PlatformHelper:
    """Cross-platform utilities for opening files and applications."""
    
    @staticmethod
    def get_system() -> str:
        """Get the current operating system name."""
        return platform.system()
    
    @staticmethod
    def get_default_browser_path() -> Optional[str]:
        """Get the path to the default browser executable."""
        system = PlatformHelper.get_system()
        
        if system == "Windows":
            # Common browser paths on Windows
            browsers = [
                os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%ProgramFiles%\Mozilla Firefox\firefox.exe"),
                os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            ]
            for browser in browsers:
                if os.path.exists(browser):
                    return browser
            # Fallback: try to find via where command
            result = shutil.which("chrome") or shutil.which("firefox") or shutil.which("msedge")
            return result
            
        elif system == "Darwin":  # macOS
            browsers = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                "/Applications/Safari.app/Contents/MacOS/Safari",
            ]
            for browser in browsers:
                if os.path.exists(browser):
                    return browser
            return None
            
        else:  # Linux
            result = shutil.which("google-chrome") or shutil.which("firefox") or shutil.which("chromium")
            return result
    
    @staticmethod
    def open_file(filepath: str) -> Optional[subprocess.Popen]:
        """Open a file with the default system application. Returns process if trackable."""
        system = PlatformHelper.get_system()
        if system == "Windows":
            # Use subprocess to track the process
            try:
                # Try to get the associated application
                proc = subprocess.Popen(
                    ["cmd", "/c", "start", "", filepath],
                    shell=False,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )  # noqa: S603
                return proc
            except Exception:
                os.startfile(filepath)
                return None
        elif system == "Darwin":  # macOS
            return subprocess.Popen(["open", filepath])  # noqa: S603, S607
        else:  # Linux
            return subprocess.Popen(["xdg-open", filepath])  # noqa: S603, S607
    
    @staticmethod
    def open_app(filepath: str) -> Optional[subprocess.Popen]:
        """Launch an application or shortcut. Returns process if trackable."""
        system = PlatformHelper.get_system()
        if system == "Windows":
            if filepath.lower().endswith('.lnk'):
                try:
                    proc = subprocess.Popen(
                        ["cmd", "/c", "start", "", filepath],
                        shell=False,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )  # noqa: S603
                    return proc
                except Exception:
                    os.startfile(filepath)
                    return None
            else:
                return subprocess.Popen([filepath], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)  # noqa: S603
        elif system == "Darwin":  # macOS
            return subprocess.Popen(["open", filepath])  # noqa: S603, S607
        else:  # Linux
            return subprocess.Popen([filepath])  # noqa: S603
    
    @staticmethod
    def open_browser_window(url: str) -> Optional[subprocess.Popen]:
        """Open URL in a new browser window (not tab). Returns process for tracking."""
        system = PlatformHelper.get_system()
        browser_path = PlatformHelper.get_default_browser_path()
        
        if browser_path:
            try:
                if system == "Windows":
                    # --new-window flag works for Chrome, Edge, Firefox
                    return subprocess.Popen(
                        [browser_path, "--new-window", url],
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                    )  # noqa: S603
                else:
                    return subprocess.Popen([browser_path, "--new-window", url])  # noqa: S603
            except Exception:
                pass
        
        # Fallback to webbrowser module (can't track this)
        webbrowser.open_new(url)
        return None
    
    @staticmethod
    def close_process(proc: Optional[subprocess.Popen]) -> None:
        """Attempt to close a tracked process."""
        if proc is None:
            return
        try:
            proc.terminate()
            # Give it a moment to terminate gracefully
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.kill()
        except Exception as e:
            print(f"Could not close process: {e}")
    
    @staticmethod
    def get_default_bg() -> str:
        """Get the default background color for the current platform."""
        system = PlatformHelper.get_system()
        if system == "Windows":
            return 'SystemButtonFace'
        else:
            return ''  # Empty string uses system default on other platforms


class ZliderApp:
    """Main application class for the Zlider presentation tool."""
    
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Zlider - Presentation Tool")
        self.root.geometry("900x700")

        self.zlides: list[Zlide] = []
        self.current_zlide_index: int = -1
        self.presentation_mode: bool = False
        self.current_file: Optional[str] = None
        self.compact_mode: bool = False
        
        # Auto-close mode: automatically close previous zlide when navigating
        self.auto_close_mode: bool = False
        
        # Track currently open process for auto-close functionality
        self.current_process: Optional[subprocess.Popen] = None
        
        # Track all opened processes for "Close All" functionality
        self.opened_processes: list[subprocess.Popen] = []
        
        # Store original geometry for restoring from compact mode
        self.normal_geometry: str = "900x700"
        
        # Timer for presentation
        self.presentation_start_time: Optional[datetime] = None
        self.timer_id: Optional[str] = None

        # Configure root to stay on top when in presentation mode
        self.root.attributes('-topmost', False)

        # Setup keyboard shortcuts
        self._setup_keybindings()

        self.create_widgets()

    def _setup_keybindings(self) -> None:
        """Configure keyboard shortcuts."""
        # Navigation bindings (only work in presentation mode)
        nav_bindings: dict[str, Callable[[], None]] = {
            "<Left>": self.previous_zlide,
            "<Right>": self.next_zlide,
            "<Home>": lambda: self.go_to_zlide(0),
            "<End>": lambda: self.go_to_zlide(len(self.zlides) - 1),
            "<space>": self.next_zlide,
        }
        for key, action in nav_bindings.items():
            self.root.bind(key, lambda e, a=action: a() if self.presentation_mode else None)
        
        # Escape always works for compact mode toggle
        self.root.bind("<Escape>", lambda e: self.toggle_compact_mode())

    def create_widgets(self) -> None:
        """Create and layout all UI widgets."""
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")

        # Top toolbar
        self.toolbar = ttk.Frame(self.main_frame)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Button(self.toolbar, text="New", command=self.new_zlideshow, width=8).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self.toolbar, text="Open", command=self.open_zlideshow, width=8).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(self.toolbar, text="Save", command=self.save_zlideshow, width=8).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        # Presentation controls
        self.pres_controls_frame = ttk.Frame(self.toolbar)
        
        ttk.Button(
            self.pres_controls_frame,
            text="▶ Start",
            command=self.start_presentation,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        self.pres_controls_frame.pack(side=tk.LEFT)
        
        # Mini mode button (always visible)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )
        
        self.mini_btn = ttk.Button(
            self.toolbar,
            text="▼ Mini",
            command=self.toggle_compact_mode,
            width=8
        )
        self.mini_btn.pack(side=tk.LEFT, padx=2)

        # Zlide list frame (will update title with file name)
        self.list_frame = ttk.LabelFrame(self.main_frame, text="Zlideshow", padding="5")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 5))

        # Zlide listbox with scrollbar
        scrollbar = ttk.Scrollbar(self.list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.zlide_listbox = tk.Listbox(
            self.list_frame, 
            yscrollcommand=scrollbar.set, 
            height=25,
            font=('Arial', 10),
            selectmode=tk.EXTENDED  # Allow multiple selection
        )
        self.zlide_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.zlide_listbox.yview)
        
        # Double-click to open zlide
        self.zlide_listbox.bind('<Double-Button-1>', self.on_zlide_double_click)

        # Zlide controls frame
        controls_frame = ttk.LabelFrame(self.main_frame, text="Edit Zlides", padding="5")
        controls_frame.grid(row=1, column=1, sticky="nsew")

        ttk.Button(
            controls_frame,
            text="➕ Add Browser Zlide",
            command=self.add_browser_zlide,
            width=20,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            controls_frame,
            text="➕ Add File Zlide",
            command=self.add_file_zlide,
            width=20,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            controls_frame,
            text="➕ Add Application",
            command=self.add_app_zlide,
            width=20,
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            controls_frame, text="✏️ Edit Zlide", command=self.edit_zlide, width=20
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            controls_frame, text="🗑️ Delete Zlide", command=self.delete_zlide, width=20
        ).pack(pady=5, fill=tk.X)
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).pack(pady=10, fill=tk.X)
        ttk.Button(
            controls_frame, text="⬆️ Move Up", command=self.move_up, width=20
        ).pack(pady=5, fill=tk.X)
        ttk.Button(
            controls_frame, text="⬇️ Move Down", command=self.move_down, width=20
        ).pack(pady=5, fill=tk.X)
        
        # Separator before batch actions
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).pack(pady=10, fill=tk.X)
        
        # Batch open section
        batch_label = ttk.Label(controls_frame, text="Quick Launch", font=('Arial', 9, 'bold'))
        batch_label.pack(pady=(5, 2))
        
        ttk.Button(
            controls_frame, 
            text="🚀 Open All Zlides", 
            command=self.open_all_zlides, 
            width=20
        ).pack(pady=5, fill=tk.X)
        
        ttk.Button(
            controls_frame, 
            text="📂 Open Selected", 
            command=self.open_selected_zlides, 
            width=20
        ).pack(pady=5, fill=tk.X)
        
        ttk.Button(
            controls_frame, 
            text="❌ Close All Opened", 
            command=self.close_all_zlides, 
            width=20
        ).pack(pady=5, fill=tk.X)
        
        # Settings section
        ttk.Separator(controls_frame, orient=tk.HORIZONTAL).pack(pady=10, fill=tk.X)
        
        settings_label = ttk.Label(controls_frame, text="Settings", font=('Arial', 9, 'bold'))
        settings_label.pack(pady=(5, 2))
        
        # Auto-close checkbox
        self.auto_close_var = tk.BooleanVar(value=False)
        self.auto_close_check = ttk.Checkbutton(
            controls_frame,
            text="🔄 Auto-close previous",
            variable=self.auto_close_var,
            command=self._on_auto_close_toggle
        )
        self.auto_close_check.pack(pady=5, fill=tk.X)
        
        # Auto-close info label
        self.auto_close_info = ttk.Label(
            controls_frame,
            text="Close previous zlide when\nnavigating (presentation mode)",
            font=('Arial', 8),
            foreground='gray'
        )
        self.auto_close_info.pack(pady=(0, 5))

        # Status bar
        self.status_bar = ttk.Label(self.main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

    def _on_auto_close_toggle(self) -> None:
        """Handle auto-close mode toggle."""
        self.auto_close_mode = self.auto_close_var.get()
        status = "enabled" if self.auto_close_mode else "disabled"
        self.update_status(f"Auto-close mode {status}")

    def open_all_zlides(self) -> None:
        """Open all zlides in the list."""
        if not self.zlides:
            messagebox.showinfo("No Zlides", "No zlides to open")
            return
        
        count = len(self.zlides)
        if count > 5:
            if not messagebox.askyesno(
                "Open All Zlides",
                f"This will open {count} items. Continue?"
            ):
                return
        
        for zlide in self.zlides:
            self._open_zlide_without_tracking(zlide)
        
        self.update_status(f"Opened {count} zlides")

    def open_selected_zlides(self) -> None:
        """Open only the selected zlides."""
        selection = self.zlide_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select zlides to open")
            return
        
        count = len(selection)
        for idx in selection:
            zlide = self.zlides[idx]
            self._open_zlide_without_tracking(zlide)
        
        self.update_status(f"Opened {count} selected zlides")

    def _open_zlide_without_tracking(self, zlide: Zlide) -> None:
        """Open a zlide and track the process for Close All functionality."""
        proc: Optional[subprocess.Popen] = None
        try:
            if zlide.type == ZlideType.BROWSER.value:
                # Try to get a trackable browser process
                proc = PlatformHelper.open_browser_window(zlide.data)
            elif zlide.type == ZlideType.APP.value:
                proc = PlatformHelper.open_app(zlide.data)
            elif zlide.type == ZlideType.FILE.value:
                proc = PlatformHelper.open_file(zlide.data)
            
            # Track the process if we got one
            if proc is not None:
                self.opened_processes.append(proc)
        except Exception as e:
            print(f"Error opening {zlide.title}: {e}")

    def new_zlideshow(self) -> None:
        """Create a new empty zlideshow."""
        if not self.zlides:
            # Nothing to clear
            return
            
        if messagebox.askyesno("New Zlideshow", "Clear current zlides?"):
            self.zlides = []
            self.current_file = None
            self.current_zlide_index = -1
            self.refresh_zlide_list()
            self.update_status("New zlideshow created")

    def add_browser_zlide(self) -> None:
        """Add a new browser (URL) zlide."""
        url = simpledialog.askstring("Add Browser Zlide", "Enter URL:")
        if url:
            # Add https:// if no protocol specified
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            title = simpledialog.askstring(
                "Zlide Title", "Enter title:", initialvalue=url[:50]
            )
            if title:
                zlide = Zlide(ZlideType.BROWSER.value, title, url)
                self.zlides.append(zlide)
                self.refresh_zlide_list()
                self.update_status(f"Added browser zlide: {title}")

    def add_file_zlide(self) -> None:
        """Add a new file zlide."""
        filepath = filedialog.askopenfilename(title="Select File")
        if filepath:
            filename = Path(filepath).name
            title = simpledialog.askstring(
                "Zlide Title", "Enter title:", initialvalue=filename
            )
            if title:
                zlide = Zlide(ZlideType.FILE.value, title, filepath)
                self.zlides.append(zlide)
                self.refresh_zlide_list()
                self.update_status(f"Added file zlide: {title}")

    def add_app_zlide(self) -> None:
        """Add a desktop application or shortcut as a zlide."""
        filepath = filedialog.askopenfilename(
            title="Select Application or Shortcut",
            filetypes=[
                ("All Application Files", "*.exe;*.lnk;*.app"),
                ("Windows Executables", "*.exe"),
                ("Windows Shortcuts", "*.lnk"),
                ("macOS Applications", "*.app"),
                ("All Files", "*.*")
            ]
        )
        if filepath:
            filename = Path(filepath).name
            # Remove .lnk extension from display name for shortcuts
            display_name = filename.replace('.lnk', '').replace('.exe', '')
            
            title = simpledialog.askstring(
                "Zlide Title", "Enter title:", initialvalue=display_name
            )
            if title:
                zlide = Zlide(ZlideType.APP.value, title, filepath)
                self.zlides.append(zlide)
                self.refresh_zlide_list()
                self.update_status(f"Added app zlide: {title}")

    def edit_zlide(self) -> None:
        """Edit the currently selected zlide's title."""
        selection = self.zlide_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a zlide to edit")
            return

        idx = selection[0]
        zlide = self.zlides[idx]

        new_title = simpledialog.askstring(
            "Edit Zlide", "Enter new title:", initialvalue=zlide.title
        )
        if new_title:
            zlide.title = new_title
            self.refresh_zlide_list()
            self.update_status(f"Updated zlide: {new_title}")

    def delete_zlide(self) -> None:
        """Delete the currently selected zlide(s)."""
        selection = self.zlide_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a zlide to delete")
            return

        count = len(selection)
        msg = f"Delete {count} zlide(s)?" if count > 1 else "Delete this zlide?"
        
        if messagebox.askyesno("Delete Zlide", msg):
            # Delete in reverse order to maintain indices
            for idx in reversed(selection):
                del self.zlides[idx]
            self.refresh_zlide_list()
            self.update_status(f"Deleted {count} zlide(s)")

    def move_up(self) -> None:
        """Move the selected zlide up in the list."""
        selection = self.zlide_listbox.curselection()
        if not selection or selection[0] == 0:
            return

        idx = selection[0]
        self.zlides[idx], self.zlides[idx - 1] = self.zlides[idx - 1], self.zlides[idx]
        self.refresh_zlide_list()
        self.zlide_listbox.selection_set(idx - 1)

    def move_down(self) -> None:
        """Move the selected zlide down in the list."""
        selection = self.zlide_listbox.curselection()
        if not selection or selection[0] == len(self.zlides) - 1:
            return

        idx = selection[0]
        self.zlides[idx], self.zlides[idx + 1] = self.zlides[idx + 1], self.zlides[idx]
        self.refresh_zlide_list()
        self.zlide_listbox.selection_set(idx + 1)

    def _get_zlide_icon(self, zlide_type: str) -> str:
        """Get the icon for a zlide type."""
        icons = {
            ZlideType.BROWSER.value: "🌐",
            ZlideType.APP.value: "💻",
            ZlideType.FILE.value: "📄",
        }
        return icons.get(zlide_type, "📄")

    def refresh_zlide_list(self) -> None:
        """Refresh the zlide listbox display."""
        self.zlide_listbox.delete(0, tk.END)
        for i, zlide in enumerate(self.zlides):
            icon = self._get_zlide_icon(zlide.type)
            
            # Highlight current zlide in presentation mode
            prefix = "▶ " if (self.presentation_mode and i == self.current_zlide_index) else "  "
            
            self.zlide_listbox.insert(tk.END, f"{prefix}{i + 1}. {icon} {zlide.title}")
            
            # Highlight current zlide with different background
            if self.presentation_mode and i == self.current_zlide_index:
                self.zlide_listbox.itemconfig(i, background=Colors.CURRENT_ZLIDE_BG)

    def on_zlide_double_click(self, event: tk.Event) -> None:
        """Handle double-click on zlide - open it directly or navigate to it."""
        selection = self.zlide_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        
        if self.presentation_mode:
            # Navigate to this zlide
            self.go_to_zlide(idx)
        else:
            # Just open this zlide
            self._open_zlide_without_tracking(self.zlides[idx])

    def save_zlideshow(self) -> None:
        """Save the current zlideshow to a file."""
        if not self.zlides:
            messagebox.showwarning("No Zlides", "No zlides to save")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".zlides",
            filetypes=[("Zlider Files", "*.zlides"), ("All Files", "*.*")],
        )

        if filepath:
            data = {
                "version": "1.1",
                "settings": {
                    "auto_close_mode": self.auto_close_mode
                },
                "zlides": [z.to_dict() for z in self.zlides]
            }

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            self.current_file = filepath
            self._update_window_title()
            self.update_status(f"Saved: {Path(filepath).name}")

    def open_zlideshow(self) -> None:
        """Open a zlideshow from a file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("Zlider Files", "*.zlides"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                self.zlides = [Zlide.from_dict(z) for z in data["zlides"]]
                self.current_file = filepath
                
                # Load settings if present (version 1.1+)
                if "settings" in data:
                    settings = data["settings"]
                    self.auto_close_mode = settings.get("auto_close_mode", False)
                    self.auto_close_var.set(self.auto_close_mode)
                
                self.refresh_zlide_list()
                self._update_window_title()
                self.update_status(f"Loaded: {Path(filepath).name} ({len(self.zlides)} zlides)")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def start_presentation(self) -> None:
        """Start the presentation mode."""
        if not self.zlides:
            messagebox.showwarning("No Zlides", "No zlides in presentation")
            return
        
        # If already in compact mode, we need to switch to presentation compact view
        was_compact = self.compact_mode
        if was_compact:
            # Destroy the editing compact frame first
            if hasattr(self, 'compact_frame'):
                self.compact_frame.destroy()
            self.compact_mode = False

        self.presentation_mode = True
        self.current_zlide_index = 0
        self.current_process = None
        
        # Start the timer
        self.presentation_start_time = datetime.now()
        self._update_timer()
        
        # Switch UI to presentation mode
        self._switch_to_presentation_mode()
        
        # If we were in compact mode, switch to presentation compact view
        if was_compact:
            self.compact_mode = True
            self._enter_compact_mode_presentation()
        
        # Open first zlide
        self._open_zlide_with_tracking(self.zlides[0])
        self._update_zlide_navigation()

    def _switch_to_presentation_mode(self) -> None:
        """Switch UI to presentation mode."""
        # Clear and rebuild toolbar for presentation
        for widget in self.pres_controls_frame.winfo_children():
            widget.destroy()
        
        # Timer label
        self.timer_label = ttk.Label(
            self.pres_controls_frame,
            text="00:00",
            font=('Arial', 10),
            foreground=Colors.TIMER_LABEL_FG
        )
        self.timer_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Separator(self.pres_controls_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=5, fill=tk.Y
        )
        
        # Auto-close indicator
        self.auto_close_indicator = ttk.Label(
            self.pres_controls_frame,
            text="🔄",
            font=('Arial', 10),
            foreground=Colors.AUTO_CLOSE_ON if self.auto_close_mode else Colors.AUTO_CLOSE_OFF
        )
        self.auto_close_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        # Add presentation controls
        ttk.Button(
            self.pres_controls_frame,
            text="◀◀",
            command=lambda: self.go_to_zlide(0),
            width=5
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            self.pres_controls_frame,
            text="◀ Prev",
            command=self.previous_zlide,
            width=8
        ).pack(side=tk.LEFT, padx=1)
        
        self.current_zlide_label = ttk.Label(
            self.pres_controls_frame,
            text="1/1",
            font=('Arial', 10, 'bold'),
            foreground=Colors.COUNTER_LABEL_FG
        )
        self.current_zlide_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            self.pres_controls_frame,
            text="Next ▶",
            command=self.next_zlide,
            width=8
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            self.pres_controls_frame,
            text="▶▶",
            command=lambda: self.go_to_zlide(len(self.zlides) - 1),
            width=5
        ).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(self.pres_controls_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )
        
        # Compact/Expand toggle button
        self.compact_btn = ttk.Button(
            self.pres_controls_frame,
            text="▼ Mini",
            command=self.toggle_compact_mode,
            width=8
        )
        self.compact_btn.pack(side=tk.LEFT, padx=1)
        
        ttk.Button(
            self.pres_controls_frame,
            text="■ End",
            command=self.end_presentation,
            width=8
        ).pack(side=tk.LEFT, padx=1)
        
        # Make window stay on top
        self.root.attributes('-topmost', True)
        
        # Update the label
        self._update_presentation_label()

    def _update_presentation_label(self) -> None:
        """Update the current zlide counter in presentation mode."""
        if self._widget_exists('current_zlide_label'):
            self.current_zlide_label.config(
                text=f"{self.current_zlide_index + 1}/{len(self.zlides)}"
            )
        self._update_compact_labels()
    
    def _widget_exists(self, attr_name: str) -> bool:
        """Check if a widget attribute exists and the widget is still valid."""
        if not hasattr(self, attr_name):
            return False
        widget = getattr(self, attr_name)
        try:
            return widget.winfo_exists()
        except tk.TclError:
            return False
    
    def _update_compact_labels(self) -> None:
        """Update all labels in compact mode."""
        if not self.compact_mode:
            return
        
        # Only update presentation-mode compact labels
        if not self.presentation_mode:
            return
            
        # Update counter
        if self._widget_exists('compact_zlide_label'):
            self.compact_zlide_label.config(
                text=f"{self.current_zlide_index + 1}/{len(self.zlides)}"
            )
        
        # Update previous zlide
        if self._widget_exists('compact_prev_label'):
            prev_text = ""
            if self.current_zlide_index > 0:
                prev_text = f"◀ {self.zlides[self.current_zlide_index - 1].title[:30]}"
            self.compact_prev_label.config(text=prev_text)
        
        # Update current zlide
        if self._widget_exists('compact_current_label'):
            current_text = self.zlides[self.current_zlide_index].title[:40]
            self.compact_current_label.config(text=current_text)
        
        # Update next zlide
        if self._widget_exists('compact_next_label'):
            next_text = ""
            if self.current_zlide_index < len(self.zlides) - 1:
                next_text = f"{self.zlides[self.current_zlide_index + 1].title[:30]} ▶"
            self.compact_next_label.config(text=next_text)

    def end_presentation(self) -> None:
        """End presentation mode and return to editing mode."""
        self.presentation_mode = False
        self.current_zlide_index = -1
        
        # Close any tracked process
        if self.auto_close_mode and self.current_process:
            PlatformHelper.close_process(self.current_process)
            self.current_process = None
        
        # Stop the timer
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.presentation_start_time = None
        
        # If in compact mode, restore normal view first
        if self.compact_mode:
            self.compact_mode = False
            if hasattr(self, 'compact_frame'):
                self.compact_frame.destroy()
            self.main_frame.grid()
            self.root.geometry(self.normal_geometry)
        
        # Restore toolbar
        for widget in self.pres_controls_frame.winfo_children():
            widget.destroy()
        
        ttk.Button(
            self.pres_controls_frame,
            text="▶ Start",
            command=self.start_presentation,
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Remove always on top
        self.root.attributes('-topmost', False)
        
        # Restore normal background
        self.root.configure(bg=PlatformHelper.get_default_bg())
        
        self.refresh_zlide_list()
        self.update_status("Presentation ended")
    
    def _format_elapsed_time(self) -> str:
        """Format elapsed presentation time as MM:SS."""
        if not self.presentation_start_time:
            return "00:00"
        elapsed = datetime.now() - self.presentation_start_time
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _update_timer(self) -> None:
        """Update the presentation timer."""
        if self.presentation_mode and self.presentation_start_time:
            time_str = self._format_elapsed_time()
            
            # Update main timer label
            if self._widget_exists('timer_label'):
                self.timer_label.config(text=time_str)
            
            # Update compact timer label
            if self._widget_exists('compact_timer_label'):
                self.compact_timer_label.config(text=time_str)
            
            # Schedule next update
            self.timer_id = self.root.after(1000, self._update_timer)

    def _update_zlide_navigation(self) -> None:
        """Common logic after navigating to a zlide."""
        self.refresh_zlide_list()
        self._update_presentation_label()
        current = self.zlides[self.current_zlide_index]
        auto_close_status = " [Auto-close ON]" if self.auto_close_mode else ""
        self.update_status(
            f"Presenting: {current.title} ({self.current_zlide_index + 1}/{len(self.zlides)}){auto_close_status}"
        )

    def _close_previous_zlide(self) -> None:
        """Close the previously opened zlide if auto-close is enabled."""
        if self.auto_close_mode and self.current_process:
            PlatformHelper.close_process(self.current_process)
            self.current_process = None

    def _open_zlide_with_tracking(self, zlide: Zlide) -> None:
        """Open a zlide and track its process for auto-close functionality."""
        try:
            proc = None
            
            if zlide.type == ZlideType.BROWSER.value:
                print(f"Opening browser zlide: {zlide.title}")
                if self.auto_close_mode:
                    # Open in new window for better tracking
                    proc = PlatformHelper.open_browser_window(zlide.data)
                else:
                    webbrowser.open(zlide.data)
                
            elif zlide.type == ZlideType.APP.value:
                print(f"Opening application zlide: {zlide.title}")
                proc = PlatformHelper.open_app(zlide.data)
                    
            elif zlide.type == ZlideType.FILE.value:
                print(f"Opening file zlide: {zlide.title}")
                proc = PlatformHelper.open_file(zlide.data)
            
            # Store the process for potential auto-close
            if self.auto_close_mode and proc:
                self.current_process = proc
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {zlide.title}: {str(e)}")
            print(f"Error opening zlide: {e}")

    def next_zlide(self) -> None:
        """Navigate to next zlide."""
        if not self.presentation_mode:
            return
            
        if self.current_zlide_index < len(self.zlides) - 1:
            # Close previous zlide if auto-close is enabled
            self._close_previous_zlide()
            
            self.current_zlide_index += 1
            self._open_zlide_with_tracking(self.zlides[self.current_zlide_index])
            self._update_zlide_navigation()

    def previous_zlide(self) -> None:
        """Navigate to previous zlide."""
        if not self.presentation_mode:
            return
            
        if self.current_zlide_index > 0:
            # Close current zlide if auto-close is enabled
            self._close_previous_zlide()
            
            self.current_zlide_index -= 1
            self._open_zlide_with_tracking(self.zlides[self.current_zlide_index])
            self._update_zlide_navigation()

    def go_to_zlide(self, index: int) -> None:
        """Jump directly to a specific zlide index."""
        if not self.presentation_mode or index < 0 or index >= len(self.zlides):
            return
        
        # Close current zlide if auto-close is enabled
        self._close_previous_zlide()
        
        self.current_zlide_index = index
        self._open_zlide_with_tracking(self.zlides[index])
        self._update_zlide_navigation()

    def update_status(self, message: str) -> None:
        """Update the status bar."""
        self.status_bar.config(text=message)
        print(f"Status: {message}")

    def _update_window_title(self) -> None:
        """Update the window title and list frame with current file name."""
        if self.current_file:
            file_name = Path(self.current_file).stem
            self.root.title(f"Zlider - {file_name}")
            # Update list frame header
            if self._widget_exists('list_frame'):
                self.list_frame.config(text=f"Zlideshow: {file_name} ({len(self.zlides)} zlides)")
        else:
            self.root.title("Zlider - Presentation Tool")
            if self._widget_exists('list_frame'):
                self.list_frame.config(text="Zlideshow")

    def toggle_compact_mode(self) -> None:
        """Toggle between compact and normal view (works in both editing and presentation modes)."""
        self.compact_mode = not self.compact_mode
        
        if self.compact_mode:
            if self.presentation_mode:
                self._enter_compact_mode_presentation()
            else:
                self._enter_compact_mode_editing()
            # Update button to show "Full"
            if self._widget_exists('mini_btn'):
                self.mini_btn.config(text="▲ Full")
        else:
            self._exit_compact_mode()
        
        if self.presentation_mode:
            self._update_compact_labels()

    def _create_compact_button(self, parent: tk.Frame, text: str, command: Callable, 
                                width: int = 4, is_end_btn: bool = False) -> tk.Button:
        """Create a styled button for compact mode."""
        # Common button properties
        btn_kwargs = {
            'text': text,
            'command': command,
            'width': width,
            'fg': 'white',
            'activeforeground': 'white',
            'relief': tk.RAISED,
            'bd': 1,
        }
        
        # Set colors based on button type
        if is_end_btn:
            btn_kwargs['bg'] = Colors.END_BTN
            btn_kwargs['activebackground'] = Colors.END_BTN_ACTIVE
        else:
            btn_kwargs['bg'] = Colors.DARK_BTN
            btn_kwargs['activebackground'] = Colors.DARK_BTN_ACTIVE
        
        return tk.Button(parent, **btn_kwargs)

    def _enter_compact_mode_editing(self) -> None:
        """Switch to compact editing view (before presentation)."""
        # Save current geometry
        self.normal_geometry = self.root.geometry()
        
        # Hide main frame
        self.main_frame.grid_remove()
        
        # Create compact frame with dark theme
        self.compact_frame = ttk.Frame(self.root, padding="8")
        self.compact_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure dark background
        self.root.configure(bg=Colors.DARK_BG)
        
        # Create custom dark style
        style = ttk.Style()
        style.configure('Dark.TFrame', background=Colors.DARK_BG)
        style.configure('Dark.TLabel', background=Colors.DARK_BG, foreground='white')
        self.compact_frame.configure(style='Dark.TFrame')
        
        # Top row: Title and zlide count
        info_frame = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        info_frame.pack(fill=tk.X, pady=(0, 8))
        
        # File name or "Untitled"
        file_name = Path(self.current_file).stem if self.current_file else "Untitled"
        self.compact_title_label = tk.Label(
            info_frame,
            text=f"📋 {file_name}",
            font=('Arial', 10, 'bold'),
            fg=Colors.HIGHLIGHT_BLUE,
            bg=Colors.DARK_BG
        )
        self.compact_title_label.pack(side=tk.LEFT, padx=5)
        
        # Zlide count
        count_text = f"{len(self.zlides)} zlides" if self.zlides else "No zlides"
        self.compact_count_label = tk.Label(
            info_frame,
            text=count_text,
            font=('Arial', 9),
            fg=Colors.MUTED_TEXT,
            bg=Colors.DARK_BG
        )
        self.compact_count_label.pack(side=tk.RIGHT, padx=5)
        
        # Bottom row: Action buttons
        nav_frame = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        nav_frame.pack()
        
        # Open All button
        self._create_compact_button(
            nav_frame, "🚀 Open All", self.open_all_zlides, width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Open Selected button
        self._create_compact_button(
            nav_frame, "📂 Selected", self.open_selected_zlides, width=10
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(nav_frame, width=2, bg=Colors.SEPARATOR).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        # Start Presentation button
        self._create_compact_button(
            nav_frame, "▶ Start", self.start_presentation, width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # Separator
        tk.Frame(nav_frame, width=2, bg=Colors.SEPARATOR).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        # Expand button
        self._create_compact_button(
            nav_frame, "▲ Full", self.toggle_compact_mode, width=6
        ).pack(side=tk.LEFT, padx=2)
        
        # Resize window to compact size
        self.root.geometry("550x80")
        
        # Update main toolbar button
        if hasattr(self, 'mini_btn'):
            self.mini_btn.config(text="▲ Full")

    def _enter_compact_mode_presentation(self) -> None:
        """Switch to compact presentation view."""
        # Only save geometry if coming from full mode (not from editing compact)
        # Check if we're at a reasonable full-mode size
        current_geo = self.root.geometry()
        width = int(current_geo.split('x')[0])
        if width > 600:  # Only save if we're in full mode
            self.normal_geometry = current_geo
        
        # Hide main frame
        self.main_frame.grid_remove()
        
        # Create compact frame with dark theme
        self.compact_frame = ttk.Frame(self.root, padding="8")
        self.compact_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure dark background
        self.root.configure(bg=Colors.DARK_BG)
        
        # Create custom dark style
        style = ttk.Style()
        style.configure('Dark.TFrame', background=Colors.DARK_BG)
        style.configure('Dark.TLabel', background=Colors.DARK_BG, foreground='white')
        self.compact_frame.configure(style='Dark.TFrame')
        
        # Top row: Previous/Current/Next zlide names
        info_frame = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        info_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Previous zlide (left-aligned)
        prev_text = ""
        if self.current_zlide_index > 0:
            prev_text = f"◀ {self.zlides[self.current_zlide_index - 1].title[:30]}"
        self.compact_prev_label = tk.Label(
            info_frame,
            text=prev_text,
            font=('Arial', 8),
            fg=Colors.MUTED_TEXT,
            bg=Colors.DARK_BG,
            anchor=tk.W
        )
        self.compact_prev_label.pack(side=tk.LEFT, padx=5)
        
        # Next zlide (right-aligned)
        next_text = ""
        if self.current_zlide_index < len(self.zlides) - 1:
            next_text = f"{self.zlides[self.current_zlide_index + 1].title[:30]} ▶"
        self.compact_next_label = tk.Label(
            info_frame,
            text=next_text,
            font=('Arial', 8),
            fg=Colors.MUTED_TEXT,
            bg=Colors.DARK_BG,
            anchor=tk.E
        )
        self.compact_next_label.pack(side=tk.RIGHT, padx=5)
        
        # Current zlide (center)
        current_text = self.zlides[self.current_zlide_index].title[:40]
        self.compact_current_label = tk.Label(
            info_frame,
            text=current_text,
            font=('Arial', 10, 'bold'),
            fg=Colors.HIGHLIGHT_BLUE,
            bg=Colors.DARK_BG
        )
        self.compact_current_label.pack(expand=True)
        
        # Bottom row: Navigation controls
        nav_frame = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        nav_frame.pack()
        
        # Timer at the start
        self.compact_timer_label = tk.Label(
            nav_frame,
            text=self._format_elapsed_time(),
            font=('Arial', 10, 'bold'),
            fg=Colors.TIMER_GREEN,
            bg=Colors.DARK_BG,
            width=6
        )
        self.compact_timer_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Auto-close indicator in compact mode
        auto_close_color = Colors.AUTO_CLOSE_ON if self.auto_close_mode else Colors.AUTO_CLOSE_OFF
        self.compact_auto_close_label = tk.Label(
            nav_frame,
            text="🔄",
            font=('Arial', 10),
            fg=auto_close_color,
            bg=Colors.DARK_BG
        )
        self.compact_auto_close_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Separator
        tk.Frame(nav_frame, width=2, bg=Colors.SEPARATOR).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # Navigation buttons
        self._create_compact_button(
            nav_frame, "◀◀", lambda: self.go_to_zlide(0)
        ).pack(side=tk.LEFT, padx=1)
        
        self._create_compact_button(
            nav_frame, "◀", self.previous_zlide
        ).pack(side=tk.LEFT, padx=1)
        
        self.compact_zlide_label = tk.Label(
            nav_frame,
            text=f"{self.current_zlide_index + 1}/{len(self.zlides)}",
            font=('Arial', 12, 'bold'),
            fg=Colors.HIGHLIGHT_BLUE,
            bg=Colors.DARK_BG,
            width=8
        )
        self.compact_zlide_label.pack(side=tk.LEFT, padx=5)
        
        self._create_compact_button(
            nav_frame, "▶", self.next_zlide
        ).pack(side=tk.LEFT, padx=1)
        
        self._create_compact_button(
            nav_frame, "▶▶", lambda: self.go_to_zlide(len(self.zlides) - 1)
        ).pack(side=tk.LEFT, padx=1)
        
        # Separator
        tk.Frame(nav_frame, width=2, bg=Colors.SEPARATOR).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        self._create_compact_button(
            nav_frame, "▲ Full", self.toggle_compact_mode, width=6
        ).pack(side=tk.LEFT, padx=1)
        
        self._create_compact_button(
            nav_frame, "■ End", self.end_presentation, width=6, is_end_btn=True
        ).pack(side=tk.LEFT, padx=1)
        
        # Resize window to compact size
        self.root.geometry("700x90")
        
        # Update button text in main toolbar (if visible)
        if hasattr(self, 'compact_btn'):
            self.compact_btn.config(text="▲ Full")

    def _exit_compact_mode(self) -> None:
        """Exit compact mode and restore normal view."""
        if hasattr(self, 'compact_frame'):
            self.compact_frame.destroy()
        
        # Restore normal background
        self.root.configure(bg=PlatformHelper.get_default_bg())
        
        self.main_frame.grid()
        
        # Restore original geometry
        self.root.geometry(self.normal_geometry)
        
        # Update button text
        if self._widget_exists('compact_btn'):
            self.compact_btn.config(text="▼ Mini")
        if self._widget_exists('mini_btn'):
            self.mini_btn.config(text="▼ Mini")

    def close_all_zlides(self) -> None:
        """Close all tracked opened processes."""
        closed_count = 0
        
        # Close current process
        if self.current_process:
            PlatformHelper.close_process(self.current_process)
            self.current_process = None
            closed_count += 1
        
        # Close all tracked processes
        for proc in self.opened_processes:
            try:
                if proc.poll() is None:  # Process is still running
                    PlatformHelper.close_process(proc)
                    closed_count += 1
            except Exception:
                pass
        
        self.opened_processes.clear()
        
        if closed_count > 0:
            self.update_status(f"Closed {closed_count} process(es)")
        else:
            self.update_status("No tracked processes to close")


def main() -> None:
    """Application entry point."""
    root = tk.Tk()
    ZliderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()