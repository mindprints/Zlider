"""
Zlider Workspace Edition - A presentation tool with folder-based organization.
No more New/Open/Save - everything auto-saves to a single workspace.
"""

import json
import os
import platform
import subprocess
import tkinter as tk
import webbrowser
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Optional, List
import shutil


class ZlideType:
    """Types of zlides."""
    BROWSER = "browser"
    FILE = "file"
    APP = "app"


class Colors:
    """UI colors."""
    # Light theme
    LIGHT_BG = "#f6f1ea"
    TOOLBAR_BG = "#efe7dc"
    PANEL_BG = "#ffffff"
    TEXT_MAIN = "#2c2a27"
    TEXT_MUTED = "#6f6a63"
    ACCENT = "#c46b3c"
    LIST_BG = "#fffaf3"
    LIST_SELECT_BG = "#e7d2c2"
    CURRENT_ZLIDE_BG = "#dfe9f7"
    
    # Dark theme
    DARK_UI_BG = "#1c1c1c"
    DARK_UI_TOOLBAR = "#242424"
    DARK_UI_PANEL = "#2a2a2a"
    DARK_UI_TEXT = "#e6e1da"
    DARK_UI_MUTED = "#a29c92"
    DARK_UI_LIST_BG = "#222222"
    DARK_UI_LIST_SELECT_BG = "#3b2f27"
    DARK_UI_LIST_SELECT_FG = "#f2eadf"
    DARK_UI_CURRENT_BG = "#2a3a4a"
    
    # Dark compact mode
    DARK_BG = "#1f1f1f"
    DARK_BTN = "#2b2b2b"
    DARK_BTN_ACTIVE = "#3a3a3a"
    HIGHLIGHT_BLUE = "#6bb9ff"
    TIMER_GREEN = "#6fe389"
    MUTED_TEXT = "#9a9a9a"
    SEPARATOR = "#444444"
    END_BTN = "#8b0000"
    END_BTN_ACTIVE = "#a00000"
    AUTO_CLOSE_ON = "#ff6b6b"
    AUTO_CLOSE_OFF = "#666666"


@dataclass
class Zlide:
    """A single zlide."""
    type: str
    title: str
    data: str
    id: int = field(default_factory=lambda: id(object()))

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Zlide":
        return Zlide(d["type"], d["title"], d["data"], d.get("id", id(object())))


@dataclass
class Presentation:
    """A presentation (collection of zlides)."""
    name: str
    zlides: List[Zlide] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    _id: int = field(default_factory=lambda: id(object()))  # Unique ID for hashing
    
    def __hash__(self):
        return self._id
    
    def __eq__(self, other):
        if isinstance(other, Presentation):
            return self._id == other._id
        return False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "zlides": [z.to_dict() for z in self.zlides],
            "settings": self.settings
        }
    
    @staticmethod
    def from_dict(d: dict) -> "Presentation":
        return Presentation(
            name=d["name"],
            zlides=[Zlide.from_dict(z) for z in d.get("zlides", [])],
            settings=d.get("settings", {})
        )


@dataclass
class Folder:
    """A folder containing presentations."""
    name: str
    presentations: List[Presentation] = field(default_factory=list)
    _id: int = field(default_factory=lambda: id(object()))  # Unique ID for hashing
    
    def __hash__(self):
        return self._id
    
    def __eq__(self, other):
        if isinstance(other, Folder):
            return self._id == other._id
        return False
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "presentations": [p.to_dict() for p in self.presentations]
        }
    
    @staticmethod
    def from_dict(d: dict) -> "Folder":
        return Folder(
            name=d["name"],
            presentations=[Presentation.from_dict(p) for p in d.get("presentations", [])]
        )


