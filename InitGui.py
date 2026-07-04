

import FreeCAD
import FreeCADGui
from PySide import QtCore

def auto_start_multimonitor():
    """Asynchronously injects and mounts the 4-panel window into FreeCAD's active thread."""
    try:
        # Dynamically import our custom multi-monitor module file from the Mod folder
        import MultiMonitor

        # Safe memory check to close and override any duplicate window context
        if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
            try:
                FreeCADGui._mm_win_v26.close()
                FreeCADGui._mm_win_v26 = None
            except:
                pass

        # Instantiate the window class and bind it to FreeCAD's persistent global memory
        FreeCADGui._mm_win_v26 = MultiMonitor.MultiMonitorWindow6()
        FreeCADGui._mm_win_v26.show()
        FreeCADGui._mm_win_v26.raise_()
        FreeCADGui._mm_win_v26.activateWindow()

        FreeCAD.Console.PrintMessage("MultiMonitor: Persistent secondary window auto-started successfully.\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"MultiMonitor Addon Autostart Failure: {str(e)}\n")

# FreeCAD automatically executes bare InitGui.py code upon completion of the core GUI render stack.
# We set a single-shot timer to let the desktop environment fully stabilize.
QtCore.QTimer.singleShot(1500, auto_start_multimonitor)

