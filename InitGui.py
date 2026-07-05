# *************************************************************************
# *                                                                       *
# * Copyright (c) 2026 BlackMaxMetal                                      *
# *                                                                       *
# * This program is free software; you can redistribute it and/or modify  *
# * it under the terms of the GNU Lesser General Public License (LGPL)    *
# * as published by the Free Software Foundation; either version 3 of     *
# * the License, or (at your option) any later version.                   *
# * for detail see the LICENCE text file.                                 *
# *                                                                       *
# * This program is distributed in the hope that it will be useful,       *
# * but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# * GNU Library General Public License for more details.                  *
# *                                                                       *
# * You should have received a copy of the GNU Library General Public     *
# * License along with this program; if not, write to the Free Software   *
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# * USA                                                                   *
# *                                                                       *
# *************************************************************************

import FreeCAD
import FreeCADGui
from PySide import QtCore

def auto_start_multimonitor():

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