class PlatformHelper:
    """Cross-platform utilities."""
    
    @staticmethod
    def open_browser_window(url: str) -> Optional[subprocess.Popen]:
        """Open URL in new browser window."""
        browser = shutil.which("chrome") or shutil.which("firefox") or shutil.which("msedge")
        if browser:
            try:
                return subprocess.Popen([browser, "--new-window", url])  # noqa: S603
            except Exception:
                pass
        webbrowser.open_new(url)
        return None
    
    @staticmethod
    def open_file(filepath: str) -> Optional[subprocess.Popen]:
        """Open file with default application."""
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(filepath)
            elif system == "Darwin":
                return subprocess.Popen(["open", filepath])  # noqa: S603, S607
            else:
                return subprocess.Popen(["xdg-open", filepath])  # noqa: S603, S607
        except Exception as e:
            print(f"Error opening file: {e}")
        return None
    
    @staticmethod
    def open_app(filepath: str) -> Optional[subprocess.Popen]:
        """Launch application."""
        system = platform.system()
        try:
            if system == "Windows":
                if filepath.lower().endswith('.lnk'):
                    os.startfile(filepath)
                    return None
                return subprocess.Popen([filepath])  # noqa: S603
            elif system == "Darwin":
                return subprocess.Popen(["open", filepath])  # noqa: S603, S607
            else:
                return subprocess.Popen([filepath])  # noqa: S603
        except Exception as e:
            print(f"Error opening app: {e}")
        return None
    
    @staticmethod
    def close_process(proc: Optional[subprocess.Popen]) -> None:
        """Close a process."""
        if proc:
            try:
                proc.terminate()
                proc.wait(timeout=1)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


