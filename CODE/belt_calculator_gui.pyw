
"""
Timing Belt Calculator GUI v4

Features:
- Fixed-pulley and ratio-constrained pulley search.
- Physical geometry filtering.
- Per-pulley diameter constraints.
- Per-pulley diameter allowance.
- Per-pulley teeth-in-mesh constraints.
- Embedded McMaster-Carr 2MGT, 6 mm belt catalogue with part numbers and direct links.
- Help "?" popups with explanations and simple diagrams.
- File-Explorer-style column sorting by clicking result headers.
- Sorting modes for signed value or absolute magnitude on numeric columns.

Assumptions:
- Open belt between two external timing pulleys.
- Ratio convention is driven pulley teeth / driving pulley teeth.
- Pulley part geometry is generated separately in Onshape; McMaster linkage is for purchased belts.
"""

import csv
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
import re


# McMaster-Carr Precision High-Torque GT Timing Belts, 2MGT trade size,
# 6 mm width, 2 mm pitch. Key is belt tooth count.
# Source page/category: https://www.mcmaster.com/products/pulleys/manufacturer-equivalent-series~gates-powergrip-gt2/
MCMASTER_2MGT_6MM_BELTS = {
    50:  {"part": "7947K711", "length_mm": 100},
    56:  {"part": "7947K712", "length_mm": 112},
    62:  {"part": "7947K713", "length_mm": 124},
    63:  {"part": "7947K714", "length_mm": 126},
    67:  {"part": "7947K715", "length_mm": 134},
    68:  {"part": "7947K716", "length_mm": 136},
    70:  {"part": "7947K717", "length_mm": 140},
    76:  {"part": "7947K718", "length_mm": 152},
    79:  {"part": "7947K719", "length_mm": 158},
    80:  {"part": "7947K721", "length_mm": 160},
    82:  {"part": "7947K722", "length_mm": 164},
    86:  {"part": "7947K725", "length_mm": 172},
    90:  {"part": "7947K726", "length_mm": 180},
    93:  {"part": "7947K727", "length_mm": 186},
    96:  {"part": "7947K728", "length_mm": 192},
    100: {"part": "7947K729", "length_mm": 200},
    101: {"part": "7947K731", "length_mm": 202},
    106: {"part": "7947K732", "length_mm": 212},
    110: {"part": "7947K733", "length_mm": 220},
    116: {"part": "7947K734", "length_mm": 232},
    118: {"part": "7947K735", "length_mm": 236},
    120: {"part": "7947K736", "length_mm": 240},
    125: {"part": "7947K737", "length_mm": 250},
    126: {"part": "7947K738", "length_mm": 252},
    129: {"part": "7947K739", "length_mm": 258},
    140: {"part": "7947K741", "length_mm": 280},
    150: {"part": "7947K742", "length_mm": 300},
    160: {"part": "7947K743", "length_mm": 320},
    166: {"part": "7947K744", "length_mm": 332},
    175: {"part": "7947K745", "length_mm": 350},
    185: {"part": "7947K746", "length_mm": 370},
    190: {"part": "7947K747", "length_mm": 380},
    200: {"part": "7947K748", "length_mm": 400},
    210: {"part": "7947K749", "length_mm": 420},
    228: {"part": "7947K751", "length_mm": 456},
    244: {"part": "7947K753", "length_mm": 488},
    252: {"part": "7947K754", "length_mm": 504},
    264: {"part": "7947K755", "length_mm": 528},
    276: {"part": "7947K756", "length_mm": 552},
    288: {"part": "7947K757", "length_mm": 576},
    300: {"part": "7947K758", "length_mm": 600},
    320: {"part": "7947K759", "length_mm": 640},
    348: {"part": "7947K761", "length_mm": 696},
    372: {"part": "7947K762", "length_mm": 744},
    424: {"part": "7947K763", "length_mm": 848},
    582: {"part": "7947K764", "length_mm": 1164},
}

MCMASTER_CATEGORY_URL = "https://www.mcmaster.com/products/pulleys/manufacturer-equivalent-series~gates-powergrip-gt2/"


def mcmaster_part_url(part_number: str) -> str:
    return f"https://www.mcmaster.com/{part_number}/"


def belt_catalog_match(belt_teeth: int, pitch_mm: float, belt_width_mm: float) -> dict:
    if abs(pitch_mm - 2.0) < 1e-9 and abs(belt_width_mm - 6.0) < 1e-9:
        item = MCMASTER_2MGT_6MM_BELTS.get(int(belt_teeth))
        if item:
            return {
                "part": item["part"],
                "url": mcmaster_part_url(item["part"]),
                "catalog_note": "McMaster 2MGT, 6 mm wide",
            }
    return {"part": "", "url": "", "catalog_note": "No embedded McMaster match"}


def pitch_diameter(teeth: int, pitch_mm: float) -> float:
    return teeth * pitch_mm / math.pi


def check_diameter(teeth: int, pitch_mm: float, diameter_allowance_mm: float) -> float:
    return pitch_diameter(teeth, pitch_mm) + diameter_allowance_mm


