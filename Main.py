#!/usr/bin/env python3
"""
FreeCAD Parametric Generator
A Windows desktop app for generating parametric models from FreeCAD templates.
Runs FreeCAD headless to update spreadsheet parameters and export files.

Author: Generated Assistant
Version: 1.0
Date: January 2026
"""

# ═══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

import os
import sys
import json
import textwrap
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CONSTANTS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Application constants
APP_TITLE = "FreeCAD Parametric Generator"
APP_VERSION = "1.0"
APP_GEOMETRY = "600x700"

# FreeCAD installation paths to check (in order of preference)
FREECAD_SEARCH_PATHS = [
    r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
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

# UI configuration
UI_PADDING = "10"
UI_FONT_DEFAULT = ('Arial', 10)
UI_FONT_LARGE = ('Arial', 12)
UI_FONT_BUTTON = ('Arial', 14, 'bold')

# File types
FREECAD_FILETYPES = [("FreeCAD files", "*.FCStd"), ("All files", "*.*")]
EXECUTABLE_FILETYPES = [("Executable files", "*.exe"), ("All files", "*.*")]

# Processing timeouts
FREECAD_TIMEOUT = 120  # seconds
PARAM_SCAN_TIMEOUT = 60  # seconds

# Runner script filename
RUNNER_SCRIPT_NAME = "_runner.py"

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class ParametricGenerator:
    """
    Main application class for the FreeCAD Parametric Generator.
    Handles UI setup, user input validation, and FreeCAD execution.
    """
    
    def __init__(self):
        """Initialize the application and set up the UI."""
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(APP_GEOMETRY)
        self.root.resizable(True, True)
        
        self._initialize_variables()
        self._auto_detect_freecad()
        self._setup_ui()
        
    # ───────────────────────────────────────────────────────────────────────────
    # INITIALIZATION METHODS
    # ───────────────────────────────────────────────────────────────────────────
    
    def _initialize_variables(self):
        """Initialize all UI variables."""
        self.template_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.freecad_path = tk.StringVar()
        self.parameter_entries = []
        self.stl_var = tk.BooleanVar(value=True)

    def _auto_detect_freecad(self):
        """
        Auto-detect FreeCAD installation on Windows.
        Checks common installation paths and uses glob patterns as fallback.
        """
        # First try predefined common paths
        for path in FREECAD_SEARCH_PATHS:
            if os.path.isfile(path):
                self.freecad_path.set(path)
                print(f"Auto-detected FreeCAD: {path}")
                return
                
        # Fallback: Search using glob patterns
        self._search_freecad_with_glob()
            
    def _search_freecad_with_glob(self):
        """Search for FreeCAD using glob patterns as fallback."""
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
        except Exception:
            pass
            
        print("FreeCAD not found automatically. Please browse for FreeCADCmd.exe")
    
    # ───────────────────────────────────────────────────────────────────────────
    # USER INTERFACE SETUP
    # ───────────────────────────────────────────────────────────────────────────
                
    def _setup_ui(self):
        """Set up the complete Tkinter user interface."""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding=UI_PADDING)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive design
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Build UI sections
        row = 0
        row = self._create_parameters_section(main_frame, row)
        row = self._create_file_selection_section(main_frame, row)
        row = self._create_export_section(main_frame, row)
        row = self._create_action_section(main_frame, row)
        row = self._create_status_section(main_frame, row)
        
        # Initial status message
        self._log_message("Ready. Select template file, output folder, enter parameters, and click Generate.")
    
    def _create_parameters_section(self, parent, start_row):
        """Create the dynamic parameters input section."""
        self.params_frame = ttk.LabelFrame(parent, text="Template Parameters", padding="5")
        self.params_frame.grid(row=start_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.params_frame.columnconfigure(1, weight=1)

        self.params_hint = ttk.Label(
            self.params_frame,
            text="Select a template to auto-load labels from column A and values from column B."
        )
        self.params_hint.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        return start_row + 1
    
    def _create_file_selection_section(self, parent, start_row):
        """Create the file and folder selection section."""
        file_selections = [
            ("FreeCAD Template:", self.template_path, self._browse_template),
            ("Output Folder:", self.output_path, self._browse_output),
            ("FreeCADCmd.exe:", self.freecad_path, self._browse_freecad)
        ]
        
        current_row = start_row
        for label_text, variable, browse_command in file_selections:
            ttk.Label(parent, text=label_text).grid(
                row=current_row, column=0, sticky=tk.W, pady=5
            )
            ttk.Entry(parent, textvariable=variable, font=UI_FONT_DEFAULT).grid(
                row=current_row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5
            )
            ttk.Button(parent, text="Browse", command=browse_command).grid(
                row=current_row, column=2, padx=5, pady=5
            )
            current_row += 1
            
        return current_row
    
    def _create_export_section(self, parent, start_row):
        """Create the export format selection section."""
        export_frame = ttk.LabelFrame(parent, text="Export Format", padding="5")
        export_frame.grid(row=start_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Checkbutton(
            export_frame, text="STL", variable=self.stl_var, state='disabled'
        ).grid(row=0, column=0, sticky=tk.W)
        
        return start_row + 1
    
    def _create_action_section(self, parent, start_row):
        """Create the action buttons section."""
        self.generate_btn = ttk.Button(
            parent, text="Generate", command=self._generate, style='Generate.TButton'
        )
        self.generate_btn.grid(
            row=start_row, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E)
        )
        
        # Configure button style
        style = ttk.Style()
        style.configure('Generate.TButton', font=UI_FONT_BUTTON)
        
        return start_row + 1
    
    def _create_status_section(self, parent, start_row):
        """Create the status display section."""
        ttk.Label(parent, text="Status:").grid(
            row=start_row, column=0, sticky=(tk.W, tk.N), pady=5
        )
        
        self.status_text = scrolledtext.ScrolledText(parent, height=10, wrap=tk.WORD)
        self.status_text.grid(
            row=start_row + 1, column=0, columnspan=3, 
            sticky=(tk.W, tk.E, tk.N, tk.S), pady=5
        )
        parent.rowconfigure(start_row + 1, weight=1)
        
        return start_row + 2
    
    # ───────────────────────────────────────────────────────────────────────────
    # FILE BROWSER METHODS
    # ───────────────────────────────────────────────────────────────────────────
        
    def _browse_template(self):
        """Browse for FreeCAD template file."""
        filename = filedialog.askopenfilename(
            title="Select FreeCAD Template",
            filetypes=FREECAD_FILETYPES
        )
        if filename:
            self.template_path.set(filename)
            self._load_parameters_from_template()
            
    def _browse_output(self):
        """Browse for output folder."""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path.set(folder)
            
    def _browse_freecad(self):
        """Browse for FreeCAD executable."""
        filename = filedialog.askopenfilename(
            title="Select FreeCADCmd.exe",
            filetypes=EXECUTABLE_FILETYPES
        )
        if filename:
            self.freecad_path.set(filename)
    
    # ───────────────────────────────────────────────────────────────────────────
    # UTILITY METHODS
    # ───────────────────────────────────────────────────────────────────────────
            
    def _log_message(self, message):
        """Add message to status area with thread safety."""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    # ───────────────────────────────────────────────────────────────────────────
    # VALIDATION METHODS
    # ───────────────────────────────────────────────────────────────────────────
        
    def _validate_inputs(self):
        """
        Validate all user inputs before processing.
        
        Returns:
            list: List of validation error messages (empty if all valid)
        """
        validation_errors = []
        
        # Validate template file
        if not self.template_path.get() or not os.path.isfile(self.template_path.get()):
            validation_errors.append("Please select a valid template file")
            
        # Validate output folder
        if not self.output_path.get() or not os.path.isdir(self.output_path.get()):
            validation_errors.append("Please select a valid output folder")
            
        # Validate FreeCAD executable
        if not self.freecad_path.get() or not os.path.isfile(self.freecad_path.get()):
            validation_errors.append("Please select FreeCADCmd.exe")
            
        # Validate parameters loaded from template
        if not self.parameter_entries:
            validation_errors.append("No parameters loaded. Select a template with values in column B from B2 downward")
        else:
            missing = [p["label"] for p in self.parameter_entries if not p["var"].get().strip()]
            if missing:
                validation_errors.append("Please enter all parameter values")
            
        return validation_errors
    
    # ───────────────────────────────────────────────────────────────────────────
    # GENERATION PROCESS METHODS
    # ───────────────────────────────────────────────────────────────────────────
        
        
    def _generate(self):
        """
        Main generation process - coordinates the entire workflow.
        Runs in the main thread with UI updates.
        """
        # Disable UI during processing
        self._set_ui_state(False)
        self.status_text.delete('1.0', tk.END)
        self._log_message("Starting generation")
        
        try:
            if not self.parameter_entries:
                self._load_parameters_from_template()

            # Step 1: Validate inputs
            validation_errors = self._validate_inputs()
            if validation_errors:
                for error in validation_errors:
                    self._log_message(f"✗ {error}")
                return
                
            # Step 2: Prepare processing environment
            runner_path = self._prepare_runner_script()
            if not runner_path:
                self._log_message("✗ Failed to create runner script")
                return
                
            # Step 3: Execute FreeCAD process
            success = self._execute_freecad_process(runner_path)
            
            # Step 4: Report results
            if success:
                self._log_message("✓ Generation completed successfully")
            else:
                self._log_message("✗ Generation failed")
                
        except Exception as e:
            self._log_message(f"✗ Unexpected error: {str(e)}")
            
        finally:
            # Clean up and re-enable UI
            self._cleanup_temp_files()
            self._set_ui_state(True)
            
    def _set_ui_state(self, enabled):
        """Enable or disable UI controls during processing."""
        state = 'normal' if enabled else 'disabled'
        self.generate_btn.configure(state=state)
        
    def _prepare_runner_script(self):
        """
        Create and write the Python runner script for FreeCAD execution.
        
        Returns:
            str: Path to the created runner script, or None if failed
        """
        try:
            runner_script_content = self._create_runner_script_content()
            runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), RUNNER_SCRIPT_NAME)
            
            with open(runner_path, 'w', encoding='utf-8') as script_file:
                script_file.write(runner_script_content)
                
            self._log_message("✓ Created runner script")
            return runner_path
            
        except Exception as e:
            self._log_message(f"✗ Failed to create runner script: {e}")
            return None
            
    def _execute_freecad_process(self, runner_path):
        """
        Execute FreeCAD with the prepared runner script.
        
        Args:
            runner_path (str): Path to the runner script
            
        Returns:
            bool: True if execution was successful, False otherwise
        """
        try:
            # Read script content
            with open(runner_path, 'r', encoding='utf-8') as script_file:
                script_content = script_file.read()
            
            # Prepare command and environment
            command = [self.freecad_path.get(), "-c", script_content]
            environment = self._prepare_environment()
            
            self._log_message("Running...")
            
            # Execute FreeCAD
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True,
                cwd=os.path.dirname(self.template_path.get()), 
                timeout=FREECAD_TIMEOUT, 
                env=environment
            )
            
            # Check results
            return self._process_execution_result(result)
            
        except subprocess.TimeoutExpired:
            self._log_message("✗ Process timed out")
            return False
        except Exception as e:
            self._log_message(f"✗ Execution failed: {e}")
            return False
            
    def _prepare_environment(self):
        """
        Prepare environment variables for FreeCAD execution.
        
        Returns:
            dict: Environment variables dictionary
        """
        environment = os.environ.copy()
        
        params_payload = [
            {
                "row": p["row"],
                "label": p["label"],
                "value": p["var"].get(),
            }
            for p in self.parameter_entries
        ]

        # Set FreeCAD-specific environment variables
        environment.update({
            'FREECAD_TEMPLATE': self.template_path.get(),
            'FREECAD_OUTPUT': self.output_path.get(),
            'FREECAD_BASE': self._generate_filename_base(),
            'FREECAD_PARAMS_JSON': json.dumps(params_payload)
        })
        
        return environment
        
    def _generate_filename_base(self):
        """
        Generate base filename for output files.
        
        Returns:
            str: Base filename without extension
        """
        template_base = os.path.splitext(os.path.basename(self.template_path.get()))[0]
        return f"{template_base}_generated"
        
    def _process_execution_result(self, result):
        """
        Process the result of FreeCAD execution.
        
        Args:
            result: subprocess.CompletedProcess result
            
        Returns:
            bool: True if successful, False otherwise
        """
        if result.returncode == 0:
            self._log_message("Done")
            return True
        else:
            self._log_message("Failed")
            # Optionally log stderr for debugging
            if result.stderr:
                self._log_message(f"Error details: {result.stderr[:200]}...")
            return False
            
    def _cleanup_temp_files(self):
        """Clean up temporary files created during processing."""
        try:
            runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), RUNNER_SCRIPT_NAME)
            if os.path.exists(runner_path):
                os.remove(runner_path)
        except Exception:
            pass  # Ignore cleanup errors

    def _load_parameters_from_template(self):
        """Load parameter labels/values from Spreadsheet A/B starting at row 2 until B is empty."""
        template = self.template_path.get().strip()
        freecad_cmd = self.freecad_path.get().strip()

        if not template or not os.path.isfile(template):
            return False
        if not freecad_cmd or not os.path.isfile(freecad_cmd):
            self._log_message("Please select FreeCADCmd.exe before loading parameters")
            return False

        env = os.environ.copy()
        env['FREECAD_TEMPLATE'] = template

        command = [freecad_cmd, "-c", self._create_param_scan_script_content()]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=os.path.dirname(template),
                timeout=PARAM_SCAN_TIMEOUT,
                env=env
            )
        except Exception as exc:
            self._log_message(f"Failed to read template parameters: {exc}")
            return False

        params = self._extract_params_from_output(result.stdout)
        if result.returncode != 0 or params is None:
            self._log_message("Could not auto-load parameters from template")
            return False

        if not params:
            self._rebuild_parameter_inputs([])
            self._log_message("No parameters found. Fill column B from B2 downward in the template")
            return False

        self._rebuild_parameter_inputs(params)
        self._log_message(f"Loaded {len(params)} parameter(s) from template")
        return True

    def _extract_params_from_output(self, output_text):
        """Parse JSON payload emitted by the parameter scanner script."""
        begin_marker = "PARAM_SCAN_BEGIN"
        end_marker = "PARAM_SCAN_END"
        begin = output_text.find(begin_marker)
        end = output_text.find(end_marker)
        if begin == -1 or end == -1 or end <= begin:
            return None

        payload = output_text[begin + len(begin_marker):end].strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, list):
            return None
        return data

    def _rebuild_parameter_inputs(self, parameters):
        """Rebuild dynamic parameter fields in the UI."""
        for child in self.params_frame.winfo_children():
            child.destroy()

        self.parameter_entries = []

        if not parameters:
            self.params_hint = ttk.Label(
                self.params_frame,
                text="No parameters detected. B2, B3, ... must contain values; A cells provide labels."
            )
            self.params_hint.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
            return

        self.params_frame.columnconfigure(1, weight=1)
        for i, item in enumerate(parameters):
            row_number = int(item.get("row", 0))
            label_text = str(item.get("label", "")).strip() or f"Parameter {row_number}"
            value_text = str(item.get("value", ""))
            cell_ref = str(item.get("cell", f"C{row_number}"))

            var = tk.StringVar(value=value_text)
            display_label = f"{label_text} ({cell_ref}):"

            ttk.Label(self.params_frame, text=display_label).grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=2
            )
            ttk.Entry(self.params_frame, textvariable=var, font=UI_FONT_LARGE).grid(
                row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2
            )

            self.parameter_entries.append(
                {
                    "row": row_number,
                    "label": label_text,
                    "var": var,
                }
            )
    
    # ───────────────────────────────────────────────────────────────────────────
    # FREECAD SCRIPT GENERATION
    # ───────────────────────────────────────────────────────────────────────────
                
    def _create_runner_script_content(self):
        """
        Generate the Python script content to be executed by FreeCAD.
        
        Returns:
            str: Complete Python script for FreeCAD execution
        """
        return textwrap.dedent('''
            import sys
            import os
            import json

            try:
                template_file = os.environ['FREECAD_TEMPLATE']
                output_folder = os.environ['FREECAD_OUTPUT']
                filename_base = os.environ['FREECAD_BASE']
                params_json = os.environ['FREECAD_PARAMS_JSON']
                params = json.loads(params_json)

                import FreeCAD

                doc = FreeCAD.openDocument(template_file)

                for obj in doc.Objects:
                    if hasattr(obj, 'TypeId') and obj.TypeId == 'Spreadsheet::Sheet':
                        try:
                            for item in params:
                                row = int(item['row'])
                                value = str(item['value'])

                                # Keep it simple: write to Input column C, fallback to Output column B.
                                wrote = False
                                try:
                                    obj.set(f'C{row}', value)
                                    wrote = True
                                except Exception:
                                    pass

                                if not wrote:
                                    try:
                                        obj.set(f'B{row}', value)
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        break

                doc.recompute()

                for obj in doc.Objects:
                    if obj.Name == "Body":
                        import Mesh
                        stl_file_path = os.path.join(output_folder, f"{filename_base}.stl")
                        Mesh.export([obj], stl_file_path)
                        break

                FreeCAD.closeDocument(doc.Name)

            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
        ''').strip() + "\n"

    def _create_param_scan_script_content(self):
        """Generate a FreeCAD script that reads labels from A and values from B starting at row 2."""
        return textwrap.dedent('''
            import os
            import sys
            import json

            try:
                template_file = os.environ['FREECAD_TEMPLATE']
                import FreeCAD

                doc = FreeCAD.openDocument(template_file)
                rows = []

                sheet = None
                for obj in doc.Objects:
                    if hasattr(obj, 'TypeId') and obj.TypeId == 'Spreadsheet::Sheet':
                        sheet = obj
                        break

                if sheet is not None:
                    row = 2
                    while True:
                        try:
                            b_value = sheet.get(f'B{row}')
                        except Exception:
                            b_value = ''

                        if b_value is None or str(b_value).strip() == '':
                            break

                        try:
                            a_label = sheet.get(f'A{row}')
                        except Exception:
                            a_label = ''

                        output_cell = f'B{row}'
                        input_cell = f'C{row}'

                        try:
                            input_contents = sheet.getContents(input_cell)
                        except Exception:
                            input_contents = ''

                        try:
                            input_value = sheet.get(input_cell)
                        except Exception:
                            input_value = ''

                        # Prefer explicit input column C when present.
                        target_cell = output_cell
                        use_input_column = str(input_contents).strip() != '' or str(input_value).strip() != ''
                        if use_input_column:
                            target_cell = input_cell

                        label = str(a_label).strip() if a_label is not None else ''
                        if not label:
                            label = f'Parameter {row}'

                        # Show/edit the source value from the chosen target cell.
                        value_for_ui = b_value
                        if target_cell == input_cell and str(input_value).strip() != '':
                            value_for_ui = input_value

                        rows.append({
                            'row': row,
                            'label': label,
                            'cell': target_cell,
                            'value': str(value_for_ui)
                        })
                        row += 1

                print('PARAM_SCAN_BEGIN')
                print(json.dumps(rows))
                print('PARAM_SCAN_END')

                if doc is not None:
                    FreeCAD.closeDocument(doc.Name)
            except Exception:
                print('PARAM_SCAN_BEGIN')
                print('[]')
                print('PARAM_SCAN_END')
                sys.exit(1)
        ''').strip() + "\n"


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """
    Application entry point.
    Creates and runs the main application instance.
    """
    try:
        app = ParametricGenerator()
        app.root.mainloop()
    except Exception as e:
        print(f"Application startup failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