class WorkspaceManager:
    """Manages the workspace data and auto-save."""
    
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path
        self.folders: List[Folder] = []
        self.recent: List[str] = []  # Recent presentation names
        self.settings: dict = {"dark_mode": False, "auto_close_mode": False}
        self._load_workspace()
    
    def _load_workspace(self) -> None:
        """Load workspace from disk."""
        if not self.workspace_path.exists():
            # Create default workspace
            self.folders = [
                Folder("My Presentations"),
                Folder("Work"),
                Folder("Personal")
            ]
            self._save_workspace()
            return
        
        try:
            with open(self.workspace_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.folders = [Folder.from_dict(f) for f in data.get("folders", [])]
            self.recent = data.get("recent", [])
            self.settings = data.get("settings", {})
        except Exception as e:
            print(f"Error loading workspace: {e}")
            self.folders = [Folder("My Presentations")]
    
    def _save_workspace(self) -> None:
        """Auto-save workspace to disk."""
        try:
            data = {
                "version": "2.0",
                "folders": [f.to_dict() for f in self.folders],
                "recent": self.recent,
                "settings": self.settings
            }
            
            # Atomic write
            temp_path = self.workspace_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            temp_path.replace(self.workspace_path)
        except Exception as e:
            print(f"Error saving workspace: {e}")
    
    def save(self) -> None:
        """Explicitly save workspace (calls auto-save)."""
        self._save_workspace()
    
    def add_folder(self, name: str) -> Folder:
        """Add a new folder."""
        folder = Folder(name)
        self.folders.append(folder)
        self._save_workspace()
        return folder
    
    def remove_folder(self, folder: Folder) -> None:
        """Remove a folder."""
        self.folders.remove(folder)
        self._save_workspace()
    
    def find_presentation(self, name: str) -> Optional[tuple[Folder, Presentation]]:
        """Find a presentation by name across all folders."""
        for folder in self.folders:
            for pres in folder.presentations:
                if pres.name == name:
                    return (folder, pres)
        return None
    
    def add_to_recent(self, name: str) -> None:
        """Add presentation to recent list."""
        if name in self.recent:
            self.recent.remove(name)
        self.recent.insert(0, name)
        self.recent = self.recent[:10]  # Keep last 10
        self._save_workspace()


class ZliderWorkspaceApp:
    """Main workspace application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Zlider Workspace")
        self.root.geometry("1100x700")
        
        # Workspace manager
        workspace_path = Path.home() / ".zlider_workspace.json"
        self.workspace = WorkspaceManager(workspace_path)
        
        # Current state
        self.current_folder: Optional[Folder] = None
        self.current_presentation: Optional[Presentation] = None
        self.current_zlide_index: int = -1
        self.presentation_mode: bool = False
        self.compact_mode: bool = False
        self.normal_geometry: str = "1100x700"
        
        # Dark mode
        self.dark_mode: bool = self.workspace.settings.get("dark_mode", False)
        
        # Auto-close tracking
        self.auto_close_mode: bool = self.workspace.settings.get("auto_close_mode", False)
        self.current_process: Optional[subprocess.Popen] = None
        self.opened_processes: List[subprocess.Popen] = []
        
        # Timer
        self.presentation_start_time: Optional[datetime] = None
        self.timer_id: Optional[str] = None
        
        # UI state
        self.folder_nodes: dict = {}  # folder -> tree node id
        
        self._setup_keybindings()
        self._configure_styles()
        self._create_ui()
        self._apply_theme()
        
        # Load first folder by default
        if self.workspace.folders:
            self._select_folder(self.workspace.folders[0])
    
    def _configure_styles(self) -> None:
        """Configure ttk styles."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
    
    def _apply_theme(self) -> None:
        """Apply current theme (light/dark)."""
        style = ttk.Style()
        
        if self.dark_mode:
            bg = Colors.DARK_UI_BG
            fg = Colors.DARK_UI_TEXT
            panel_bg = Colors.DARK_UI_PANEL
            list_bg = Colors.DARK_UI_LIST_BG
            list_select = Colors.DARK_UI_LIST_SELECT_BG
            current_bg = Colors.DARK_UI_CURRENT_BG
        else:
            bg = Colors.LIGHT_BG
            fg = Colors.TEXT_MAIN
            panel_bg = Colors.PANEL_BG
            list_bg = Colors.LIST_BG
            list_select = Colors.LIST_SELECT_BG
            current_bg = Colors.CURRENT_ZLIDE_BG
        
        self.root.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("TLabelframe", background=panel_bg, foreground=fg)
        style.configure("TLabelframe.Label", background=bg, foreground=fg)
        
        # Update listbox if it exists
        if hasattr(self, 'zlide_list'):
            self.zlide_list.configure(
                bg=list_bg,
                fg=fg,
                selectbackground=list_select,
                selectforeground=fg
            )
        
        Colors.CURRENT_ZLIDE_BG = current_bg
    
    def _setup_keybindings(self) -> None:
        """Setup keyboard shortcuts."""
        self.root.bind("<Left>", lambda e: self.previous_zlide())
        self.root.bind("<Right>", lambda e: self.next_zlide())
        self.root.bind("<space>", lambda e: self.next_zlide())
        self.root.bind("<Escape>", lambda e: self.toggle_compact_mode())
    
    def _create_ui(self) -> None:
        """Create the main UI."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Top toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Label(toolbar, text="📂 Zlider Workspace", font=('Arial', 12, 'bold')).pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Navigation controls
        self.nav_frame = ttk.Frame(toolbar)
        ttk.Button(self.nav_frame, text="◀◀", command=lambda: self.go_to_zlide(0), width=4).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.nav_frame, text="◀", command=self.previous_zlide, width=4).pack(side=tk.LEFT, padx=1)
        
        self.zlide_counter = ttk.Label(self.nav_frame, text="0/0", font=('Arial', 10, 'bold'))
        self.zlide_counter.pack(side=tk.LEFT, padx=8)
        
        ttk.Button(self.nav_frame, text="▶", command=self.next_zlide, width=4).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.nav_frame, text="▶▶", command=lambda: self.go_to_zlide(999), width=4).pack(side=tk.LEFT, padx=1)
        
        self.nav_frame.pack(side=tk.LEFT)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        self.mini_btn = ttk.Button(toolbar, text="▼ Mini", command=self.toggle_compact_mode, width=8)
        self.mini_btn.pack(side=tk.LEFT)
        
        # Left sidebar: Folders and presentations
        sidebar = ttk.Frame(main_frame)
        sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        
        # Folders tree
        tree_frame = ttk.LabelFrame(sidebar, text="Folders & Presentations", padding="5")
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.folder_tree = ttk.Treeview(tree_frame, yscrollcommand=tree_scroll.set, selectmode='browse')
        self.folder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.folder_tree.yview)
        
        self.folder_tree.bind('<<TreeviewSelect>>', self._on_tree_select)
        self.folder_tree.bind('<Double-Button-1>', self._on_tree_double_click)
        
        # Folder management buttons
        folder_btns = ttk.Frame(sidebar)
        folder_btns.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(folder_btns, text="+ Folder", command=self._add_folder, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(folder_btns, text="+ Presentation", command=self._add_presentation, width=12).pack(side=tk.LEFT, padx=2)
        
        # Right panel: Current presentation
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=1, column=1, sticky="nsew")
        
        # Presentation title
        title_frame = ttk.Frame(right_panel)
        title_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.pres_title_label = ttk.Label(title_frame, text="No presentation selected", font=('Arial', 11, 'bold'))
        self.pres_title_label.pack(side=tk.LEFT)
        
        ttk.Button(title_frame, text="✏️", command=self._rename_presentation, width=3).pack(side=tk.RIGHT, padx=2)
        ttk.Button(title_frame, text="🗑️", command=self._delete_presentation, width=3).pack(side=tk.RIGHT, padx=2)
        
        # Zlides list
        list_frame = ttk.LabelFrame(right_panel, text="Zlides", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.zlide_list = tk.Listbox(list_frame, yscrollcommand=scroll.set, font=('Arial', 10), selectmode=tk.EXTENDED)
        self.zlide_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.zlide_list.yview)
        
        self.zlide_list.bind('<Double-Button-1>', self._on_zlide_double_click)
        
        # Zlide controls
        controls = ttk.Frame(right_panel)
        controls.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(controls, text="➕ Browser", command=self._add_browser_zlide, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="➕ File", command=self._add_file_zlide, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="➕ App", command=self._add_app_zlide, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="🗑️ Delete", command=self._delete_zlide, width=12).pack(side=tk.LEFT, padx=2)
        
        # Settings section
        settings_frame = ttk.LabelFrame(right_panel, text="Settings", padding="5")
        settings_frame.pack(fill=tk.X, pady=(5, 0))
        
        settings_inner = ttk.Frame(settings_frame)
        settings_inner.pack(fill=tk.X)
        
        # Auto-close checkbox
        self.auto_close_var = tk.BooleanVar(value=self.auto_close_mode)
        ttk.Checkbutton(
            settings_inner,
            text="🔄 Auto-close previous",
            variable=self.auto_close_var,
            command=self._on_auto_close_toggle
        ).pack(side=tk.LEFT, padx=5)
        
        # Dark mode checkbox
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        ttk.Checkbutton(
            settings_inner,
            text="🌙 Dark mode",
            variable=self.dark_mode_var,
            command=self._on_dark_mode_toggle
        ).pack(side=tk.LEFT, padx=5)
        
        # Quick Launch section
        launch_frame = ttk.LabelFrame(right_panel, text="Quick Launch", padding="5")
        launch_frame.pack(fill=tk.X, pady=(5, 0))
        
        launch_btns = ttk.Frame(launch_frame)
        launch_btns.pack()
        
        ttk.Button(launch_btns, text="🚀 Open All", command=self._open_all_zlides, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(launch_btns, text="📂 Open Selected", command=self._open_selected_zlides, width=14).pack(side=tk.LEFT, padx=2)
        ttk.Button(launch_btns, text="❌ Close All Opened", command=self._close_all_zlides, width=16).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status = ttk.Label(main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        # Grid configuration
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=2)
        main_frame.rowconfigure(1, weight=1)
        
        # Populate tree
        self._refresh_folder_tree()
    
    def _on_auto_close_toggle(self) -> None:
        """Handle auto-close toggle."""
        self.auto_close_mode = self.auto_close_var.get()
        self.workspace.settings["auto_close_mode"] = self.auto_close_mode
        self.workspace.save()
        status = "enabled" if self.auto_close_mode else "disabled"
        self.status.config(text=f"Auto-close mode {status}")
    
    def _on_dark_mode_toggle(self) -> None:
        """Handle dark mode toggle."""
        self.dark_mode = self.dark_mode_var.get()
        self.workspace.settings["dark_mode"] = self.dark_mode
        self.workspace.save()
        self._apply_theme()
        status = "enabled" if self.dark_mode else "disabled"
        self.status.config(text=f"Dark mode {status}")
    
    def _open_all_zlides(self) -> None:
        """Open all zlides in current presentation."""
        if not self.current_presentation or not self.current_presentation.zlides:
            messagebox.showinfo("No Zlides", "No zlides to open")
            return
        
        count = len(self.current_presentation.zlides)
        if count > 5:
            if not messagebox.askyesno("Open All", f"Open {count} items?"):
                return
        
        for zlide in self.current_presentation.zlides:
            proc = self._open_zlide_get_process(zlide)
            if proc:
                self.opened_processes.append(proc)
        
        self.status.config(text=f"Opened {count} zlides")
    
    def _open_selected_zlides(self) -> None:
        """Open selected zlides."""
        if not self.current_presentation:
            return
        
        selection = self.zlide_list.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Select zlides to open")
            return
        
        count = 0
        for idx in selection:
            zlide = self.current_presentation.zlides[idx]
            proc = self._open_zlide_get_process(zlide)
            if proc:
                self.opened_processes.append(proc)
            count += 1
        
        self.status.config(text=f"Opened {count} selected zlides")
    
    def _close_all_zlides(self) -> None:
        """Close all tracked processes."""
        closed = 0
        
        # Close current
        if self.current_process:
            PlatformHelper.close_process(self.current_process)
            self.current_process = None
            closed += 1
        
        # Close all tracked
        for proc in self.opened_processes:
            try:
                if proc.poll() is None:
                    PlatformHelper.close_process(proc)
                    closed += 1
            except Exception:
                pass
        
        self.opened_processes.clear()
        
        if closed > 0:
            self.status.config(text=f"Closed {closed} process(es)")
        else:
            self.status.config(text="No tracked processes to close")
    
    def _open_zlide_get_process(self, zlide: Zlide) -> Optional[subprocess.Popen]:
        """Open a zlide and return its process (for tracking)."""
        proc = None
        if zlide.type == ZlideType.BROWSER:
            proc = PlatformHelper.open_browser_window(zlide.data)
        elif zlide.type == ZlideType.FILE:
            proc = PlatformHelper.open_file(zlide.data)
        elif zlide.type == ZlideType.APP:
            proc = PlatformHelper.open_app(zlide.data)
        return proc
    
    def _refresh_folder_tree(self) -> None:
        """Refresh the folder tree view."""
        # Clear tree
        for item in self.folder_tree.get_children():
            self.folder_tree.delete(item)
        
        self.folder_nodes.clear()
        
        # Add folders and presentations
        for folder in self.workspace.folders:
            folder_id = self.folder_tree.insert('', 'end', text=f"📁 {folder.name}", tags=('folder',))
            self.folder_nodes[folder] = folder_id
            
            for pres in folder.presentations:
                pres_id = self.folder_tree.insert(folder_id, 'end', text=f"  📋 {pres.name} ({len(pres.zlides)})", tags=('presentation',))
                self.folder_nodes[pres] = pres_id
    
    def _on_tree_select(self, event) -> None:
        """Handle tree selection."""
        selection = self.folder_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        # Find what was selected
        for obj, node_id in self.folder_nodes.items():
            if node_id == item_id:
                if isinstance(obj, Folder):
                    self._select_folder(obj)
                elif isinstance(obj, Presentation):
                    self._select_presentation(obj)
                break
    
    def _on_tree_double_click(self, event) -> None:
        """Handle double-click on tree item."""
        selection = self.folder_tree.selection()
        if not selection:
            return
        
        item_id = selection[0]
        
        # Find presentation
        for obj, node_id in self.folder_nodes.items():
            if node_id == item_id and isinstance(obj, Presentation):
                # Start presenting
                self.current_zlide_index = 0
                if obj.zlides:
                    self.go_to_zlide(0)
                break
    
    def _select_folder(self, folder: Folder) -> None:
        """Select a folder."""
        self.current_folder = folder
        self.current_presentation = None
        self.pres_title_label.config(text=f"Folder: {folder.name}")
        self.zlide_list.delete(0, tk.END)
        self._update_zlide_counter()
    
    def _select_presentation(self, presentation: Presentation) -> None:
        """Select a presentation to edit."""
        # Find which folder contains this presentation
        for folder in self.workspace.folders:
            if presentation in folder.presentations:
                self.current_folder = folder
                break
        
        self.current_presentation = presentation
        self.current_zlide_index = -1
        self.pres_title_label.config(text=presentation.name)
        
        # Load zlides
        self.zlide_list.delete(0, tk.END)
        for i, zlide in enumerate(presentation.zlides):
            icon = {"browser": "🌐", "file": "📄", "app": "💻"}.get(zlide.type, "📄")
            self.zlide_list.insert(tk.END, f"{i+1}. {icon} {zlide.title}")
        
        self._update_zlide_counter()
        self.workspace.add_to_recent(presentation.name)
    
    def _add_folder(self) -> None:
        """Add a new folder."""
        name = simpledialog.askstring("New Folder", "Folder name:")
        if name:
            self.workspace.add_folder(name)
            self._refresh_folder_tree()
            self.status.config(text=f"Created folder: {name}")
    
    def _add_presentation(self) -> None:
        """Add a new presentation to current folder."""
        if not self.current_folder:
            messagebox.showwarning("No Folder", "Please select a folder first")
            return
        
        name = simpledialog.askstring("New Presentation", "Presentation name:")
        if name:
            pres = Presentation(name)
            self.current_folder.presentations.append(pres)
            self.workspace.save()
            self._refresh_folder_tree()
            self._select_presentation(pres)
            self.status.config(text=f"Created presentation: {name}")
    
    def _rename_presentation(self) -> None:
        """Rename current presentation."""
        if not self.current_presentation:
            return
        
        new_name = simpledialog.askstring("Rename", "New name:", initialvalue=self.current_presentation.name)
        if new_name:
            self.current_presentation.name = new_name
            self.workspace.save()
            self._refresh_folder_tree()
            self._select_presentation(self.current_presentation)
    
    def _delete_presentation(self) -> None:
        """Delete current presentation."""
        if not self.current_presentation or not self.current_folder:
            return
        
        if messagebox.askyesno("Delete", f"Delete '{self.current_presentation.name}'?"):
            self.current_folder.presentations.remove(self.current_presentation)
            self.workspace.save()
            self._refresh_folder_tree()
            self.current_presentation = None
            self.zlide_list.delete(0, tk.END)
            self.status.config(text="Presentation deleted")
    
    def _add_browser_zlide(self) -> None:
        """Add browser zlide."""
        if not self.current_presentation:
            messagebox.showwarning("No Presentation", "Select a presentation first")
            return
        
        url = simpledialog.askstring("Add Browser Zlide", "URL:")
        if url:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            title = simpledialog.askstring("Title", "Title:", initialvalue=url[:50])
            if title:
                zlide = Zlide(ZlideType.BROWSER, title, url)
                self.current_presentation.zlides.append(zlide)
                self.workspace.save()
                self._select_presentation(self.current_presentation)
    
    def _add_file_zlide(self) -> None:
        """Add file zlide."""
        if not self.current_presentation:
            messagebox.showwarning("No Presentation", "Select a presentation first")
            return
        
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(title="Select File")
        if filepath:
            filename = Path(filepath).name
            title = simpledialog.askstring("Title", "Title:", initialvalue=filename)
            if title:
                zlide = Zlide(ZlideType.FILE, title, filepath)
                self.current_presentation.zlides.append(zlide)
                self.workspace.save()
                self._select_presentation(self.current_presentation)
    
    def _add_app_zlide(self) -> None:
        """Add app zlide."""
        if not self.current_presentation:
            messagebox.showwarning("No Presentation", "Select a presentation first")
            return
        
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Select Application",
            filetypes=[("Applications", "*.exe;*.lnk;*.app"), ("All Files", "*.*")]
        )
        if filepath:
            filename = Path(filepath).stem
            title = simpledialog.askstring("Title", "Title:", initialvalue=filename)
            if title:
                zlide = Zlide(ZlideType.APP, title, filepath)
                self.current_presentation.zlides.append(zlide)
                self.workspace.save()
                self._select_presentation(self.current_presentation)
    
    def _delete_zlide(self) -> None:
        """Delete selected zlide(s)."""
        if not self.current_presentation:
            return
        
        selection = self.zlide_list.curselection()
        if not selection:
            return
        
        if messagebox.askyesno("Delete", f"Delete {len(selection)} zlide(s)?"):
            for idx in reversed(selection):
                del self.current_presentation.zlides[idx]
            self.workspace.save()
            self._select_presentation(self.current_presentation)
    
    def _on_zlide_double_click(self, event) -> None:
        """Open zlide on double-click."""
        selection = self.zlide_list.curselection()
        if selection:
            self.go_to_zlide(selection[0])
    
    def _open_zlide(self, zlide: Zlide) -> None:
        """Open a zlide."""
        # Close previous if auto-close enabled
        if self.auto_close_mode and self.current_process:
            PlatformHelper.close_process(self.current_process)
        
        # Open new
        proc = None
        if zlide.type == ZlideType.BROWSER:
            proc = PlatformHelper.open_browser_window(zlide.data)
        elif zlide.type == ZlideType.FILE:
            proc = PlatformHelper.open_file(zlide.data)
        elif zlide.type == ZlideType.APP:
            proc = PlatformHelper.open_app(zlide.data)
        
        if self.auto_close_mode:
            self.current_process = proc
    
    def next_zlide(self) -> None:
        """Navigate to next zlide."""
        if not self.current_presentation or not self.current_presentation.zlides:
            return
        
        if self.current_zlide_index < 0:
            self.current_zlide_index = 0
        elif self.current_zlide_index < len(self.current_presentation.zlides) - 1:
            self.current_zlide_index += 1
        else:
            return
        
        self._open_zlide(self.current_presentation.zlides[self.current_zlide_index])
        self._update_ui_for_current_zlide()
    
    def previous_zlide(self) -> None:
        """Navigate to previous zlide."""
        if not self.current_presentation or not self.current_presentation.zlides:
            return
        
        if self.current_zlide_index <= 0:
            return
        
        self.current_zlide_index -= 1
        self._open_zlide(self.current_presentation.zlides[self.current_zlide_index])
        self._update_ui_for_current_zlide()
    
    def go_to_zlide(self, index: int) -> None:
        """Go to specific zlide."""
        if not self.current_presentation or not self.current_presentation.zlides:
            return
        
        index = max(0, min(index, len(self.current_presentation.zlides) - 1))
        self.current_zlide_index = index
        self._open_zlide(self.current_presentation.zlides[index])
        self._update_ui_for_current_zlide()
    
    def _update_ui_for_current_zlide(self) -> None:
        """Update UI to reflect current zlide."""
        self._update_zlide_counter()
        self._update_compact_counter()
        
        # Highlight current zlide
        self.zlide_list.selection_clear(0, tk.END)
        if self.current_zlide_index >= 0:
            self.zlide_list.selection_set(self.current_zlide_index)
            self.zlide_list.see(self.current_zlide_index)
        
        # Update status
        if self.current_zlide_index >= 0 and self.current_presentation:
            zlide = self.current_presentation.zlides[self.current_zlide_index]
            self.status.config(text=f"Viewing: {zlide.title} ({self.current_zlide_index + 1}/{len(self.current_presentation.zlides)})")
    
    def _update_zlide_counter(self) -> None:
        """Update the zlide counter."""
        if self.current_presentation:
            current = self.current_zlide_index + 1 if self.current_zlide_index >= 0 else 0
            total = len(self.current_presentation.zlides)
            self.zlide_counter.config(text=f"{current}/{total}")
        else:
            self.zlide_counter.config(text="0/0")
    
    def toggle_compact_mode(self) -> None:
        """Toggle compact mode."""
        self.compact_mode = not self.compact_mode
        
        if self.compact_mode:
            self._enter_compact_mode()
        else:
            self._exit_compact_mode()
    
    def _enter_compact_mode(self) -> None:
        """Enter compact/mini mode."""
        # Save geometry
        current_geo = self.root.geometry()
        width = int(current_geo.split("x")[0])
        if width > 600:
            self.normal_geometry = current_geo
        
        # Hide main content
        for widget in self.root.winfo_children():
            widget.grid_remove()
        
        # Create compact frame
        self.compact_frame = tk.Frame(self.root, bg=Colors.DARK_BG, padx=8, pady=8)
        self.compact_frame.grid(row=0, column=0, sticky="nsew")
        
        # Top row: presentation info
        info_frame = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        info_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Presentation name
        pres_name = self.current_presentation.name if self.current_presentation else "No presentation"
        tk.Label(
            info_frame,
            text=f"📋 {pres_name}",
            font=('Arial', 10, 'bold'),
            fg=Colors.HIGHLIGHT_BLUE,
            bg=Colors.DARK_BG
        ).pack(side=tk.LEFT, padx=5)
        
        # Current zlide name
        if self.current_presentation and self.current_zlide_index >= 0:
            current_zlide = self.current_presentation.zlides[self.current_zlide_index]
            tk.Label(
                info_frame,
                text=current_zlide.title[:40],
                font=('Arial', 9),
                fg=Colors.MUTED_TEXT,
                bg=Colors.DARK_BG
            ).pack(side=tk.LEFT, padx=10)
        
        # Bottom row: controls
        controls = tk.Frame(self.compact_frame, bg=Colors.DARK_BG)
        controls.pack()
        
        # Auto-close indicator
        auto_close_color = Colors.AUTO_CLOSE_ON if self.auto_close_mode else Colors.AUTO_CLOSE_OFF
        tk.Label(
            controls,
            text="🔄",
            fg=auto_close_color,
            bg=Colors.DARK_BG,
            font=('Arial', 10)
        ).pack(side=tk.LEFT, padx=5)
        
        # Nav buttons
        btn_style = {
            'bg': Colors.DARK_BTN,
            'fg': 'white',
            'activebackground': Colors.DARK_BTN_ACTIVE,
            'relief': tk.RAISED,
            'bd': 1
        }
        
        tk.Button(controls, text="◀◀", command=lambda: self.go_to_zlide(0), width=4, **btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(controls, text="◀", command=self.previous_zlide, width=4, **btn_style).pack(side=tk.LEFT, padx=1)
        
        # Counter
        current = self.current_zlide_index + 1 if self.current_zlide_index >= 0 else 0
        total = len(self.current_presentation.zlides) if self.current_presentation else 0
        self.compact_counter = tk.Label(
            controls,
            text=f"{current}/{total}",
            font=('Arial', 12, 'bold'),
            fg=Colors.HIGHLIGHT_BLUE,
            bg=Colors.DARK_BG,
            width=8
        )
        self.compact_counter.pack(side=tk.LEFT, padx=5)
        
        tk.Button(controls, text="▶", command=self.next_zlide, width=4, **btn_style).pack(side=tk.LEFT, padx=1)
        tk.Button(controls, text="▶▶", command=lambda: self.go_to_zlide(999), width=4, **btn_style).pack(side=tk.LEFT, padx=1)
        
        # Separator
        tk.Frame(controls, width=2, bg=Colors.SEPARATOR).pack(side=tk.LEFT, padx=8, fill=tk.Y)
        
        # Expand button
        tk.Button(controls, text="▲ Full", command=self.toggle_compact_mode, width=6, **btn_style).pack(side=tk.LEFT, padx=2)
        
        # Resize
        self.root.geometry("700x80")
        self.mini_btn.config(text="▲ Full")
    
    def _exit_compact_mode(self) -> None:
        """Exit compact mode."""
        if hasattr(self, 'compact_frame'):
            self.compact_frame.destroy()
        
        # Restore main content
        for widget in self.root.winfo_children():
            widget.grid()
        
        # Restore geometry
        self.root.geometry(self.normal_geometry)
        self.mini_btn.config(text="▼ Mini")
    
    def _update_compact_counter(self) -> None:
        """Update compact mode counter."""
        if self.compact_mode and hasattr(self, 'compact_counter') and self.current_presentation:
            current = self.current_zlide_index + 1 if self.current_zlide_index >= 0 else 0
            total = len(self.current_presentation.zlides)
            self.compact_counter.config(text=f"{current}/{total}")


def main():
    root = tk.Tk()
    ZliderWorkspaceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()