def parse_ratio(text: str) -> float:
    text = text.strip()
    if ":" in text:
        left, right = text.split(":", 1)
        return float(left.strip()) / float(right.strip())
    return float(text)


def wrap_angles_rad(z1: int, z2: int, center_mm: float, pitch_mm: float) -> tuple[float, float]:
    d1 = pitch_diameter(z1, pitch_mm)
    d2 = pitch_diameter(z2, pitch_mm)
    delta = abs(d2 - d1)
    if center_mm <= delta / 2:
        raise ValueError("Center distance is too small for these pulley diameters.")
    beta = math.asin(delta / (2 * center_mm))
    small_wrap = math.pi - 2 * beta
    large_wrap = math.pi + 2 * beta
    return (small_wrap, large_wrap) if d1 <= d2 else (large_wrap, small_wrap)


def teeth_in_mesh(z_teeth: int, wrap_angle_rad: float) -> float:
    return z_teeth * wrap_angle_rad / (2 * math.pi)


def geometry_check(
    z1: int,
    z2: int,
    center_mm: float,
    pitch_mm: float,
    max_dia_1_mm: float | None = None,
    max_dia_2_mm: float | None = None,
    allowance_1_mm: float = 0.0,
    allowance_2_mm: float = 0.0,
    min_clearance_mm: float = 0.0,
    min_mesh_1: float = 6.0,
    min_mesh_2: float = 6.0,
) -> dict:
    messages = []
    if z1 <= 0 or z2 <= 0:
        return {"ok": False, "messages": ["Pulley tooth counts must be positive."]}

    pd1 = pitch_diameter(z1, pitch_mm)
    pd2 = pitch_diameter(z2, pitch_mm)
    cd1 = check_diameter(z1, pitch_mm, allowance_1_mm)
    cd2 = check_diameter(z2, pitch_mm, allowance_2_mm)

    # Belt tangent condition for an open belt around external pulleys.
    if center_mm <= abs(pd2 - pd1) / 2:
        return {
            "ok": False,
            "messages": ["No valid external tangent exists; center distance is too small for the pulley size difference."],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": center_mm - (cd1 + cd2) / 2,
            "mesh1": float("nan"), "mesh2": float("nan"),
        }

    # Physical pulley overlap check, using checked diameters.
    clearance = center_mm - (cd1 + cd2) / 2
    if clearance < min_clearance_mm:
        return {
            "ok": False,
            "messages": [
                f"Pulley checked diameters interfere or miss clearance: clearance={clearance:.3f} mm, required >= {min_clearance_mm:.3f} mm."
            ],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": clearance, "mesh1": float("nan"), "mesh2": float("nan"),
        }

    if max_dia_1_mm is not None and cd1 > max_dia_1_mm:
        return {
            "ok": False,
            "messages": [f"Pulley 1 checked diameter {cd1:.3f} mm exceeds limit {max_dia_1_mm:.3f} mm."],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": clearance, "mesh1": float("nan"), "mesh2": float("nan"),
        }

    if max_dia_2_mm is not None and cd2 > max_dia_2_mm:
        return {
            "ok": False,
            "messages": [f"Pulley 2 checked diameter {cd2:.3f} mm exceeds limit {max_dia_2_mm:.3f} mm."],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": clearance, "mesh1": float("nan"), "mesh2": float("nan"),
        }

    wrap1, wrap2 = wrap_angles_rad(z1, z2, center_mm, pitch_mm)
    mesh1 = teeth_in_mesh(z1, wrap1)
    mesh2 = teeth_in_mesh(z2, wrap2)

    if mesh1 < min_mesh_1:
        return {
            "ok": False,
            "messages": [f"Pulley 1 has too few teeth in mesh: {mesh1:.2f}, required >= {min_mesh_1:.2f}."],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": clearance, "mesh1": mesh1, "mesh2": mesh2,
        }

    if mesh2 < min_mesh_2:
        return {
            "ok": False,
            "messages": [f"Pulley 2 has too few teeth in mesh: {mesh2:.2f}, required >= {min_mesh_2:.2f}."],
            "pd1": pd1, "pd2": pd2, "cd1": cd1, "cd2": cd2,
            "clearance": clearance, "mesh1": mesh1, "mesh2": mesh2,
        }

    if clearance < 1.0:
        messages.append("Very low pulley body clearance; verify CAD.")
    if mesh1 < 8.0:
        messages.append("Pulley 1 has low teeth in mesh.")
    if mesh2 < 8.0:
        messages.append("Pulley 2 has low teeth in mesh.")

    return {
        "ok": True,
        "messages": messages,
        "pd1": pd1,
        "pd2": pd2,
        "cd1": cd1,
        "cd2": cd2,
        "clearance": clearance,
        "mesh1": mesh1,
        "mesh2": mesh2,
    }


