import os

os.environ["TCL_LIBRARY"] = r"C:\Users\Victus\AppData\Local\Programs\Python\Python313\tcl\tcl8.6"
os.environ["TK_LIBRARY"] = r"C:\Users\Victus\AppData\Local\Programs\Python\Python313\tcl\tk8.6"

import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import load_config
from controllers import process_panchayat_development_plan,process_reconsilation,process_createnregisterplan
import traceback

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("eSwaraj Automations")
        self.root.geometry("400x220")
        self.root.resizable(False, False)

        ttk.Label(
            self.root,
            text="eSwaraj Automations",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=20)

        ttk.Button(
            self.root,
            text="Panchayat Development Plan",
            command=self.run_pdp,
            width=35
        ).pack(pady=10)

        ttk.Button(
            self.root,
            text="Account Reconsilation",
            command=self.run_reconsilation,
            width=35
        ).pack(pady=10)

        ttk.Button(
            self.root,
            text="Create And Register Plan",
            command=self.run_cpandr,
            width=35
        ).pack(pady=10)

        self.loading = None

    def show_loading(self, text="Please wait...\nAutomation is running."):
        self.loading = tk.Toplevel(self.root)
        self.loading.title("Running")
        self.loading.geometry("320x120")
        self.loading.resizable(False, False)

        # Prevent closing
        self.loading.protocol("WM_DELETE_WINDOW", lambda: None)

        # Make it modal
        self.loading.transient(self.root)
        self.loading.grab_set()

        ttk.Label(
            self.loading,
            text=text,
            justify="center"
        ).pack(pady=15)

        progress = ttk.Progressbar(
            self.loading,
            mode="indeterminate",
            length=250
        )
        progress.pack(pady=10)
        progress.start()

        # Disable main window
        self.root.attributes("-disabled", True)

    def hide_loading(self):
        try:
            self.root.attributes("-disabled", False)
        except tk.TclError:
            pass
        
        if self.loading:
            try:
                self.loading.grab_release()
            except tk.TclError:
                pass
            
            try:
                self.loading.destroy()
            except tk.TclError:
                pass
            
            self.loading = None

    def execute(self, func):
        try:
            func()
    
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Completed",
                    "Automation completed successfully."
                )
            )
    
            # Close the application after success
            self.root.after(100, self.root.destroy)
    
        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error",
                    str(e)
                )
            )
    
        finally:
            self.root.after(0, self.hide_loading)

    def start_task(self, func, loading_text):
        self.show_loading(loading_text)
        threading.Thread(
            target=self.execute,
            args=(func,),
            daemon=True
        ).start()

    def run_pdp(self):
        def task():
            config = load_config()
            process_panchayat_development_plan(config)

        self.start_task(
            task,
            "Running Panchayat Development Plan..."
        )

    def run_reconsilation(self):
        def task():
           config = load_config()
           process_reconsilation(config)

        self.start_task(
            task,
            "Running Reconsilation Automation..."
        )
    def run_cpandr(self):
        def task():
           config = load_config()
           process_createnregisterplan(config)

        self.start_task(
            task,
            "Creating Plan And Register Automation..."
        )
    def run(self):
        self.root.mainloop()


