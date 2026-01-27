import json
import os
import platform
import subprocess
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from pynput.keyboard import Controller, Key


class Zlide:
    def __init__(self, zlide_type, title, data, zlide_id=None):
        self.id = zlide_id if zlide_id else id(self)
        self.type = zlide_type  # 'browser', 'file', 'app'
        self.title = title
        self.data = data  # URL for browser, path for file/app

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "data": self.data,
        }

    @staticmethod
    def from_dict(d):
        return Zlide(d["type"], d["title"], d["data"], d["id"])


class ZliderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zlider - Presentation Tool")
        self.root.geometry("900x700")

        self.zlides = []
        self.current_zlide_index = -1
        self.presentation_mode = False
        self.current_file = None
        self.compact_mode = False
        
        # Store original geometry for restoring from compact mode
        self.normal_geometry = "900x700"

        # Keyboard controller for automation currently buggy
        self.keyboard = Controller()

        # Configure root to stay on top when in presentation mode
        self.root.attributes('-topmost', False)

        # Bind keyboard shortcuts
        self.root.bind("<Left>", lambda e: self.previous_zlide() if self.presentation_mode else None)
        self.root.bind("<Right>", lambda e: self.next_zlide() if self.presentation_mode else None)
        self.root.bind("<Home>", lambda e: self.go_to_zlide(0) if self.presentation_mode else None)
        self.root.bind("<End>", lambda e: self.go_to_zlide(len(self.zlides) - 1) if self.presentation_mode else None)
        self.root.bind("<space>", lambda e: self.next_zlide() if self.presentation_mode else None)
        self.root.bind("<Escape>", lambda e: self.toggle_compact_mode() if self.presentation_mode else None)

        self.create_widgets()

    def create_widgets(self):
        # Main container
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Top toolbar
        self.toolbar = ttk.Frame(self.main_frame)
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

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

        # Presentation controls (hidden initially)
        self.pres_controls_frame = ttk.Frame(self.toolbar)
        
        ttk.Button(
            self.pres_controls_frame,
            text="▶ Start",
            command=self.start_presentation,
            width=10
        ).pack(side=tk.LEFT, padx=2)

        self.pres_controls_frame.pack(side=tk.LEFT)

        # Zlide list frame
        list_frame = ttk.LabelFrame(self.main_frame, text="Zlideshow", padding="5")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))

        # Zlide listbox with scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.zlide_listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set, 
            height=25,
            font=('Arial', 10),
            selectmode=tk.SINGLE
        )
        self.zlide_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.zlide_listbox.yview)
        
        # Double-click to open zlide
        self.zlide_listbox.bind('<Double-Button-1>', self.on_zlide_double_click)

        # Zlide controls frame
        controls_frame = ttk.LabelFrame(self.main_frame, text="Edit Zlides", padding="5")
        controls_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

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

        # Status bar
        self.status_bar = ttk.Label(self.main_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=3)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

    def new_zlideshow(self):
        if self.zlides and messagebox.askyesno(
            "New Zlideshow", "Clear current zlides?"
        ):
            self.zlides = []
            self.current_file = None
            self.current_zlide_index = -1
            self.refresh_zlide_list()
            self.update_status("New zlideshow created")

    def add_browser_zlide(self):
        url = simpledialog.askstring("Add Browser Zlide", "Enter URL:")
        if url:
            # Add http:// if no protocol specified
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            title = simpledialog.askstring(
                "Zlide Title", "Enter title:", initialvalue=url[:50]
            )
            if title:
                zlide = Zlide("browser", title, url)
                self.zlides.append(zlide)
                self.refresh_zlide_list()
                self.update_status(f"Added browser zlide: {title}")

    def add_file_zlide(self):
        filepath = filedialog.askopenfilename(title="Select File")
        if filepath:
            filename = Path(filepath).name
            title = simpledialog.askstring(
                "Zlide Title", "Enter title:", initialvalue=filename
            )
            if title:
                zlide = Zlide("file", title, filepath)
                self.zlides.append(zlide)
                self.refresh_zlide_list()
                self.update_status(f"Added file zlide: {title}")

    def edit_zlide(self):
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

    def delete_zlide(self):
        selection = self.zlide_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a zlide to delete")
            return

        if messagebox.askyesno("Delete Zlide", "Are you sure?"):
            idx = selection[0]
            title = self.zlides[idx].title
            del self.zlides[idx]
            self.refresh_zlide_list()
            self.update_status(f"Deleted zlide: {title}")

    def move_up(self):
        selection = self.zlide_listbox.curselection()
        if not selection or selection[0] == 0:
            return

        idx = selection[0]
        self.zlides[idx], self.zlides[idx - 1] = self.zlides[idx - 1], self.zlides[idx]
        self.refresh_zlide_list()
        self.zlide_listbox.selection_set(idx - 1)

    def move_down(self):
        selection = self.zlide_listbox.curselection()
        if not selection or selection[0] == len(self.zlides) - 1:
            return

        idx = selection[0]
        self.zlides[idx], self.zlides[idx + 1] = self.zlides[idx + 1], self.zlides[idx]
        self.refresh_zlide_list()
        self.zlide_listbox.selection_set(idx + 1)

    def refresh_zlide_list(self):
        self.zlide_listbox.delete(0, tk.END)
        for i, zlide in enumerate(self.zlides):
            icon = "🌐" if zlide.type == "browser" else "📄"
            
            # Highlight current zlide in presentation mode
            prefix = "▶ " if (self.presentation_mode and i == self.current_zlide_index) else "  "
            
            self.zlide_listbox.insert(tk.END, f"{prefix}{i + 1}. {icon} {zlide.title}")
            
            # Highlight current zlide with different background
            if self.presentation_mode and i == self.current_zlide_index:
                self.zlide_listbox.itemconfig(i, background='lightblue')

    def on_zlide_double_click(self, event):
        """Handle double-click on zlide - open it directly or navigate to it"""
        selection = self.zlide_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        
        if self.presentation_mode:
            # Navigate to this zlide
            self.go_to_zlide(idx)
        else:
            # Just open this zlide
            self.open_single_zlide(self.zlides[idx])

    def save_zlideshow(self):
        if not self.zlides:
            messagebox.showwarning("No Zlides", "No zlides to save")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".zlides",
            filetypes=[("Zlider Files", "*.zlides"), ("All Files", "*.*")],
        )

        if filepath:
            data = {"version": "1.0", "zlides": [z.to_dict() for z in self.zlides]}

            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            self.current_file = filepath
            self.update_status(f"Saved: {Path(filepath).name}")
            messagebox.showinfo("Saved", f"Zlideshow saved to {filepath}")

    def open_zlideshow(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("Zlider Files", "*.zlides"), ("All Files", "*.*")]
        )

        if filepath:
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)

                self.zlides = [Zlide.from_dict(z) for z in data["zlides"]]
                self.current_file = filepath
                self.refresh_zlide_list()
                self.update_status(f"Loaded: {Path(filepath).name} ({len(self.zlides)} zlides)")
                messagebox.showinfo("Loaded", f"Loaded {len(self.zlides)} zlides")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

    def start_presentation(self):
        if not self.zlides:
            messagebox.showwarning("No Zlides", "No zlides in presentation")
            return

        self.presentation_mode = True
        self.current_zlide_index = 0
        
        # Switch UI to presentation mode
        self.switch_to_presentation_mode()
        
        # Open first zlide
        self.open_single_zlide(self.zlides[0])
        self.refresh_zlide_list()
        self.update_status(f"Presenting: {self.zlides[0].title} (1/{len(self.zlides)}) - Use ← → or Space to navigate")

    def switch_to_presentation_mode(self):
        """Switch UI to presentation mode"""
        # Clear and rebuild toolbar for presentation
        for widget in self.pres_controls_frame.winfo_children():
            widget.destroy()
        
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
            foreground='blue'
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
        self.update_presentation_label()

    def update_presentation_label(self):
        """Update the current zlide counter in presentation mode"""
        if hasattr(self, 'current_zlide_label'):
            self.current_zlide_label.config(
                text=f"{self.current_zlide_index + 1}/{len(self.zlides)}"
            )
        self.update_compact_label()
    
    def update_compact_label(self):
        """Update the compact mode label if in compact mode"""
        if self.compact_mode and hasattr(self, 'compact_zlide_label'):
            self.compact_zlide_label.config(
                text=f"{self.current_zlide_index + 1}/{len(self.zlides)}"
            )

    def end_presentation(self):
        """End presentation mode and return to editing mode"""
        self.presentation_mode = False
        self.current_zlide_index = -1
        
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
        
        self.refresh_zlide_list()
        self.update_status("Presentation ended")

    def next_zlide(self):
        """Navigate to next zlide"""
        if not self.presentation_mode:
            return
            
        if self.current_zlide_index < len(self.zlides) - 1:
            self.current_zlide_index += 1
            self.open_single_zlide(self.zlides[self.current_zlide_index])
            self.refresh_zlide_list()
            self.update_presentation_label()
            current = self.zlides[self.current_zlide_index]
            self.update_status(f"Presenting: {current.title} ({self.current_zlide_index + 1}/{len(self.zlides)})")

    def previous_zlide(self):
        """Navigate to previous zlide"""
        if not self.presentation_mode:
            return
            
        if self.current_zlide_index > 0:
            self.current_zlide_index -= 1
            self.open_single_zlide(self.zlides[self.current_zlide_index])
            self.refresh_zlide_list()
            self.update_presentation_label()
            current = self.zlides[self.current_zlide_index]
            self.update_status(f"Presenting: {current.title} ({self.current_zlide_index + 1}/{len(self.zlides)})")

    def go_to_zlide(self, index):
        """Jump directly to a specific zlide index"""
        if not self.presentation_mode or index < 0 or index >= len(self.zlides):
            return
        
        self.current_zlide_index = index
        self.open_single_zlide(self.zlides[index])
        self.refresh_zlide_list()
        self.update_presentation_label()
        current = self.zlides[self.current_zlide_index]
        self.update_status(f"Presenting: {current.title} ({self.current_zlide_index + 1}/{len(self.zlides)})")

    def open_single_zlide(self, zlide):
        """Open a single zlide (browser tab or file)"""
        try:
            if zlide.type == "browser":
                print(f"Opening browser zlide: {zlide.title}")
                webbrowser.open(zlide.data)
            elif zlide.type == "file":
                print(f"Opening file zlide: {zlide.title}")
                if platform.system() == "Windows":
                    os.startfile(zlide.data)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.call(["open", zlide.data])
                else:  # linux
                    subprocess.call(["xdg-open", zlide.data])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {zlide.title}: {str(e)}")
            print(f"Error opening zlide: {e}")

    def update_status(self, message):
        """Update the status bar"""
        self.status_bar.config(text=message)
        print(f"Status: {message}")

    def toggle_compact_mode(self):
        """Toggle between compact and normal view during presentation"""
        if not self.presentation_mode:
            return
        
        self.compact_mode = not self.compact_mode
        
        if self.compact_mode:
            # Save current geometry
            self.normal_geometry = self.root.geometry()
            
            # Hide everything except toolbar
            self.main_frame.grid_remove()
            
            # Create compact frame
            self.compact_frame = ttk.Frame(self.root, padding="5")
            self.compact_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            # Compact navigation
            nav_frame = ttk.Frame(self.compact_frame)
            nav_frame.pack()
            
            ttk.Button(
                nav_frame,
                text="◀◀",
                command=lambda: self.go_to_zlide(0),
                width=4
            ).pack(side=tk.LEFT, padx=1)
            
            ttk.Button(
                nav_frame,
                text="◀",
                command=self.previous_zlide,
                width=4
            ).pack(side=tk.LEFT, padx=1)
            
            self.compact_zlide_label = ttk.Label(
                nav_frame,
                text=f"{self.current_zlide_index + 1}/{len(self.zlides)}",
                font=('Arial', 12, 'bold'),
                foreground='blue',
                width=8
            )
            self.compact_zlide_label.pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                nav_frame,
                text="▶",
                command=self.next_zlide,
                width=4
            ).pack(side=tk.LEFT, padx=1)
            
            ttk.Button(
                nav_frame,
                text="▶▶",
                command=lambda: self.go_to_zlide(len(self.zlides) - 1),
                width=4
            ).pack(side=tk.LEFT, padx=1)
            
            ttk.Separator(nav_frame, orient=tk.VERTICAL).pack(
                side=tk.LEFT, padx=5, fill=tk.Y
            )
            
            ttk.Button(
                nav_frame,
                text="▲ Full",
                command=self.toggle_compact_mode,
                width=6
            ).pack(side=tk.LEFT, padx=1)
            
            ttk.Button(
                nav_frame,
                text="■ End",
                command=self.end_presentation,
                width=6
            ).pack(side=tk.LEFT, padx=1)
            
            # Resize window to compact size
            self.root.geometry("400x60")
            
            # Update button text in main toolbar (if visible)
            if hasattr(self, 'compact_btn'):
                self.compact_btn.config(text="▲ Full")
            
        else:
            # Restore normal view
            if hasattr(self, 'compact_frame'):
                self.compact_frame.destroy()
            
            self.main_frame.grid()
            
            # Restore original geometry
            self.root.geometry(self.normal_geometry)
            
            # Update button text
            if hasattr(self, 'compact_btn'):
                self.compact_btn.config(text="▼ Mini")
        
        self.update_compact_label()


def main():
    root = tk.Tk()
    app = ZliderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()