def belt_length_for_center_distance(z1: int, z2: int, center_mm: float, pitch_mm: float) -> dict:
    d1 = pitch_diameter(z1, pitch_mm)
    d2 = pitch_diameter(z2, pitch_mm)
    big, small = max(d1, d2), min(d1, d2)

    if center_mm <= (big - small) / 2:
        raise ValueError("Center distance is too small for these pulley diameters.")

    alpha = math.asin((big - small) / (2 * center_mm))
    straight = 2 * math.sqrt(center_mm**2 - ((big - small) / 2)**2)
    arcs = (math.pi / 2) * (big + small) + alpha * (big - small)
    length_mm = straight + arcs

    return {
        "length_mm": length_mm,
        "ideal_teeth": length_mm / pitch_mm,
        "nearest_teeth": round(length_mm / pitch_mm),
    }


def center_distance_for_belt(z1: int, z2: int, belt_teeth: int, pitch_mm: float) -> dict:
    target_length = belt_teeth * pitch_mm
    d1, d2 = pitch_diameter(z1, pitch_mm), pitch_diameter(z2, pitch_mm)
    big, small = max(d1, d2), min(d1, d2)

    min_center = (big - small) / 2 + 0.001
    max_center = max(target_length / 2, min_center + 1)

    def length_at_c(c: float) -> float:
        alpha = math.asin(max(-1.0, min(1.0, (big - small) / (2 * c))))
        straight = 2 * math.sqrt(max(0.0, c**2 - ((big - small) / 2)**2))
        return straight + (math.pi / 2) * (big + small) + alpha * (big - small)

    if length_at_c(min_center) > target_length:
        raise ValueError("Belt is too short for these pulleys.")

    for _ in range(120):
        mid = (min_center + max_center) / 2
        if length_at_c(mid) < target_length:
            min_center = mid
        else:
            max_center = mid

    return {"center_mm": (min_center + max_center) / 2, "length_mm": target_length}


class HelpPopup:
    @staticmethod
    def show(parent, title, text, diagram=None):
        win = tk.Toplevel(parent)
        win.title(title)
        win.geometry("520x430")
        win.transient(parent)
        win.grab_set()

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        lbl = ttk.Label(frm, text=text, wraplength=480, justify="left")
        lbl.pack(fill=tk.X)

        if diagram:
            canvas = tk.Canvas(frm, height=190, bg="white", highlightthickness=1, highlightbackground="#cccccc")
            canvas.pack(fill=tk.X, pady=(12, 8))
            HelpPopup._draw_diagram(canvas, diagram)

        ttk.Button(frm, text="Close", command=win.destroy).pack(pady=(8, 0))

    @staticmethod
    def _draw_diagram(canvas, diagram):
        w = 500
        if diagram == "ratio":
            canvas.create_oval(70, 70, 130, 130, width=2)
            canvas.create_text(100, 50, text="Driving pulley")
            canvas.create_text(100, 100, text="20T")
            canvas.create_oval(320, 45, 440, 165, width=2)
            canvas.create_text(380, 25, text="Driven pulley")
            canvas.create_text(380, 105, text="60T")
            canvas.create_line(130, 80, 320, 65, dash=(4, 3))
            canvas.create_line(130, 120, 320, 145, dash=(4, 3))
            canvas.create_text(250, 180, text="Ratio = driven / driving = 60 / 20 = 3:1")
        elif diagram == "center":
            canvas.create_oval(80, 75, 140, 135, width=2)
            canvas.create_oval(350, 65, 430, 145, width=2)
            canvas.create_line(110, 105, 390, 105, arrow=tk.BOTH)
            canvas.create_text(250, 90, text="center distance")
            canvas.create_text(110, 155, text="shaft center")
            canvas.create_text(390, 165, text="shaft center")
        elif diagram == "clearance":
            canvas.create_oval(80, 60, 180, 160, width=2)
            canvas.create_oval(310, 60, 410, 160, width=2)
            canvas.create_line(180, 110, 310, 110, arrow=tk.BOTH)
            canvas.create_text(245, 92, text="pulley clearance")
            canvas.create_text(130, 175, text="checked diameter 1")
            canvas.create_text(360, 175, text="checked diameter 2")
        elif diagram == "mesh":
            canvas.create_oval(150, 40, 350, 240, width=2)
            canvas.create_arc(150, 40, 350, 240, start=35, extent=180, width=5, style=tk.ARC)
            canvas.create_text(250, 140, text="Pulley")
            canvas.create_text(250, 265, text="Teeth in mesh ≈ pulley teeth × belt wrap / 360°")


class BeltCalculatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Timing Belt Calculator")
        self.geometry("1420x860")
        self.minsize(1120, 700)

        self.mode_var = tk.StringVar(value="ratio")
        self.only_catalog_belts_var = tk.BooleanVar(value=True)

        self.z1_var = tk.StringVar(value="20")
        self.z2_var = tk.StringVar(value="60")
        self.ratio_var = tk.StringVar(value="3:1")
        self.min_driver_var = tk.StringVar(value="12")
        self.max_driver_var = tk.StringVar(value="80")
        self.min_driven_var = tk.StringVar(value="12")
        self.max_driven_var = tk.StringVar(value="120")
        self.max_ratio_error_var = tk.StringVar(value="5")

        self.center_var = tk.StringVar(value="100")
        self.pitch_var = tk.StringVar(value="2.0")
        self.belt_width_var = tk.StringVar(value="6.0")
        self.search_range_var = tk.StringVar(value="30")

        self.max_dia_1_var = tk.StringVar(value="")
        self.max_dia_2_var = tk.StringVar(value="")
        self.allowance_1_var = tk.StringVar(value="0")
        self.allowance_2_var = tk.StringVar(value="0")
        self.min_mesh_1_var = tk.StringVar(value="6")
        self.min_mesh_2_var = tk.StringVar(value="6")
        self.min_clearance_var = tk.StringVar(value="0")

        self.results = []
        self.original_results = []
        self.sort_state = {"column": None, "direction": None, "absolute": False}
        self.numeric_columns = {
            "p1", "p2", "ratio", "ratio_err", "belt_teeth", "length", "center", "center_err",
            "pd1", "pd2", "cd1", "cd2", "clearance", "mesh1", "mesh2"
        }
        self.default_abs_sort_columns = {"ratio_err", "center_err"}
        self._build_ui()
        self._on_mode_change()
        self.calculate()

    def _help_button(self, parent, title, text, diagram=None):
        return ttk.Button(parent, text="?", width=2, command=lambda: HelpPopup.show(self, title, text, diagram))

    def _build_ui(self):
        p = {"padx": 6, "pady": 4}
        main = ttk.Frame(self, padding=10)
        main.pack(fill=tk.BOTH, expand=True)

        mode = ttk.LabelFrame(main, text="Mode")
        mode.pack(fill=tk.X)

        ttk.Radiobutton(mode, text="Fixed pulley tooth counts", variable=self.mode_var, value="fixed", command=self._on_mode_change).pack(side=tk.LEFT, padx=8, pady=8)
        ttk.Radiobutton(mode, text="Constrain gear ratio and search pulley pairs", variable=self.mode_var, value="ratio", command=self._on_mode_change).pack(side=tk.LEFT, padx=8, pady=8)

        inputs = ttk.LabelFrame(main, text="Inputs")
        inputs.pack(fill=tk.X, pady=(8, 0))

        self.fixed_frame = ttk.Frame(inputs)
        self.fixed_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(self.fixed_frame, text="Pulley 1 / driving teeth").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(self.fixed_frame, textvariable=self.z1_var, width=10).grid(row=0, column=1, **p)
        self._help_button(self.fixed_frame, "Driving pulley teeth", "Number of teeth on the input pulley. If this is on the motor, it is the driving pulley. Ratio is calculated as driven / driving.", "ratio").grid(row=0, column=2, **p)

        ttk.Label(self.fixed_frame, text="Pulley 2 / driven teeth").grid(row=0, column=3, sticky="w", **p)
        ttk.Entry(self.fixed_frame, textvariable=self.z2_var, width=10).grid(row=0, column=4, **p)
        self._help_button(self.fixed_frame, "Driven pulley teeth", "Number of teeth on the output pulley. A larger driven pulley than driving pulley creates a speed reduction and torque increase.", "ratio").grid(row=0, column=5, **p)

        self.ratio_frame = ttk.Frame(inputs)
        self.ratio_frame.grid(row=1, column=0, sticky="ew")
        ttk.Label(self.ratio_frame, text="Desired ratio, driven:driving").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(self.ratio_frame, textvariable=self.ratio_var, width=10).grid(row=0, column=1, **p)
        self._help_button(self.ratio_frame, "Gear ratio", "Use driven pulley teeth divided by driving pulley teeth. Example: 20T driving and 60T driven gives 60/20 = 3:1.", "ratio").grid(row=0, column=2, **p)

        ttk.Label(self.ratio_frame, text="Driving teeth range").grid(row=0, column=3, sticky="w", **p)
        ttk.Entry(self.ratio_frame, textvariable=self.min_driver_var, width=7).grid(row=0, column=4, **p)
        ttk.Label(self.ratio_frame, text="to").grid(row=0, column=5, **p)
        ttk.Entry(self.ratio_frame, textvariable=self.max_driver_var, width=7).grid(row=0, column=6, **p)

        ttk.Label(self.ratio_frame, text="Driven teeth range").grid(row=1, column=3, sticky="w", **p)
        ttk.Entry(self.ratio_frame, textvariable=self.min_driven_var, width=7).grid(row=1, column=4, **p)
        ttk.Label(self.ratio_frame, text="to").grid(row=1, column=5, **p)
        ttk.Entry(self.ratio_frame, textvariable=self.max_driven_var, width=7).grid(row=1, column=6, **p)

        ttk.Label(self.ratio_frame, text="Max ratio error (%)").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(self.ratio_frame, textvariable=self.max_ratio_error_var, width=10).grid(row=1, column=1, **p)
        self._help_button(self.ratio_frame, "Max ratio error", "Allowed deviation from the desired ratio. For 3:1 with 5% error, the app accepts ratios from 2.85:1 to 3.15:1.").grid(row=1, column=2, **p)

        shared = ttk.Frame(inputs)
        shared.grid(row=2, column=0, sticky="ew")
        ttk.Label(shared, text="Desired center distance (mm)").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(shared, textvariable=self.center_var, width=10).grid(row=0, column=1, **p)
        self._help_button(shared, "Center distance", "Distance between the two pulley shaft centers. The app finds belt tooth counts that produce a center distance close to this.", "center").grid(row=0, column=2, **p)

        ttk.Label(shared, text="Belt pitch (mm)").grid(row=0, column=3, sticky="w", **p)
        ttk.Combobox(shared, textvariable=self.pitch_var, values=["2.0", "3.0", "5.0"], width=8).grid(row=0, column=4, **p)
        self._help_button(shared, "Belt pitch", "Distance from one belt tooth to the next. For 2MGT/GT2 belts use 2 mm. Belt pitch must match pulley pitch.").grid(row=0, column=5, **p)

        ttk.Label(shared, text="Belt width (mm)").grid(row=0, column=6, sticky="w", **p)
        ttk.Combobox(shared, textvariable=self.belt_width_var, values=["6.0", "9.0", "12.0"], width=8).grid(row=0, column=7, **p)
        self._help_button(shared, "Belt width", "Physical belt width. Your earlier constraint was 6 mm or thinner. The embedded McMaster part-number library currently targets 2MGT belts at 6 mm width.").grid(row=0, column=8, **p)

        ttk.Label(shared, text="Belt search range (+/- teeth)").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(shared, textvariable=self.search_range_var, width=10).grid(row=1, column=1, **p)
        self._help_button(shared, "Belt search range", "How many belt tooth counts to check above and below the ideal theoretical belt length. Increase this to find more catalogue belt options.").grid(row=1, column=2, **p)

        ttk.Checkbutton(shared, text="Only suggest embedded McMaster catalogue belts", variable=self.only_catalog_belts_var).grid(row=1, column=3, columnspan=4, sticky="w", **p)
        self._help_button(shared, "Catalogue belt filter", "When checked, results are limited to belt tooth counts with an embedded McMaster part number. Currently this is the 2MGT, 6 mm wide catalogue set.").grid(row=1, column=7, **p)

        geom = ttk.LabelFrame(main, text="Geometry constraints")
        geom.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(geom, text="Pulley 1 max checked diameter (mm)").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.max_dia_1_var, width=10).grid(row=0, column=1, **p)
        self._help_button(geom, "Pulley 1 max checked diameter", "Maximum allowed diameter for pulley 1. Blank means no limit. Checked diameter = pitch diameter + pulley 1 diameter allowance. Use this to enforce package space.", "clearance").grid(row=0, column=2, **p)

        ttk.Label(geom, text="Pulley 2 max checked diameter (mm)").grid(row=0, column=3, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.max_dia_2_var, width=10).grid(row=0, column=4, **p)
        self._help_button(geom, "Pulley 2 max checked diameter", "Maximum allowed diameter for pulley 2. Blank means no limit. This is separate because the output pulley may have different space constraints.", "clearance").grid(row=0, column=5, **p)

        ttk.Label(geom, text="Pulley 1 diameter allowance (mm)").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.allowance_1_var, width=10).grid(row=1, column=1, **p)
        self._help_button(geom, "Pulley 1 diameter allowance", "Added to pitch diameter for pulley 1 to estimate physical OD. Use 0 for pitch diameter only. Add more if the printed pulley has teeth/flanges extending beyond pitch diameter.").grid(row=1, column=2, **p)

        ttk.Label(geom, text="Pulley 2 diameter allowance (mm)").grid(row=1, column=3, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.allowance_2_var, width=10).grid(row=1, column=4, **p)
        self._help_button(geom, "Pulley 2 diameter allowance", "Added to pitch diameter for pulley 2 to estimate physical OD. This is separate from pulley 1 because flanges/hubs may be different.").grid(row=1, column=5, **p)

        ttk.Label(geom, text="Pulley 1 min teeth in mesh").grid(row=2, column=0, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.min_mesh_1_var, width=10).grid(row=2, column=1, **p)
        self._help_button(geom, "Pulley 1 teeth in mesh", "Approximate number of pulley teeth engaged by the belt. Too few engaged teeth can strip/skid under load. Default 6 is a rough screening value.", "mesh").grid(row=2, column=2, **p)

        ttk.Label(geom, text="Pulley 2 min teeth in mesh").grid(row=2, column=3, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.min_mesh_2_var, width=10).grid(row=2, column=4, **p)
        self._help_button(geom, "Pulley 2 teeth in mesh", "Approximate number of teeth engaged on pulley 2. Large ratio differences can reduce wrap on the smaller pulley.").grid(row=2, column=5, **p)

        ttk.Label(geom, text="Min clearance between checked pulley diameters (mm)").grid(row=3, column=0, columnspan=2, sticky="w", **p)
        ttk.Entry(geom, textvariable=self.min_clearance_var, width=10).grid(row=3, column=2, **p)
        self._help_button(geom, "Pulley clearance", "Minimum gap between the two checked pulley diameters. Clearance = center distance - (checked diameter 1 + checked diameter 2)/2.", "clearance").grid(row=3, column=3, **p)

        buttons = ttk.Frame(main)
        buttons.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(buttons, text="Calculate", command=self.calculate).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Open Selected McMaster Part", command=self.open_selected_mcmaster).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Open McMaster GT Catalogue", command=lambda: webbrowser.open(MCMASTER_CATEGORY_URL)).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="Export CSV", command=self.export_csv).pack(side=tk.LEFT, padx=4)

        sort_options = ttk.LabelFrame(main, text="Sorting")
        sort_options.pack(fill=tk.X, pady=(8, 0))
        self.abs_sort_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            sort_options,
            text="Sort error/signed numeric columns by absolute magnitude",
            variable=self.abs_sort_var,
            command=self._reapply_current_sort,
        ).pack(side=tk.LEFT, padx=8, pady=6)
        self._help_button(
            sort_options,
            "Sorting results",
            "Click any results table heading to sort it like File Explorer. First click sorts ascending, second click sorts descending, third click returns to the original generated order. When the magnitude option is enabled, signed columns like center error and ratio error sort by closeness to zero rather than most negative to most positive."
        ).pack(side=tk.LEFT, padx=4, pady=6)

        summary_frame = ttk.LabelFrame(main, text="Summary")
        summary_frame.pack(fill=tk.X, pady=(8, 0))
        self.summary_text = tk.Text(summary_frame, height=6, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.X, padx=8, pady=8)
        self.summary_text.configure(state="disabled")

        results_frame = ttk.LabelFrame(main, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        self.columns = (
            "p1", "p2", "ratio", "ratio_err", "belt_teeth", "length",
            "mcmaster_part", "mcmaster_url", "center", "center_err",
            "pd1", "pd2", "cd1", "cd2", "clearance", "mesh1", "mesh2", "warnings"
        )
        self.tree = ttk.Treeview(results_frame, columns=self.columns, show="headings", height=16)
        headings = {
            "p1": "Driving T", "p2": "Driven T", "ratio": "Ratio", "ratio_err": "Ratio err %",
            "belt_teeth": "Belt T", "length": "Length mm", "mcmaster_part": "McMaster part",
            "mcmaster_url": "McMaster URL", "center": "Center mm", "center_err": "Center err",
            "pd1": "PD1", "pd2": "PD2", "cd1": "Chk Dia 1", "cd2": "Chk Dia 2",
            "clearance": "Clearance", "mesh1": "Mesh 1", "mesh2": "Mesh 2", "warnings": "Warnings"
        }
        widths = {
            "p1": 75, "p2": 75, "ratio": 85, "ratio_err": 90, "belt_teeth": 70, "length": 85,
            "mcmaster_part": 105, "mcmaster_url": 210, "center": 95, "center_err": 85,
            "pd1": 75, "pd2": 75, "cd1": 85, "cd2": 85, "clearance": 85,
            "mesh1": 70, "mesh2": 70, "warnings": 300
        }
        self.heading_labels = headings.copy()
        for c in self.columns:
            self.tree.heading(c, text=headings[c], command=lambda col=c: self._on_heading_click(col))
            self.tree.column(c, width=widths[c], anchor="center")

        yscroll = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        xscroll = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

    def _on_mode_change(self):
        if self.mode_var.get() == "fixed":
            self.fixed_frame.grid()
            self.ratio_frame.grid_remove()
        else:
            self.fixed_frame.grid_remove()
            self.ratio_frame.grid()

    def _float_or_none(self, s):
        s = s.strip()
        return None if s == "" else float(s)

    def _parse_common(self):
        center = float(self.center_var.get())
        pitch = float(self.pitch_var.get())
        width = float(self.belt_width_var.get())
        search_range = int(self.search_range_var.get())
        if center <= 0 or pitch <= 0 or width <= 0 or search_range < 1:
            raise ValueError("Center, pitch, width, and search range must be positive.")
        max_dia_1 = self._float_or_none(self.max_dia_1_var.get())
        max_dia_2 = self._float_or_none(self.max_dia_2_var.get())
        allowance_1 = float(self.allowance_1_var.get())
        allowance_2 = float(self.allowance_2_var.get())
        min_mesh_1 = float(self.min_mesh_1_var.get())
        min_mesh_2 = float(self.min_mesh_2_var.get())
        min_clearance = float(self.min_clearance_var.get())
        for name, value in [
            ("Pulley 1 max diameter", max_dia_1),
            ("Pulley 2 max diameter", max_dia_2),
        ]:
            if value is not None and value <= 0:
                raise ValueError(f"{name} must be positive or blank.")
        for name, value in [
            ("Pulley 1 diameter allowance", allowance_1),
            ("Pulley 2 diameter allowance", allowance_2),
            ("Pulley 1 min teeth in mesh", min_mesh_1),
            ("Pulley 2 min teeth in mesh", min_mesh_2),
            ("Min clearance", min_clearance),
        ]:
            if value < 0:
                raise ValueError(f"{name} cannot be negative.")
        return center, pitch, width, search_range, max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2

    def _make_option(self, z1, z2, belt_teeth, desired_center, pitch, width, desired_ratio, constraints):
        center = center_distance_for_belt(z1, z2, belt_teeth, pitch)["center_mm"]
        max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2 = constraints
        geom = geometry_check(z1, z2, center, pitch, max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2)
        if not geom["ok"]:
            return None
        catalog = belt_catalog_match(belt_teeth, pitch, width)
        if self.only_catalog_belts_var.get() and not catalog["part"]:
            return None
        actual_ratio = z2 / z1
        ratio_err = 0 if desired_ratio is None else 100 * (actual_ratio - desired_ratio) / desired_ratio
        return {
            "p1": z1, "p2": z2, "ratio": actual_ratio, "ratio_err": ratio_err,
            "belt_teeth": belt_teeth, "length": belt_teeth * pitch,
            "mcmaster_part": catalog["part"], "mcmaster_url": catalog["url"],
            "center": center, "center_err": center - desired_center,
            "pd1": geom["pd1"], "pd2": geom["pd2"], "cd1": geom["cd1"], "cd2": geom["cd2"],
            "clearance": geom["clearance"], "mesh1": geom["mesh1"], "mesh2": geom["mesh2"],
            "warnings": "; ".join(geom["messages"]),
        }

    def _belt_teeth_to_search(self, z1, z2, desired_center, pitch, search_range, width):
        if self.only_catalog_belts_var.get() and abs(pitch - 2.0) < 1e-9 and abs(width - 6.0) < 1e-9:
            return list(MCMASTER_2MGT_6MM_BELTS.keys())
        ideal = belt_length_for_center_distance(z1, z2, desired_center, pitch)["ideal_teeth"]
        low = max(1, math.floor(ideal) - search_range)
        high = math.ceil(ideal) + search_range
        return range(low, high + 1)

    def calculate(self):
        try:
            center, pitch, width, search_range, max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2 = self._parse_common()
            constraints = (max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2)
            results = []

            if self.mode_var.get() == "fixed":
                z1 = int(self.z1_var.get())
                z2 = int(self.z2_var.get())
                for belt_teeth in self._belt_teeth_to_search(z1, z2, center, pitch, search_range, width):
                    try:
                        opt = self._make_option(z1, z2, belt_teeth, center, pitch, width, None, constraints)
                        if opt:
                            results.append(opt)
                    except ValueError:
                        pass
                results.sort(key=lambda x: abs(x["center_err"]))

            else:
                desired_ratio = parse_ratio(self.ratio_var.get())
                min_driver = int(self.min_driver_var.get())
                max_driver = int(self.max_driver_var.get())
                min_driven = int(self.min_driven_var.get())
                max_driven = int(self.max_driven_var.get())
                max_ratio_err = float(self.max_ratio_error_var.get())

                if min_driver <= 0 or min_driven <= 0 or max_driver < min_driver or max_driven < min_driven:
                    raise ValueError("Pulley tooth ranges are invalid.")

                for z1 in range(min_driver, max_driver + 1):
                    for z2 in range(min_driven, max_driven + 1):
                        ratio_err = 100 * ((z2 / z1) - desired_ratio) / desired_ratio
                        if abs(ratio_err) > max_ratio_err:
                            continue
                        # Desired-center geometry pre-screen.
                        if not geometry_check(z1, z2, center, pitch, max_dia_1, max_dia_2, allowance_1, allowance_2, min_clearance, min_mesh_1, min_mesh_2)["ok"]:
                            continue
                        for belt_teeth in self._belt_teeth_to_search(z1, z2, center, pitch, search_range, width):
                            try:
                                opt = self._make_option(z1, z2, belt_teeth, center, pitch, width, desired_ratio, constraints)
                                if opt:
                                    opt["score"] = abs(opt["center_err"]) + 0.25 * abs(opt["ratio_err"])
                                    results.append(opt)
                            except ValueError:
                                pass

                results.sort(key=lambda x: (x.get("score", abs(x["center_err"])), abs(x["center_err"]), abs(x["ratio_err"])))
                results = results[:250]

            self.results = results
            self.original_results = list(results)
            self.sort_state = {"column": None, "direction": None, "absolute": False}
            self._refresh_heading_labels()
            self._update_summary(center, pitch, width)
            self._update_table()

        except Exception as exc:
            messagebox.showerror("Calculation error", str(exc))

    def _update_summary(self, center, pitch, width):
        if not self.results:
            text = (
                "No valid results found.\n"
                "Try widening the pulley tooth ranges, increasing max ratio error, increasing center distance, "
                "relaxing per-pulley diameter/mesh/clearance constraints, or unchecking the McMaster catalogue-only filter."
            )
        else:
            best = self.results[0]
            text = (
                f"Best result: {best['p1']}T driving, {best['p2']}T driven, ratio {best['ratio']:.4f}:1, "
                f"{best['belt_teeth']}T belt, center {best['center']:.3f} mm ({best['center_err']:+.3f} mm error).\n"
                f"McMaster belt part: {best['mcmaster_part'] or 'not in embedded catalogue'}\n"
                f"Pitch/width selected: {pitch:g} mm pitch, {width:g} mm width. Desired center: {center:.3f} mm.\n"
                "Pulley geometry should still be verified in Onshape because tooth OD, flanges, hubs, shaft bores, and mounting hardware are not fully modeled here."
            )
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, text)
        self.summary_text.configure(state="disabled")

    def _update_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for r in self.results:
            self.tree.insert("", tk.END, values=(
                r["p1"], r["p2"], f"{r['ratio']:.4f}:1", f"{r['ratio_err']:+.3f}",
                r["belt_teeth"], f"{r['length']:.3f}", r["mcmaster_part"], r["mcmaster_url"],
                f"{r['center']:.3f}", f"{r['center_err']:+.3f}",
                f"{r['pd1']:.3f}", f"{r['pd2']:.3f}", f"{r['cd1']:.3f}", f"{r['cd2']:.3f}",
                f"{r['clearance']:.3f}", f"{r['mesh1']:.2f}", f"{r['mesh2']:.2f}", r["warnings"],
            ))


    def _parse_display_value(self, value):
        """
        Converts displayed table values back to sortable values where needed.

        The main sort uses self.results dictionaries directly, but this helper is
        intentionally robust for future columns that may only exist as strings.
        """
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return value
        text = str(value).strip()
        if text.endswith(":1"):
            text = text[:-2]
        text = text.replace("+", "")
        try:
            return float(text)
        except ValueError:
            return text.lower()

    def _sort_key(self, row, column, absolute=False):
        value = row.get(column, "")
        if column == "ratio":
            value = row.get("ratio", 0.0)

        if column in self.numeric_columns:
            try:
                num = float(value)
                return abs(num) if absolute else num
            except (TypeError, ValueError):
                return float("inf")

        # Natural-ish string sort so 7947K9 does not behave too weirdly beside 7947K100.
        text = str(value).lower()
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]

    def _on_heading_click(self, column):
        """
        Explorer-style 3-state sorting:
        - first click: ascending
        - second click: descending
        - third click: unsorted/original generated order

        For signed numeric columns, if the magnitude checkbox is enabled and the
        column is an error/magnitude-style column, sorting uses abs(value).
        """
        current_column = self.sort_state.get("column")
        current_direction = self.sort_state.get("direction")

        if current_column != column:
            direction = "asc"
        elif current_direction == "asc":
            direction = "desc"
        elif current_direction == "desc":
            direction = None
        else:
            direction = "asc"

        if direction is None:
            self.results = list(self.original_results)
            self.sort_state = {"column": None, "direction": None, "absolute": False}
        else:
            use_abs = bool(self.abs_sort_var.get() and column in self.default_abs_sort_columns)
            self.results = sorted(
                self.results,
                key=lambda row: self._sort_key(row, column, use_abs),
                reverse=(direction == "desc"),
            )
            self.sort_state = {"column": column, "direction": direction, "absolute": use_abs}

        self._refresh_heading_labels()
        self._update_table()

    def _reapply_current_sort(self):
        column = self.sort_state.get("column")
        direction = self.sort_state.get("direction")

        if not column or not direction:
            return

        use_abs = bool(self.abs_sort_var.get() and column in self.default_abs_sort_columns)
        self.results = sorted(
            self.results,
            key=lambda row: self._sort_key(row, column, use_abs),
            reverse=(direction == "desc"),
        )
        self.sort_state = {"column": column, "direction": direction, "absolute": use_abs}
        self._refresh_heading_labels()
        self._update_table()

    def _refresh_heading_labels(self):
        if not hasattr(self, "tree") or not hasattr(self, "heading_labels"):
            return

        active_col = self.sort_state.get("column")
        direction = self.sort_state.get("direction")
        absolute = self.sort_state.get("absolute")

        for col, label in self.heading_labels.items():
            suffix = ""
            if col == active_col and direction:
                suffix = " ▲" if direction == "asc" else " ▼"
                if absolute:
                    suffix += " |abs|"
            self.tree.heading(col, text=label + suffix, command=lambda c=col: self._on_heading_click(c))


    def open_selected_mcmaster(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("No selection", "Select a result row first.")
            return
        values = self.tree.item(sel[0], "values")
        url = values[self.columns.index("mcmaster_url")]
        if not url:
            messagebox.showinfo("No McMaster part", "This row does not have an embedded McMaster part number.")
            return
        webbrowser.open(url)

    def export_csv(self):
        if not self.results:
            messagebox.showinfo("No results", "Calculate results before exporting.")
            return
        file_path = filedialog.asksaveasfilename(title="Export results", defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        fieldnames = list(self.results[0].keys())
        if "score" in fieldnames:
            fieldnames.remove("score")
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        messagebox.showinfo("Export complete", f"Saved results to:\n{file_path}")


if __name__ == "__main__":
    app = BeltCalculatorApp()
    app.mainloop()
