#!/usr/bin/env python3
"""
FreeCAD Parametric Generator
A minimal Windows desktop app that updates FreeCAD spreadsheet inputs and exports STL.
"""

# ============================================================================
# IMPORTS
# ============================================================================

import json
import math
import os
import subprocess
import sys
import textwrap
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk

import pyvista as pv

# ============================================================================
# GLOBAL CONFIGURATION
# ============================================================================

APP_TITLE = "FreeCAD Parametric Generator"
APP_VERSION = "1.0"
APP_GEOMETRY = "600x700"

FREECAD_TIMEOUT = 120
PARAM_SCAN_TIMEOUT = 60
PREVIEW_TIMEOUT = 60
PREVIEW_STL_NAME = "_preview.stl"
PREVIEW_IMAGE_NAME = "_preview.png"

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

        self.preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PREVIEW_STL_NAME)
        self.preview_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PREVIEW_IMAGE_NAME)
        self.preview_yaw = -0.7
        self.preview_pitch = 0.45
        self.preview_after_id = None
        self.preview_drag_last = None
        self.preview_photo = None
        self._pyvista_error_logged = False

        self._auto_detect_freecad()
        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._log("Preview renderer: PyVista/VTK (realistic)")

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

        self.preview_frame = ttk.LabelFrame(main, text="Live Preview", padding="5")
        self.preview_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N), pady=5)
        self.preview_frame.columnconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(self.preview_frame, height=220, bg="#121212", highlightthickness=1)
        self.preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.preview_frame.rowconfigure(0, weight=1)

        self.preview_canvas.bind("<Configure>", lambda _e: self._render_preview())
        self.preview_canvas.bind("<ButtonPress-1>", self._on_preview_press)
        self.preview_canvas.bind("<B1-Motion>", self._on_preview_drag)
        self._draw_preview_message("Preview will appear here")
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
            self._schedule_preview()

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
            var.trace_add("write", lambda *_: self._schedule_preview())
            row_wrap = ttk.Frame(self.params_frame)
            row_wrap.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)

            ttk.Label(row_wrap, text=f"{label} (Row {row_number}):").pack(side=tk.LEFT)
            ttk.Entry(self.params_frame, textvariable=var).grid(
                row=i, column=1, sticky=(tk.W, tk.E), padx=5, pady=2
            )

            self.parameter_entries.append({"row": row_number, "label": label, "var": var})

        self._schedule_preview()

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
                self._schedule_preview()
            else:
                self._log("Failed")
                if result.stderr:
                    self._log(f"Error details: {result.stderr[:500]}")

        except Exception as exc:
            self._log(f"X Unexpected error: {exc}")
        finally:
            self._set_ui_state(True)

    # ------------------------------------------------------------------------
    # LIVE PREVIEW
    # ------------------------------------------------------------------------

    def _schedule_preview(self):
        if self.preview_after_id is not None:
            self.root.after_cancel(self.preview_after_id)
        self.preview_after_id = self.root.after(650, self._run_live_preview)

    def _run_live_preview(self):
        self.preview_after_id = None

        if not self.template_path.get() or not os.path.isfile(self.template_path.get()):
            self._draw_preview_message("Select a template to preview")
            return
        if not self.freecad_path.get() or not os.path.isfile(self.freecad_path.get()):
            self._draw_preview_message("Select FreeCADCmd.exe")
            return
        if not self.parameter_entries:
            self._draw_preview_message("No parameters loaded")
            return

        env = os.environ.copy()
        env["FREECAD_TEMPLATE"] = self.template_path.get()
        env["FREECAD_PARAMS_JSON"] = json.dumps(
            [{"row": p["row"], "value": p["var"].get()} for p in self.parameter_entries]
        )
        env["FREECAD_PREVIEW_PATH"] = self.preview_path

        result = self._run_freecad_script(
            self._create_runner_script(),
            env=env,
            cwd=os.path.dirname(self.template_path.get()),
            timeout=PREVIEW_TIMEOUT,
        )

        if result is None or result.returncode != 0:
            self._draw_preview_message("Preview failed")
            return
        if not os.path.isfile(self.preview_path):
            self._draw_preview_message("No preview mesh generated")
            return

        self._render_preview()

    def _render_preview_pyvista(self, width, height):
        if not os.path.isfile(self.preview_path):
            return False

        plotter = None
        try:
            mesh = pv.read(self.preview_path)
            if mesh is None or mesh.n_points == 0:
                return False

            win_w = max(120, int(width))
            win_h = max(120, int(height))
            plotter = pv.Plotter(off_screen=True, window_size=(win_w, win_h), lighting="none")
            plotter.set_background("#101216")

            mesh_color = "#d6d9de"
            plotter.add_mesh(
                mesh,
                color=mesh_color,
                smooth_shading=True,
                ambient=0.25,
                diffuse=0.75,
                specular=0.35,
                specular_power=24,
                show_edges=False,
            )

            # Subtle silhouette/feature edges to keep shape readability.
            try:
                feature_edges = mesh.extract_feature_edges(
                    boundary_edges=True,
                    feature_edges=True,
                    manifold_edges=False,
                    non_manifold_edges=False,
                    feature_angle=35,
                )
                if feature_edges is not None and feature_edges.n_points > 0:
                    plotter.add_mesh(feature_edges, color="#6f7882", line_width=1)
            except Exception:
                pass

            key = pv.Light(position=(3.2, 2.4, 4.1), focal_point=(0.0, 0.0, 0.0), color="white", intensity=1.0)
            fill = pv.Light(position=(-3.0, 1.8, 1.4), focal_point=(0.0, 0.0, 0.0), color="#d8deea", intensity=0.55)
            rim = pv.Light(position=(0.0, -4.0, 2.2), focal_point=(0.0, 0.0, 0.0), color="#f6f8ff", intensity=0.25)
            plotter.add_light(key)
            plotter.add_light(fill)
            plotter.add_light(rim)

            xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
            dx = xmax - xmin
            dy = ymax - ymin
            dz = zmax - zmin
            diag = max(1e-6, math.sqrt(dx * dx + dy * dy + dz * dz))
            dist = diag * 2.2
            center = mesh.center

            cam_x = center[0] + dist * math.cos(self.preview_pitch) * math.sin(self.preview_yaw)
            cam_y = center[1] + dist * math.sin(self.preview_pitch)
            cam_z = center[2] + dist * math.cos(self.preview_pitch) * math.cos(self.preview_yaw)
            plotter.camera_position = [(cam_x, cam_y, cam_z), center, (0.0, 1.0, 0.0)]
            plotter.camera.SetViewAngle(30)

            plotter.show(auto_close=False)
            plotter.screenshot(filename=self.preview_image_path, transparent_background=False)
            plotter.close()
            plotter = None

            if os.path.isfile(self.preview_image_path):
                self.preview_photo = tk.PhotoImage(file=self.preview_image_path)
                self.preview_canvas.delete("all")
                self.preview_canvas.create_image(width * 0.5, height * 0.5, image=self.preview_photo)
                return True

            return False
        except Exception as exc:
            if not self._pyvista_error_logged:
                self._log(f"PyVista preview failed: {exc}")
                self._pyvista_error_logged = True
            return False
        finally:
            if plotter is not None:
                try:
                    plotter.close()
                except Exception:
                    pass

    def _render_preview(self):
        self.preview_canvas.delete("all")

        if self._render_preview_pyvista(
            max(10, self.preview_canvas.winfo_width()),
            max(10, self.preview_canvas.winfo_height()),
        ):
            return

        self._draw_preview_message("PyVista preview failed")
        return

    def _draw_preview_message(self, message):
        self.preview_canvas.delete("all")
        w = max(10, self.preview_canvas.winfo_width())
        h = max(10, self.preview_canvas.winfo_height())
        self.preview_canvas.create_text(w // 2, h // 2, text=message, fill="#d0d0d0")

    def _on_preview_press(self, event):
        self.preview_drag_last = (event.x, event.y)

    def _on_preview_drag(self, event):
        if self.preview_drag_last is None:
            self.preview_drag_last = (event.x, event.y)
            return
        last_x, last_y = self.preview_drag_last
        dx = event.x - last_x
        dy = event.y - last_y
        self.preview_drag_last = (event.x, event.y)

        self.preview_yaw += dx * 0.01
        self.preview_pitch += dy * 0.01
        self._render_preview()

    def _on_close(self):
        try:
            if os.path.exists(self.preview_path):
                os.remove(self.preview_path)
            if os.path.exists(self.preview_image_path):
                os.remove(self.preview_image_path)
        except Exception:
            pass
        self.root.destroy()

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
                params = json.loads(os.environ['FREECAD_PARAMS_JSON'])
                output_folder = os.environ.get('FREECAD_OUTPUT', '')
                filename_base = os.environ.get('FREECAD_BASE', '')
                preview_path = os.environ.get('FREECAD_PREVIEW_PATH', '')

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
                        if preview_path:
                            Mesh.export([obj], preview_path)
                        elif output_folder and filename_base:
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
