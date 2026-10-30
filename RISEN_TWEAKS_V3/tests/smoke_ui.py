"""Smoke-Test ohne Windows/GUI: ersetzt customtkinter/tkinter durch Mocks und
fuehrt den kompletten UI-Aufbau sowie die neuen Handler aus. Prueft NUR, dass
der Code ohne NameError/AttributeError/TypeError durchlaeuft - kein visueller Test."""
import sys, types, threading, time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

class Base:
    def __init__(self, *a, **k): pass
    def after(self, ms, fn=None, *a):
        if fn and ms == 0:
            fn()
        return "id"
    def __getattr__(self, name):
        m = MagicMock(name=name)
        m.winfo_children.return_value = []
        return m

ctk = MagicMock()
ctk.CTk = Base
sys.modules["customtkinter"] = ctk
try:
    import tkinter  # noqa
except Exception:
    tk = MagicMock()
    sys.modules["tkinter"] = tk
    sys.modules["tkinter.ttk"] = tk.ttk
    sys.modules["tkinter.messagebox"] = tk.messagebox
    sys.modules["tkinter.filedialog"] = tk.filedialog

import tweaklib
tweaklib.WinRegBackend = tweaklib.MemoryBackend

import main
main.messagebox = MagicMock()
main.messagebox.askyesno.return_value = True
main.APP_DIR = Path("/tmp/risen_smoke"); main.APP_DIR.mkdir(exist_ok=True)
main.TWEAK_STATE_FILE = main.APP_DIR / "tweak_state.json"
if main.TWEAK_STATE_FILE.exists(): main.TWEAK_STATE_FILE.unlink()

app = main.RisenTweaks.__new__(main.RisenTweaks)
# __init__ ruft periodic/after etc. -> normal ausfuehren
main.RisenTweaks.__init__(app)
app.engine.runner = lambda args, timeout=12: (1, "no powercfg in test")

errors = []
def step(name, fn):
    try:
        fn()
        print("ok  ", name)
    except Exception as exc:
        errors.append((name, exc)); print("FAIL", name, repr(exc))

for cat in main.tweaklib.CATEGORIES:
    step(f"render {cat}", lambda c=cat: (setattr(app, "tl_category", c), app.tl_render()))
step("apply game_mode", lambda: app.engine_apply_dialog("game_mode"))
step("apply mouse", lambda: app.engine_apply_dialog("mouse_accel"))
time.sleep(0.5)
step("backup label", lambda: app.update_backup_label())
step("undo game_mode", lambda: app.engine_undo_dialog("game_mode"))
step("restore_all", lambda: app.restore_all())
step("startup toggle", lambda: (app.engine.backend.write(main.tweaklib.RUN_KEY, "Foo", 1, "x.exe"), app.tl_toggle_startup("Foo", False)))
step("nl_refresh_config", app.nl_refresh_config)
step("nl_dns_epic", app.nl_dns_epic); time.sleep(3)
step("fn_background", app.fn_background); time.sleep(2)
step("fn_capture (no presentmon)", app.fn_capture)
step("run_ping_test", lambda: app.run_ping_test("127.0.0.1", "Loopback")); time.sleep(4)
step("hw accept", lambda: app._accept_hardware({"CPU": {"Name": "Ryzen", "NumberOfCores": 6, "NumberOfLogicalProcessors": 12}, "Mem": [{"Capacity": 34359738368, "Speed": 3200, "ConfiguredClockSpeed": 2133}]}))
step("gpu detail", lambda: print(main.safe_gpu_detail({"available": True, "name": "RTX", "usage": 10, "mem_used": 1, "mem_total": 8, "temp": 40, "power": 50, "clock": 2500, "mem_clock": 14000}, True)))
print("ERRORS:", errors)
sys.exit(1 if errors else 0)
