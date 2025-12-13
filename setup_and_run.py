#!/usr/bin/env python3
"""
StockLeague Automatic Setup & Run Script
This script sets up the entire environment and launches the webapp.
Works on Windows and Mac without requiring terminal knowledge.
"""

import os
import sys
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
from pathlib import Path


class SetupRunner:
    """Manages the setup and execution process"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("StockLeague Setup & Launcher")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="StockLeague Setup & Launcher", 
                               font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready to start setup", 
                                      font=("Helvetica", 10))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=10, sticky=tk.W)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Output text area
        output_label = ttk.Label(main_frame, text="Setup Output:", font=("Helvetica", 9, "bold"))
        output_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))
        
        self.output_text = scrolledtext.ScrolledText(main_frame, height=15, width=70,
                                                      font=("Courier", 9),
                                                      state=tk.DISABLED)
        self.output_text.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        # Start button
        self.start_button = ttk.Button(button_frame, text="Start Setup & Launch", 
                                       command=self.start_setup)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        # Cancel button
        self.cancel_button = ttk.Button(button_frame, text="Cancel", 
                                        command=self.cancel_setup, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.setup_thread = None
        self.should_cancel = False
        
    def log_output(self, message):
        """Add message to output text"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)  # Auto-scroll to bottom
        self.output_text.config(state=tk.DISABLED)
        self.root.update()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
        self.root.update()
    
    def start_setup(self):
        """Start setup in background thread"""
        self.should_cancel = False
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL)
        self.progress.start()
        
        self.setup_thread = threading.Thread(target=self.run_setup, daemon=True)
        self.setup_thread.start()
    
    def cancel_setup(self):
        """Cancel setup"""
        self.should_cancel = True
        self.update_status("Cancelling setup...")
    
    def run_setup(self):
        """Run the actual setup process"""
        try:
            # Get the script directory
            script_dir = Path(__file__).parent.absolute()
            os.chdir(script_dir)
            
            self.log_output("=" * 60)
            self.log_output("StockLeague Setup & Launcher")
            self.log_output("=" * 60)
            self.log_output(f"Python Version: {sys.version}")
            self.log_output(f"Platform: {platform.system()}")
            self.log_output(f"Working Directory: {script_dir}")
            self.log_output("")
            
            # Step 1: Check Python version
            self.update_status("Checking Python version...")
            self.log_output("[1/4] Checking Python version...")
            if sys.version_info < (3, 8):
                raise Exception("Python 3.8+ is required")
            self.log_output(f"✓ Python version OK: {sys.version_info.major}.{sys.version_info.minor}")
            self.log_output("")
            
            if self.should_cancel:
                self.log_output("Setup cancelled by user")
                return
            
            # Step 2: Check/Create virtual environment
            self.update_status("Setting up virtual environment...")
            self.log_output("[2/4] Setting up virtual environment...")
            venv_path = script_dir / "venv"
            
            if venv_path.exists():
                self.log_output("✓ Virtual environment already exists")
            else:
                self.log_output("Creating virtual environment...")
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], 
                             check=True, capture_output=True)
                self.log_output("✓ Virtual environment created")
            
            # Get the appropriate Python executable
            if platform.system() == "Windows":
                python_exe = venv_path / "Scripts" / "python.exe"
                pip_exe = venv_path / "Scripts" / "pip.exe"
            else:  # Mac/Linux
                python_exe = venv_path / "bin" / "python"
                pip_exe = venv_path / "bin" / "pip"
            
            self.log_output("")
            
            if self.should_cancel:
                self.log_output("Setup cancelled by user")
                return
            
            # Step 3: Install requirements
            self.update_status("Installing dependencies...")
            self.log_output("[3/4] Installing dependencies from requirements.txt...")
            
            requirements_file = script_dir / "requirements.txt"
            if requirements_file.exists():
                self.log_output("Installing packages (this may take a minute)...")
                result = subprocess.run([str(pip_exe), "install", "-r", str(requirements_file)],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_output("✓ Dependencies installed successfully")
                else:
                    self.log_output("Warning: Some packages may not have installed correctly")
                    self.log_output(result.stderr[-500:] if len(result.stderr) > 500 else result.stderr)
            else:
                self.log_output("⚠ requirements.txt not found, skipping dependency installation")
                self.log_output("Make sure all dependencies are installed manually")
            
            self.log_output("")
            
            if self.should_cancel:
                self.log_output("Setup cancelled by user")
                return
            
            # Step 4: Launch the app
            self.update_status("Launching StockLeague...")
            self.log_output("[4/4] Launching StockLeague...")
            self.log_output("")
            self.log_output("Starting Flask server...")
            self.log_output("=" * 60)
            
            # Launch the app
            app_script = script_dir / "app.py"
            if app_script.exists():
                self.progress.stop()
                self.start_button.config(state=tk.NORMAL)
                self.cancel_button.config(state=tk.DISABLED)
                
                # Hide or minimize the launcher window
                self.log_output("")
                self.log_output("✓ Setup complete! Opening StockLeague in your browser...")
                self.log_output("")
                self.log_output("The app will be available at: http://localhost:5000")
                self.log_output("This window will close after the app starts.")
                self.log_output("")
                
                self.root.update()
                time.sleep(2)
                
                # Run the app
                subprocess.Popen([str(python_exe), str(app_script)])
                
                # Close the launcher window after a short delay
                self.root.after(3000, self.root.quit)
            else:
                raise Exception("app.py not found in the current directory")
                
        except Exception as e:
            self.progress.stop()
            self.start_button.config(state=tk.NORMAL)
            self.cancel_button.config(state=tk.DISABLED)
            
            error_msg = f"✗ Error during setup: {str(e)}"
            self.log_output("")
            self.log_output(error_msg)
            self.update_status(f"Error: {str(e)}")
            
            messagebox.showerror("Setup Error", 
                               f"An error occurred during setup:\n\n{error_msg}\n\nPlease check the output above.")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = SetupRunner(root)
    root.mainloop()


if __name__ == "__main__":
    main()
