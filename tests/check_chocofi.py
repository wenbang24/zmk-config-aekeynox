"""Check the Chocofi adapters without injecting unavailable Kconfig defines.

Run: python3 tests/check_chocofi.py (requires clang).
Pin reference: pashutk/chocofi, PCB revision 273676d11b06785fb5a1a94860a39fc36c38baba.
"""

from pathlib import Path
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
rows = [" ".join(f"K{i}" for i in range(n, n + 5)) for n in range(0, 30, 5)]
args = []
for i in range(0, 6, 2):
    args += ["OUT", rows[i], rows[i + 1], "OUT"]
args += ["LT1", "LT2", "LT3", "RT3", "RT2", "RT1"]

with tempfile.TemporaryDirectory() as tmp:
    # Only replace Selenium's external behavior dependencies, not the adapter.
    stub = Path(tmp) / "aekeynox/selenium.keymap"
    stub.parent.mkdir()
    stub.write_text("#include <aekeynox/defaults.h>\n"
                    "#ifndef HT_TWO_THUMB_KEYS\n#error Expected 2TK\n#endif\n")
    for side, expected, upstream in (
        ("left", [20, 19, 18, 15, 14], [21, 20, 19, 18, 15]),
        ("right", [14, 15, 18, 19, 20], [15, 18, 19, 20, 21]),
    ):
        # ZMK gives the shared keymap priority over per-half files.
        keymap = root / "config/temper.keymap"
        if not keymap.exists():
            keymap = root / f"config/temper_{side}.keymap"
        pins = ", ".join(f"<&pro_micro {pin} GPIO_ACTIVE_HIGH>" for pin in upstream)
        source = f'&kscan0 {{ col-gpios = {pins}; }};\n#include "{keymap}"\n'
        source += "KEYS SELENIUM_KEYMAP_BINDINGS(" + ",".join(args) + ")\n"
        result = subprocess.run(
            ["clang", "-E", "-P", "-x", "c", "-I", tmp, "-I", str(root / "include"), "-"],
            input=source, text=True, capture_output=True, check=True,
        ).stdout
        columns = re.findall(r"col-gpios\s*=\s*(.*?);", result, re.S)[-1]
        actual = [int(pin) for pin in re.findall(r"&pro_micro\s+(\d+)", columns)]
        assert actual == expected, f"{side}: scan pins {actual}, expected {expected}"
        assert result.split("KEYS", 1)[1].split() == [f"K{i}" for i in range(30)] + [
            "&none", "LT1", "LT2", "RT2", "RT1", "&none"
        ]
        print(f"PASS {side}: {keymap.name}, Chocofi pins, all 36 key positions")
