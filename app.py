"""
Bill Compressor GUI - Folder selection, compression, and ZIP creation.
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
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        self.selected_folder: str = ""
        self.files: list[str] = []
        self.processing = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title = ttk.Label(
            main_frame, 
            text="Compresseur de Factures",
            font=('Segoe UI', 18, 'bold')
        )
        title.pack(pady=(0, 5))
        
        subtitle = ttk.Label(
            main_frame,
            text="Compresse PDF/PNG/JPG a 200 Ko max",
            font=('Segoe UI', 10)
        )
        subtitle.pack(pady=(0, 30))
        
        self.select_btn = ttk.Button(
            main_frame,
            text="Selectionner un dossier",
            command=self._select_folder
        )
        self.select_btn.pack(pady=(0, 15))
        
        self.folder_var = tk.StringVar(value="Aucun dossier selectionne")
        folder_label = ttk.Label(
            main_frame,
            textvariable=self.folder_var,
            font=('Segoe UI', 9),
            foreground='gray'
        )
        folder_label.pack(pady=(0, 5))
        
        self.count_var = tk.StringVar(value="")
        count_label = ttk.Label(
            main_frame,
            textvariable=self.count_var,
            font=('Segoe UI', 10, 'bold')
        )
        count_label.pack(pady=(0, 20))
        
        self.progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(
            main_frame,
            textvariable=self.progress_var,
            font=('Segoe UI', 9)
        )
        progress_label.pack(pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=(0, 20))
        
        self.compress_btn = ttk.Button(
            main_frame,
            text="Compresser",
            command=self._start_compression,
            state=tk.DISABLED
        )
        self.compress_btn.pack(pady=(0, 20))
        
        result_frame = ttk.LabelFrame(main_frame, text="Resultats", padding="5")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(
            result_frame,
            height=10,
            font=('Consolas', 9),
            state=tk.DISABLED
        )
        scrollbar = ttk.Scrollbar(
            result_frame,
            orient=tk.VERTICAL,
            command=self.result_text.yview
        )
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _select_folder(self):
        folder = filedialog.askdirectory(
            title="Selectionner le dossier contenant les factures"
        )
        
        if not folder:
            return
        
        self.selected_folder = folder
        self.files = []
        
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isfile(filepath):
                if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                    self.files.append(filepath)
        
        self.folder_var.set(folder)
        
        if self.files:
            total_size = sum(os.path.getsize(f) for f in self.files) // 1024
            self.count_var.set(
                f"{len(self.files)} fichiers trouves ({total_size} Ko total)"
            )
            self.compress_btn.config(state=tk.NORMAL)
        else:
            self.count_var.set("Aucun fichier PDF/PNG/JPG trouve")
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
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_folder = os.path.join(
            self.selected_folder,
            f"factures_compressees_{timestamp}"
        )
        output_zip = output_folder + ".zip"
        
        self.processing = True
        self.select_btn.config(state=tk.DISABLED)
        self.compress_btn.config(state=tk.DISABLED)
        self._clear_results()
        
        thread = threading.Thread(
            target=self._run_compression,
            args=(output_folder, output_zip),
            daemon=True
        )
        thread.start()
    
    def _run_compression(self, output_folder: str, output_zip: str):
        def progress_callback(current: int, total: int, filename: str):
            self.root.after(
                0,
                lambda: self._update_progress(current, total, filename)
            )
        
        try:
            stats = process_files(
                self.files,
                output_folder,
                output_zip,
                progress_callback
            )
            self.root.after(0, lambda: self._show_results(stats))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(str(e)))
        finally:
            self.root.after(0, self._reset_ui)
    
    def _update_progress(self, current: int, total: int, filename: str):
        percent = (current / total) * 100
        self.progress_bar['value'] = percent
        self.progress_var.set(f"{filename} ({current}/{total})")
    
    def _show_results(self, stats: dict):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        
        self.result_text.insert(tk.END, "=== COMPRESSION TERMINEE ===\n\n")
        self.result_text.insert(
            tk.END,
            f"Fichiers OK: {stats['success']}/{stats['total']}\n"
        )
        self.result_text.insert(
            tk.END,
            f"Taille ZIP: {stats.get('zip_size_kb', 0)} Ko\n\n"
        )
        self.result_text.insert(tk.END, "Details:\n")
        
        for filename, status in stats['details']:
            self.result_text.insert(tk.END, f"  {filename}\n")
            self.result_text.insert(tk.END, f"    -> {status}\n")
        
        self.result_text.insert(tk.END, f"\nDossier: {stats['output_folder']}\n")
        self.result_text.insert(tk.END, f"ZIP: {stats['output_folder']}.zip")
        self.result_text.config(state=tk.DISABLED)
        
        self.progress_var.set("Termine!")
    
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
