"""
Bill Compressor GUI - Simple folder selection and compression.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from compressor import process_files

SUPPORTED_EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg')


class CompressorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Compresseur de Factures")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        self.selected_folder: str = ""
        self.files: list[str] = []
        self.processing = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            main_frame, 
            text="Compresseur de Factures",
            font=('Segoe UI', 18, 'bold')
        )
        title.pack(pady=(0, 5))
        
        subtitle = ttk.Label(
            main_frame,
            text="Compresse PDF/PNG a 200 Ko max et cree un ZIP",
            font=('Segoe UI', 10)
        )
        subtitle.pack(pady=(0, 30))
        
        # Folder selection
        self.select_btn = ttk.Button(
            main_frame,
            text="Selectionner un dossier",
            command=self._select_folder
        )
        self.select_btn.pack(pady=(0, 15))
        
        # Selected folder display
        self.folder_var = tk.StringVar(value="Aucun dossier selectionne")
        folder_label = ttk.Label(
            main_frame,
            textvariable=self.folder_var,
            font=('Segoe UI', 9),
            foreground='gray'
        )
        folder_label.pack(pady=(0, 5))
        
        # File count
        self.count_var = tk.StringVar(value="")
        count_label = ttk.Label(
            main_frame,
            textvariable=self.count_var,
            font=('Segoe UI', 10, 'bold')
        )
        count_label.pack(pady=(0, 20))
        
        # Progress
        self.progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(
            main_frame,
            textvariable=self.progress_var,
            font=('Segoe UI', 9)
        )
        progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 20))
        
        # Compress button
        self.compress_btn = ttk.Button(
            main_frame,
            text="Compresser",
            command=self._start_compression,
            state=tk.DISABLED
        )
        self.compress_btn.pack(pady=(0, 20))
        
        # Result text
        self.result_text = tk.Text(
            main_frame,
            height=8,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)
    
    def _select_folder(self):
        folder = filedialog.askdirectory(title="Selectionner le dossier des factures")
        
        if not folder:
            return
        
        self.selected_folder = folder
        self.files = []
        
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath) and filename.lower().endswith(SUPPORTED_EXTENSIONS):
                self.files.append(filepath)
        
        self.folder_var.set(folder)
        
        if self.files:
            total_size = sum(os.path.getsize(f) for f in self.files) // 1024
            self.count_var.set(f"{len(self.files)} fichiers trouves ({total_size} Ko)")
            self.compress_btn.config(state=tk.NORMAL)
        else:
            self.count_var.set("Aucun fichier PDF/PNG trouve")
            self.compress_btn.config(state=tk.DISABLED)
        
        self._clear_results()
    
    def _clear_results(self):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.progress_var.set("")
        self.progress_bar['value'] = 0
    
    def _start_compression(self):
        if not self.files or self.processing:
            return
        
        # Output ZIP in same folder as source
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_name = f"factures_compressees_{timestamp}.zip"
        output_path = os.path.join(self.selected_folder, default_name)
        
        # Ask where to save
        output_path = filedialog.asksaveasfilename(
            title="Enregistrer le ZIP",
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")],
            initialfile=default_name,
            initialdir=self.selected_folder
        )
        
        if not output_path:
            return
        
        self.processing = True
        self.select_btn.config(state=tk.DISABLED)
        self.compress_btn.config(state=tk.DISABLED)
        self._clear_results()
        
        thread = threading.Thread(
            target=self._run_compression,
            args=(output_path,),
            daemon=True
        )
        thread.start()
    
    def _run_compression(self, output_path: str):
        def progress_callback(current: int, total: int, filename: str):
            self.root.after(0, lambda: self._update_progress(current, total, filename))
        
        try:
            stats = process_files(self.files, output_path, progress_callback)
            self.root.after(0, lambda: self._show_results(stats, output_path))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, self._reset_ui)
    
    def _update_progress(self, current: int, total: int, filename: str):
        percent = (current / total) * 100
        self.progress_bar['value'] = percent
        self.progress_var.set(f"{filename} ({current}/{total})")
    
    def _show_results(self, stats: dict, output_path: str):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        
        self.result_text.insert(tk.END, f"=== TERMINE ===\n\n")
        self.result_text.insert(tk.END, f"Fichiers: {stats['success']}/{stats['total']} OK\n")
        self.result_text.insert(tk.END, f"ZIP: {stats.get('zip_size_kb', 0)} Ko\n\n")
        
        for filename, status in stats['details']:
            self.result_text.insert(tk.END, f"  {filename}: {status}\n")
        
        self.result_text.insert(tk.END, f"\nFichier: {output_path}")
        self.result_text.config(state=tk.DISABLED)
        
        self.progress_var.set("Compression terminee!")
    
    def _show_error(self, error: str):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, f"ERREUR: {error}")
        self.result_text.config(state=tk.DISABLED)
    
    def _reset_ui(self):
        self.processing = False
        self.select_btn.config(state=tk.NORMAL)
        if self.files:
            self.compress_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    CompressorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
