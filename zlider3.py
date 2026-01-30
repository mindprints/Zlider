"""
Zlider Workspace Edition - A presentation tool with folder-based organization.
No more New/Open/Save - everything auto-saves to a single workspace.

Migration Guide:
----------------
To migrate from zlider.py (v1) to zlider3.py (v2):

1. First-time setup: Run zlider3.py - it will create a new workspace automatically
2. Import existing presentations: 
   - Click "📥 Import" button in the sidebar
   - Select your existing .zlides files
   - They will be imported into the current folder
3. Your old .zlides files remain untouched - they serve as backups
4. All changes in zlider3 are auto-saved to ~/.zlider_workspace.json

Backwards Compatibility:
- zlider.py (v1) files (.zlides) can be imported but not opened directly
- Once imported, presentations live in the workspace
- Both apps can coexist during transition period
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

# Version info for migration support
VERSION = "2.0"
LEGACY_VERSION = "1.0"


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
    
    # Dark compact mode
    DARK_BG = "#1f1f1f"
    DARK_BTN = "#2b2b2b"
    DARK_BTN_ACTIVE = "#3a3a3a"
    HIGHLIGHT_BLUE = "#6bb9ff"
    TIMER_GREEN = "#6fe389"
    MUTED_TEXT = "#9a9a9a"


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
    
    def __hash__(self):
        """Make Presentation hashable for use as dict key."""
        return id(self)
    
    def __eq__(self, other):
        """Equality based on identity for hash consistency."""
        if not isinstance(other, Presentation):
            return False
        return id(self) == id(other)
    
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
    
    def __hash__(self):
        """Make Folder hashable for use as dict key."""
        return id(self)
    
    def __eq__(self, other):
        """Equality based on identity for hash consistency."""
        if not isinstance(other, Folder):
            return False
        return id(self) == id(other)
    
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
                "version": VERSION,
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
    
    def import_zlides_file(self, filepath: str) -> Optional[Presentation]:
        """Import a legacy .zlides file into the workspace.
        
        Args:
            filepath: Path to the .zlides file to import
            
        Returns:
            The imported Presentation, or None if import failed
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check version for compatibility
            file_version = data.get('version', LEGACY_VERSION)
            if file_version not in (LEGACY_VERSION, VERSION):
                print(f"Warning: Unknown file version {file_version}, attempting import anyway")
            
            # Extract filename without extension as presentation name
            from pathlib import Path
            pres_name = Path(filepath).stem
            
            # Create presentation
            presentation = Presentation(name=pres_name)
            
            # Import zlides - handle both old and new formats
            for zlide_data in data.get('zlides', []):
                # Handle legacy format where type might be an enum value
                zlide_type = zlide_data.get('type', '')
                if hasattr(ZlideType, zlide_type.upper()):
                    zlide_type = getattr(ZlideType, zlide_type.upper())
                
                zlide = Zlide.from_dict(zlide_data)
                presentation.zlides.append(zlide)
            
            # Import settings if available
            if 'settings' in data:
                presentation.settings = data['settings']
            
            return presentation
            
        except Exception as e:
            print(f"Error importing .zlides file: {e}")
            return None
    
    def import_all_zlides_files(self, directory: str, target_folder: Folder) -> int:
        """Import all .zlides files from a directory into a folder.
        
        Args:
            directory: Directory to search for .zlides files
            target_folder: Folder to add presentations to
            
        Returns:
            Number of presentations imported
        """
        import os
        count = 0
        
        for filename in os.listdir(directory):
            if filename.endswith('.zlides'):
                filepath = os.path.join(directory, filename)
                presentation = self.import_zlides_file(filepath)
                if presentation:
                    target_folder.presentations.append(presentation)
                    count += 1
        
        if count > 0:
            self._save_workspace()
        
        return count


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
        
        # Auto-close tracking
        self.auto_close_mode: bool = self.workspace.settings.get("auto_close_mode", False)
        self.current_process: Optional[subprocess.Popen] = None
        
        # Timer
        self.presentation_start_time: Optional[datetime] = None
        self.timer_id: Optional[str] = None
        
        # UI state
        self.folder_nodes: dict = {}  # folder -> tree node id
        
        self._setup_keybindings()
        self._create_ui()
        
        # Load first folder by default
        if self.workspace.folders:
            self._select_folder(self.workspace.folders[0])
    
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
        
        # Import button for legacy files
        import_btn = ttk.Button(folder_btns, text="📥 Import", command=self._import_zlides_file, width=12)
        import_btn.pack(side=tk.LEFT, padx=2)
        
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
    
    def _import_zlides_file(self) -> None:
        """Import a legacy .zlides file into the current folder."""
        if not self.current_folder:
            messagebox.showwarning("No Folder", "Please select a folder first")
            return
        
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            title="Import .zlides File",
            filetypes=[("Zlider presentations", "*.zlides"), ("All files", "*.*")]
        )
        
        if filepath:
            presentation = self.workspace.import_zlides_file(filepath)
            if presentation:
                self.current_folder.presentations.append(presentation)
                self.workspace.save()
                self._refresh_folder_tree()
                self._select_presentation(presentation)
                self.status.config(text=f"Imported: {presentation.name} ({len(presentation.zlides)} zlides)")
            else:
                messagebox.showerror("Import Failed", f"Could not import file:\n{filepath}")
    
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
            current = max(0, self.current_zlide_index) if self.current_zlide_index >= 0 else 0
            total = len(self.current_presentation.zlides)
            self.zlide_counter.config(text=f"{current}/{total}")
        else:
            self.zlide_counter.config(text="0/0")
    
    def toggle_compact_mode(self) -> None:
        """Toggle compact mode (simplified for now)."""
        # For MVP, just show message
        messagebox.showinfo("Compact Mode", "Compact mode coming soon!\n\nFor now, use the navigation buttons and keyboard shortcuts.")


def main():
    root = tk.Tk()
    ZliderWorkspaceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()