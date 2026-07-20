
# Timing Belt Calculator GUI v5

## New in v5

This version adds:

- Explorer-style sortable results columns.
- Click a column heading once for ascending, twice for descending, and a third time to return to original generated order.
- Magnitude sorting for signed/error columns such as center error and ratio error.
- Embedded **McMaster-Carr 2MGT, 6 mm wide belt catalogue** with part numbers.
- Direct links to McMaster part pages from the results table.
- A button to open the selected McMaster part.
- Per-pulley geometric constraints:
  - Pulley 1 max checked diameter
  - Pulley 2 max checked diameter
  - Pulley 1 diameter allowance
  - Pulley 2 diameter allowance
  - Pulley 1 minimum teeth in mesh
  - Pulley 2 minimum teeth in mesh
- A shared minimum pulley-to-pulley clearance constraint.
- "?" help buttons beside most parameters, with short explanations and simple diagrams where useful.

## Important assumption

The app assumes the pulleys are generated in Onshape and 3D printed.

The embedded McMaster catalogue is for the **belt**, not printed pulleys.

For your original use case, the intended belt family is:

```text
2MGT / GT2
2 mm pitch
6 mm width
```

## Catalogue filter

By default, the app only suggests belt tooth counts that are present in the embedded McMaster 2MGT, 6 mm belt list.

Uncheck:

```text
Only suggest embedded McMaster catalogue belts
```

to see theoretical belt tooth counts that may not correspond to an embedded McMaster part number.

## How the diameter constraints work

For each pulley:

```text
pitch diameter = teeth × pitch / π
checked diameter = pitch diameter + diameter allowance
```

Use `0 mm` allowance if you only want to constrain pitch diameter.

Use a positive allowance if the generated pulley has teeth/flanges/hub geometry that extends beyond pitch diameter.

Final packaging should still be checked in Onshape.

## How to run from source

Install Python 3.10+.

Then double-click:

```text
belt_calculator_gui.pyw
```

or run:

```bash
python belt_calculator_gui.pyw
```

## How to build a Windows .exe

On Windows, open PowerShell in this folder and run:

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --windowed --name BeltCalculator belt_calculator_gui.pyw
```

Or double-click:

```text
build_windows_exe.bat
```

The executable will be created here:

```text
dist/BeltCalculator.exe
```


## Sorting

The results table behaves like File Explorer:

```text
1st click on a column heading  -> ascending
2nd click                      -> descending
3rd click                      -> unsorted / original generated order
```

For signed error columns, enable:

```text
Sort error/signed numeric columns by absolute magnitude
```

This makes columns like center error sort by closeness to zero.

Example:

```text
+0.05 mm
-0.10 mm
+0.25 mm
```

instead of pure numeric order:

```text
-0.10 mm
+0.05 mm
+0.25 mm
```
