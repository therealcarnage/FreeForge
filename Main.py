#!/usr/bin/env python3
"""
FreeCAD Parametric Generator
A minimal Windows desktop app that updates FreeCAD spreadsheet inputs and exports STL.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import json
import os
import subprocess
import sys
import textwrap
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

APP_TITLE = "FreeCAD Parametric Generator"
APP_VERSION = "1.0"
APP_GEOMETRY = "600x700"

FREECAD_TIMEOUT = 120
PARAM_SCAN_TIMEOUT = 60
RUNNER_SCRIPT_NAME = "_runner.py"

FREECAD_FILETYPES = [("FreeCAD files", "*.FCStd"), ("All files", "*.*")]
EXECUTABLE_FILETYPES = [("Executable files", "*.exe"), ("All files", "*.*")]

FREECAD_SEARCH_PATHS = [
    r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 1.0\bin\freecadcmd.exe",
    r"C:\Program Files\FreeCAD 0.23\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD 0.22\bin\FreeCADCmd.exe",
    r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
    r"C:\Program Files (x86)\FreeCAD 1.0\bin\FreeCADCmd.exe",
    r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe",
]

# ============================================================================
# MAIN APPLICATION
# ============================================================================


class ParametricGenerator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_TITLE} v{APP_VERSION}")
        self.root.geometry(APP_GEOMETRY)
        self.root.resizable(True, True)

        self.template_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.freecad_path = tk.StringVar()
        self.parameter_entries = []

        self._auto_detect_freecad()
        self._setup_ui()

    # ------------------------------------------------------------------------
    # UI SETUP
    # ------------------------------------------------------------------------

    def _setup_ui(self):
        main = ttk.Frame(self.root, padding="10")
        main.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)

        row = 0

        self.params_frame = ttk.LabelFrame(main, text="Template Parameters", padding="5")
        self.params_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.params_frame.columnconfigure(1, weight=1)
        self.params_hint = ttk.Label(
            self.params_frame,
            text="Select template to auto-load A/B/C spreadsheet parameters.",
        )
        self.params_hint.grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)
        row += 1

        self._path_row(main, row, "FreeCAD Template:", self.template_path, self._browse_template)
        row += 1
        self._path_row(main, row, "Output Folder:", self.output_path, self._browse_output)
        row += 1
        self._path_row(main, row, "FreeCADCmd.exe:", self.freecad_path, self._browse_freecad)
        row += 1

        self.generate_btn = ttk.Button(main, text="Generate", command=self._generate)
        self.generate_btn.grid(row=row, column=0, columnspan=3, pady=20, sticky=(tk.W, tk.E))
        row += 1

        ttk.Label(main, text="Status:").grid(row=row, column=0, sticky=(tk.W, tk.N), pady=5)
        row += 1

        self.status_text = scrolledtext.ScrolledText(main, height=10, wrap=tk.WORD)
        self.status_text.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main.rowconfigure(row, weight=1)

        self._log("Ready. Select template, output folder, set values, then Generate.")

    def _path_row(self, parent, row, label, var, browse_cmd):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        ttk.Button(parent, text="Browse", command=browse_cmd).grid(row=row, column=2, padx=5, pady=5)

    # ------------------------------------------------------------------------
    # BROWSE / STATUS
    # ------------------------------------------------------------------------

    def _browse_template(self):
        filename = filedialog.askopenfilename(title="Select FreeCAD Template", filetypes=FREECAD_FILETYPES)
        if filename:
            self.template_path.set(filename)
            self._load_parameters_from_template()

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path.set(folder)

    def _browse_freecad(self):
        filename = filedialog.askopenfilename(title="Select FreeCADCmd.exe", filetypes=EXECUTABLE_FILETYPES)
        if filename:
            self.freecad_path.set(filename)

    def _log(self, message):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()

    # ------------------------------------------------------------------------
    # FREECAD DISCOVERY
    # ------------------------------------------------------------------------

    def _auto_detect_freecad(self):
        for path in FREECAD_SEARCH_PATHS:
            if os.path.isfile(path):
                self.freecad_path.set(path)
                print(f"Auto-detected FreeCAD: {path}")
                return

    # ------------------------------------------------------------------------
    # PARAMETER LOADING
    # ------------------------------------------------------------------------

    def _load_parameters_from_template(self):
        template = self.template_path.get().strip()
        freecad_cmd = self.freecad_path.get().strip()

        if not template or not os.path.isfile(template):
            return False
        if not freecad_cmd or not os.path.isfile(freecad_cmd):
            self._log("Please select FreeCADCmd.exe first.")
            return False

        env = os.environ.copy()
        env["FREECAD_TEMPLATE"] = template

        result = self._run_freecad_script(
            self._create_param_scan_script(),
            env=env,
            cwd=os.path.dirname(template),
            timeout=PARAM_SCAN_TIMEOUT,
        )

        if result is None:
            self._log("Could not load parameters from template.")
            return False

        params = self._extract_payload(result.stdout)
        if result.returncode != 0 or params is None:
            self._log("Could not load parameters from template.")
            return False

        if not params:
            self._rebuild_parameter_inputs([])
            self._log("No parameters found.")
            return False

        self._rebuild_parameter_inputs(params)
        self._log(f"Loaded {len(params)} parameter(s).")
        return True

    def _extract_payload(self, output_text):
        begin = output_text.find("PARAM_SCAN_BEGIN")
        end = output_text.find("PARAM_SCAN_END")
        if begin == -1 or end == -1 or end <= begin:
            return None

        payload = output_text[begin + len("PARAM_SCAN_BEGIN") : end].strip()
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return None

        return data if isinstance(data, list) else None

    def _rebuild_parameter_inputs(self, parameters):
        for child in self.params_frame.winfo_children():
            child.destroy()

        self.parameter_entries = []

        if not parameters:
            ttk.Label(self.params_frame, text="No parameters detected.").grid(
                row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2
            )
            return

        self.params_frame.columnconfigure(1, weight=1)

        for i, item in enumerate(parameters):
            row_number = int(item.get("row", 0))
            label = str(item.get("label", "")).strip() or f"Parameter {row_number}"
            value = str(item.get("value", ""))

            var = tk.StringVar(value=value)
            ttk.Label(self.params_frame, text=f"{label} (Row {row_number}):").grid(
                row=i, column=0, sticky=tk.W, padx=5, pady=2
            )
            ttk.Entry(self.params_frame, textvariable=var).grid(
                row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2
            )

            self.parameter_entries.append({"row": row_number, "label": label, "var": var})

    # ------------------------------------------------------------------------
    # GENERATION
    # ------------------------------------------------------------------------

    def _validate_inputs(self):
        errors = []

        if not self.template_path.get() or not os.path.isfile(self.template_path.get()):
            errors.append("Please select a valid template file")

        if not self.output_path.get() or not os.path.isdir(self.output_path.get()):
            errors.append("Please select a valid output folder")

        if not self.freecad_path.get() or not os.path.isfile(self.freecad_path.get()):
            errors.append("Please select FreeCADCmd.exe")

        if not self.parameter_entries:
            errors.append("No parameters loaded")
        else:
            for p in self.parameter_entries:
                if not p["var"].get().strip():
                    errors.append("Please enter all parameter values")
                    break

        return errors

    def _set_ui_state(self, enabled):
        self.generate_btn.configure(state="normal" if enabled else "disabled")

    def _prepare_environment(self):
        params_payload = [
            {"row": p["row"], "label": p["label"], "value": p["var"].get()}
            for p in self.parameter_entries
        ]

        env = os.environ.copy()
        env.update(
            {
                "FREECAD_TEMPLATE": self.template_path.get(),
                "FREECAD_OUTPUT": self.output_path.get(),
                "FREECAD_BASE": self._generate_filename_base(),
                "FREECAD_PARAMS_JSON": json.dumps(params_payload),
            }
        )
        return env

    def _generate_filename_base(self):
        base = os.path.splitext(os.path.basename(self.template_path.get()))[0]
        return f"{base}_generated"

    def _generate(self):
        self._set_ui_state(False)
        self.status_text.delete("1.0", tk.END)
        self._log("Starting generation")

        try:
            if not self.parameter_entries:
                self._load_parameters_from_template()

            errors = self._validate_inputs()
            if errors:
                for err in errors:
                    self._log(f"X {err}")
                return

            runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), RUNNER_SCRIPT_NAME)
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(self._create_runner_script())

            self._log("Running...")
            result = self._run_freecad_script(
                self._create_runner_script(),
                env=self._prepare_environment(),
                cwd=os.path.dirname(self.template_path.get()),
                timeout=FREECAD_TIMEOUT,
            )

            if result is None:
                self._log("Failed")
                return

            if result.returncode == 0:
                self._log("Done")
            else:
                self._log("Failed")
                if result.stderr:
                    self._log(f"Error details: {result.stderr[:500]}")

        except Exception as exc:
            self._log(f"X Unexpected error: {exc}")
        finally:
            self._cleanup_temp_files()
            self._set_ui_state(True)

    def _cleanup_temp_files(self):
        try:
            runner_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), RUNNER_SCRIPT_NAME)
            if os.path.exists(runner_path):
                os.remove(runner_path)
        except Exception:
            pass

    # ------------------------------------------------------------------------
    # FREECAD SCRIPT EXECUTION
    # ------------------------------------------------------------------------

    def _run_freecad_script(self, script_content, env, cwd, timeout):
        try:
            command = [self.freecad_path.get(), "-c", script_content]
            return subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            self._log("X Process timed out")
            return None
        except Exception as exc:
            self._log(f"X Execution failed: {exc}")
            return None

    def _create_runner_script(self):
        return textwrap.dedent(
            '''
            import json
            import os
            import sys

            try:
                template_file = os.environ['FREECAD_TEMPLATE']
                output_folder = os.environ['FREECAD_OUTPUT']
                filename_base = os.environ['FREECAD_BASE']
                params = json.loads(os.environ['FREECAD_PARAMS_JSON'])

                import FreeCAD
                import Mesh

                doc = FreeCAD.openDocument(template_file)

                sheet = None
                for obj in doc.Objects:
                    if getattr(obj, 'TypeId', '') == 'Spreadsheet::Sheet':
                        sheet = obj
                        break

                if sheet is not None:
                    for item in params:
                        row = int(item['row'])
                        value = str(item['value'])

                        wrote = False
                        try:
                            sheet.set(f'C{row}', value)
                            wrote = True
                        except Exception:
                            pass

                        if not wrote:
                            try:
                                sheet.set(f'B{row}', value)
                            except Exception:
                                pass

                doc.recompute()

                for obj in doc.Objects:
                    if obj.Name == 'Body':
                        stl_file = os.path.join(output_folder, f"{filename_base}.stl")
                        Mesh.export([obj], stl_file)
                        break

                FreeCAD.closeDocument(doc.Name)
            except Exception as e:
                print(f"Error: {e}")
                sys.exit(1)
            '''
        ).strip() + "\n"

    def _create_param_scan_script(self):
        return textwrap.dedent(
            '''
            import json
            import os
            import sys

            try:
                template_file = os.environ['FREECAD_TEMPLATE']

                import FreeCAD

                doc = FreeCAD.openDocument(template_file)
                rows = []

                sheet = None
                for obj in doc.Objects:
                    if getattr(obj, 'TypeId', '') == 'Spreadsheet::Sheet':
                        sheet = obj
                        break

                if sheet is not None:
                    row = 2
                    while True:
                        try:
                            b_value = sheet.get(f'B{row}')
                        except Exception:
                            b_value = ''

                        try:
                            c_value = sheet.get(f'C{row}')
                        except Exception:
                            c_value = ''

                        if str(b_value).strip() == '' and str(c_value).strip() == '':
                            break

                        try:
                            a_label = sheet.get(f'A{row}')
                        except Exception:
                            a_label = ''

                        label = str(a_label).strip() if a_label is not None else ''
                        if not label:
                            label = f'Parameter {row}'

                        value_for_ui = c_value if str(c_value).strip() != '' else b_value
                        rows.append({'row': row, 'label': label, 'value': str(value_for_ui)})
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
            '''
        ).strip() + "\n"


# ============================================================================
# ENTRY POINT
# ============================================================================


def main():
    try:
        app = ParametricGenerator()
        app.root.mainloop()
    except Exception as exc:
        print(f"Application startup failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
