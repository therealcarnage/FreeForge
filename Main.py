#!/usr/bin/env python3
"""
FreeCAD Parametric Generator
A Windows desktop app for generating parametric models from FreeCAD templates.
Runs FreeCAD headless to update spreadsheet parameters and export files.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import subprocess
import re
import threading
from pathlib import Path


class ParametricGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FreeCAD Parametric Generator")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # Variables for UI
        self.template_path = tk.StringVar(value=r"D:\Documents D\FreeCad\Projects\Rectangle.FCStd")
        self.output_path = tk.StringVar(value=r"D:\Documents D\FreeForge Output")
        self.freecad_path = tk.StringVar()
        self.c1_var = tk.StringVar(value="100")
        self.c2_var = tk.StringVar(value="50")
        self.c3_var = tk.StringVar(value="2")
        self.c4_var = tk.StringVar(value="1")
        self.stl_var = tk.BooleanVar(value=True)
        
        # Auto-detect FreeCAD
        self.auto_detect_freecad()
        
        self.setup_ui()
        
    def auto_detect_freecad(self):
        """Auto-detect common FreeCAD installation paths on Windows"""
        common_paths = [
            r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",  # lowercase variant
            r"C:\Program Files\FreeCAD 0.23\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD 0.22\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe", 
            r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 1.0\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 1.0\bin\freecadcmd.exe",
            r"C:\Program Files (x86)\FreeCAD 0.23\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 0.22\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 0.21\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 0.20\bin\FreeCADCmd.exe", 
            r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe"
        ]
        
        # First try common installation paths
        for path in common_paths:
            if os.path.isfile(path):
                self.freecad_path.set(path)
                print(f"Auto-detected FreeCAD: {path}")
                return
                
        # If not found, try searching Program Files directories
        try:
            import glob
            search_patterns = [
                r"C:\Program Files*\FreeCAD*\bin\FreeCADCmd.exe",
                r"C:\Program Files*\FreeCAD*\bin\freecadcmd.exe",
                r"C:\Program Files*\*\FreeCAD*\bin\FreeCADCmd.exe",
                r"C:\Program Files*\*\FreeCAD*\bin\freecadcmd.exe"
            ]
            for pattern in search_patterns:
                matches = glob.glob(pattern)
                if matches:
                    self.freecad_path.set(matches[0])
                    print(f"Found FreeCAD: {matches[0]}")
                    return
        except:
            pass
            
        print("FreeCAD not found automatically. Please browse for FreeCADCmd.exe")
                
    def setup_ui(self):
        """Setup the complete Tkinter user interface"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Parameters section
        params_frame = ttk.LabelFrame(main_frame, text="Parameters (e.g., '50 mm')", padding="5")
        params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        params_frame.columnconfigure(1, weight=1)
        
        param_entries = [
            ("C1:", self.c1_var),
            ("C2:", self.c2_var), 
            ("C3:", self.c3_var),
            ("C4:", self.c4_var)
        ]
        
        for i, (label, var) in enumerate(param_entries):
            ttk.Label(params_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(params_frame, textvariable=var, font=('Arial', 12))
            entry.grid(row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
            
        row += 1
        
        # Template file selection
        ttk.Label(main_frame, text="FreeCAD Template:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.template_path, font=('Arial', 10)).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_template).grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Output folder selection  
        ttk.Label(main_frame, text="Output Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.output_path, font=('Arial', 10)).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_output).grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # FreeCAD executable selection
        ttk.Label(main_frame, text="FreeCADCmd.exe:").grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(main_frame, textvariable=self.freecad_path, font=('Arial', 10)).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_freecad).grid(row=row, column=2, padx=5, pady=5)
        row += 1
        
        # Export formats
        export_frame = ttk.LabelFrame(main_frame, text="Export Formats", padding="5")
        export_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Checkbutton(export_frame, text="STL", variable=self.stl_var).grid(row=0, column=0, sticky=tk.W) 
        row += 1
        
        # Generate button
        self.generate_btn = ttk.Button(main_frame, text="Generate", 
                                     command=self.generate_threaded, style='Generate.TButton')
        self.generate_btn.grid(row=row, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        
        # Configure large button style
        style = ttk.Style()
        style.configure('Generate.TButton', font=('Arial', 14, 'bold'))
        row += 1
        
        # Status area
        ttk.Label(main_frame, text="Status:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5)
        row += 1
        
        self.status_text = scrolledtext.ScrolledText(main_frame, height=10, wrap=tk.WORD)
        self.status_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(row, weight=1)
        
        # Initial status message
        self.log("Ready. Select template file, output folder, enter parameters, and click Generate.")
        
    def browse_template(self):
        """Browse for FreeCAD template file"""
        filename = filedialog.askopenfilename(
            title="Select FreeCAD Template",
            filetypes=[("FreeCAD files", "*.FCStd"), ("All files", "*.*")]
        )
        if filename:
            self.template_path.set(filename)
            
    def browse_output(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path.set(folder)
            
    def browse_freecad(self):
        """Browse for FreeCAD executable"""
        filename = filedialog.askopenfilename(
            title="Select FreeCADCmd.exe",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.freecad_path.set(filename)
            
    def log(self, message):
        """Add message to status area"""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
        
    def validate_inputs(self):
        """Validate all required inputs"""
        errors = []
        
        if not self.template_path.get():
            errors.append("Please select a FreeCAD template file")
        elif not os.path.isfile(self.template_path.get()):
            errors.append("Template file does not exist")
            
        if not self.output_path.get():
            errors.append("Please select an output folder")
        elif not os.path.isdir(self.output_path.get()):
            errors.append("Output folder does not exist")
            
        if not self.freecad_path.get():
            errors.append("Please select FreeCADCmd.exe")
        elif not os.path.isfile(self.freecad_path.get()):
            errors.append("FreeCADCmd.exe does not exist")
            
        for param, name in [(self.c1_var.get(), "C1"), (self.c2_var.get(), "C2"),
                           (self.c3_var.get(), "C3"), (self.c4_var.get(), "C4")]:
            if not param.strip():
                errors.append(f"Parameter {name} is required")
                
        if not any([self.stl_var.get()]):
            errors.append("Please select STL export format")
            
        return errors
        
    def sanitize_filename_part(self, text):
        """Sanitize text for use in filenames"""
        # Keep only alphanumeric, underscore, hyphen, dot, and remove spaces
        sanitized = re.sub(r'[^a-zA-Z0-9._-]', '', text.replace(' ', ''))
        return sanitized[:50]  # Limit length
        
    def generate_threaded(self):
        """Run generation in a separate thread to avoid UI freezing"""
        threading.Thread(target=self.generate, daemon=True).start()
        
    def generate(self):
        """Main generation process"""
        # Disable button and clear status
        self.root.after(0, lambda: self.generate_btn.configure(state='disabled'))
        self.root.after(0, lambda: self.status_text.delete('1.0', tk.END))
        self.root.after(0, lambda: self.log("Starting generation..."))
        
        try:
            # Validate inputs
            errors = self.validate_inputs()
            if errors:
                for error in errors:
                    self.root.after(0, lambda e=error: self.log(f"ERROR: {e}"))
                return
                
            # Create the runner script
            runner_script = self.create_runner_script()
            runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_runner.py")
            
            with open(runner_path, 'w', encoding='utf-8') as f:
                f.write(runner_script)
                
            self.root.after(0, lambda: self.log("Created runner script"))
            
            # Prepare parameters
            template_file = self.template_path.get()
            output_folder = self.output_path.get()
            
            # Generate output filename base
            template_base = os.path.splitext(os.path.basename(template_file))[0]
            c1_clean = self.sanitize_filename_part(self.c1_var.get())
            c2_clean = self.sanitize_filename_part(self.c2_var.get())
            c3_clean = self.sanitize_filename_part(self.c3_var.get()) 
            c4_clean = self.sanitize_filename_part(self.c4_var.get())
            
            filename_base = f"{template_base}_C1{c1_clean}_C2{c2_clean}_C3{c3_clean}_C4{c4_clean}"
            
            # Build command - Use -c flag to execute Python code directly
            # Write script to file first, then read and execute it to avoid quote issues
            with open(runner_path, 'r') as f:
                script_content = f.read()
            
            cmd = [
                self.freecad_path.get(),
                "-c",
                script_content
            ]
            
            self.root.after(0, lambda: self.log(f"Executing FreeCAD with template: {os.path.basename(template_file)}"))
            self.root.after(0, lambda: self.log("Generating..."))
            
            # Set environment variables to pass arguments to the script
            env = os.environ.copy()
            env['FREECAD_TEMPLATE'] = template_file
            env['FREECAD_OUTPUT'] = output_folder
            env['FREECAD_BASE'] = filename_base
            env['FREECAD_C1'] = self.c1_var.get()
            env['FREECAD_C2'] = self.c2_var.get()
            env['FREECAD_C3'] = self.c3_var.get()
            env['FREECAD_C4'] = self.c4_var.get()
            env['FREECAD_STL'] = str(int(self.stl_var.get()))
            
            # Execute FreeCAD
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, 
                                      cwd=os.path.dirname(template_file), timeout=120, env=env)
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: self.log("✗ FreeCAD execution timed out (120 seconds)"))
                return
            
            if result.returncode == 0:
                self.root.after(0, lambda: self.log("FreeCAD execution completed"))
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.root.after(0, lambda l=line: self.log(l))
                self.root.after(0, lambda: self.log("✓ Generation completed successfully!"))
            else:
                self.root.after(0, lambda: self.log("✗ FreeCAD execution failed"))
                if result.stderr.strip():
                    for line in result.stderr.strip().split('\n'):
                        self.root.after(0, lambda l=line: self.log(f"ERROR: {l}"))
                if result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        self.root.after(0, lambda l=line: self.log(f"OUTPUT: {l}"))
                        
        except Exception as e:
            self.root.after(0, lambda: self.log(f"✗ Unexpected error: {str(e)}"))
            
        finally:
            # Re-enable button
            self.root.after(0, lambda: self.generate_btn.configure(state='normal'))
            
            # Clean up runner script
            try:
                runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_runner.py")
                if os.path.exists(runner_path):
                    os.remove(runner_path)
            except:
                pass
                
    def create_runner_script(self):
        """Create the Python script that will be executed by FreeCADCmd"""
        return '''import sys
import os

try:
    template_file = os.environ['FREECAD_TEMPLATE']
    output_folder = os.environ['FREECAD_OUTPUT']
    filename_base = os.environ['FREECAD_BASE']
    c1_value = os.environ['FREECAD_C1']
    c2_value = os.environ['FREECAD_C2']
    c3_value = os.environ['FREECAD_C3']
    c4_value = os.environ['FREECAD_C4']
    
    print(f"Output folder: {output_folder}")
    print(f"Folder exists: {os.path.exists(output_folder)}")
    
    import FreeCAD
    
    # Open document
    doc = FreeCAD.openDocument(template_file)
    
    # Find spreadsheet and set values
    for obj in doc.Objects:
        if hasattr(obj, 'TypeId') and obj.TypeId == 'Spreadsheet::Sheet':
            try:
                obj.set('C2', c1_value)
                obj.set('C3', c2_value) 
                obj.set('C4', c3_value)
                obj.set('C5', c4_value)
            except:
                pass
            break
    
    # Recompute
    doc.recompute()
    
    # Find body and export STL
    for obj in doc.Objects:
        if obj.Name == "Body":
            import Mesh
            stl_file = os.path.join(output_folder, f"{filename_base}.stl")
            print(f"Full STL path: {os.path.abspath(stl_file)}")
            Mesh.export([obj], stl_file)
            if os.path.exists(stl_file):
                print(f"SUCCESS: File created at {stl_file}")
                print(f"File size: {os.path.getsize(stl_file)} bytes")
            else:
                print(f"ERROR: File not found at {stl_file}")
            break
    
    # Close
    FreeCAD.closeDocument(doc.Name)
    
except Exception as e:
    print(f"Error: {e}")
'''

def main():
    """Main entry point"""
    app = ParametricGenerator()
    app.root.mainloop()

if __name__ == '__main__':
    main()
