 


import FreeCAD
import FreeCADGui
# Use unified PySide wrapper for cross-version stability in FreeCAD 26.3
from PySide import QtWidgets, QtCore

class MultiMonitorWindow6(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__(None, QtCore.Qt.Window)
        self.setWindowTitle("FreeCAD 26.3dev - Secondary Monitor Layout")

        # Initialize permanent storage context using QSettings with the exact MultiMonitor key
        self.settings = QtCore.QSettings("FreeCAD", "MultiMonitor")

        self.resize(1200, 800) # Full widescreen setup for 4 panels matrix

        # UI Styling block for theme isolation
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QDockWidget { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; }
            QDockWidget::title { background-color: #313335; color: #ffffff; padding-top: 4px; }
            QTextEdit, QTreeView, QTableView, QWidget { background-color: #2b2b2b; color: #ffffff; }
        """)

        # Configure the central architecture layout hierarchy
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QtWidgets.QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

        # Main horizontal splitter separating Left Column Group from Right Column Group
        self.horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.central_widget)
        self.main_layout.addWidget(self.horizontal_splitter)

        # Secondary split matrix layout for the right column section (stacked vertically)
        self.right_vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.horizontal_splitter)

        # Assemble geometry distribution structure
        self.horizontal_splitter.addWidget(self.right_vertical_splitter)

        # Controlled asynchronous timer to allow FreeCAD UI synchronization
        QtCore.QTimer.singleShot(400, self.extract_widgets)

    def extract_widgets(self):
        mw = FreeCADGui.getMainWindow()
        if not mw:
            return

        dock_combo = None
        dock_selection = None
        dock_python = None
        dock_report = None

        # Hardware scanner evaluating object names and localized window titles
        for dock in mw.findChildren(QtWidgets.QDockWidget):
            obj_name = dock.objectName().lower()
            win_title = dock.windowTitle().lower()

            if "property" in obj_name or "combo" in obj_name or "property" in win_title or "combo" in win_title:
                dock_combo = dock
            elif "select" in obj_name or "select" in win_title or "sel" in obj_name:
                dock_selection = dock
            elif "python" in obj_name or "console" in obj_name or "python" in win_title or "console" in win_title:
                dock_python = dock
            elif "report" in obj_name or "output" in obj_name or "report" in win_title or "output" in win_title:
                dock_report = dock

        # 1. Inject Property/Combo View into the LEFT slot of the horizontal splitter
        if dock_combo:
            mw.removeDockWidget(dock_combo)
            dock_combo.setFloating(False)
            self.horizontal_splitter.insertWidget(0, dock_combo)
            dock_combo.setVisible(True)
            dock_combo.update()
        else:
            FreeCAD.Console.PrintWarning("MultiMonitor: Property/Combo view panel structure not found.\n")

        # 2. Inject Selection View into the MIDDLE slot (Right side of the left column group)
        if dock_selection:
            mw.removeDockWidget(dock_selection)
            dock_selection.setFloating(False)
            self.horizontal_splitter.insertWidget(1, dock_selection)
            dock_selection.setVisible(True)
            dock_selection.update()
        else:
            FreeCAD.Console.PrintWarning("MultiMonitor: Selection view panel structure not found.\n")

        # 3. Inject Python Console into the TOP slot of the right vertical splitter
        if dock_python:
            mw.removeDockWidget(dock_python)
            dock_python.setFloating(False)
            self.right_vertical_splitter.addWidget(dock_python)
            dock_python.setVisible(True)
            dock_python.update()
        else:
            FreeCAD.Console.PrintWarning("MultiMonitor: Python console panel structure not found.\n")

        # 4. Inject Report View into the BOTTOM slot of the right vertical splitter
        if dock_report:
            mw.removeDockWidget(dock_report)
            dock_report.setFloating(False)
            self.right_vertical_splitter.addWidget(dock_report)
            dock_report.setVisible(True)
            dock_report.raise_()
            dock_report.update()
        else:
            FreeCAD.Console.PrintWarning("MultiMonitor: Report view panel structure not found.\n")

        # --- SESSION RESTORE ENGINE ---
        saved_geometry = self.settings.value("window_geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

        saved_horiz_splitter = self.settings.value("horiz_splitter_sizes")
        if saved_horiz_splitter:
            self.horizontal_splitter.setSizes([int(x) for x in saved_horiz_splitter])

        saved_vert_splitter = self.settings.value("vert_splitter_sizes")
        if saved_vert_splitter:
            self.right_vertical_splitter.setSizes([int(x) for x in saved_vert_splitter])

    def closeEvent(self, event):
        """Save geometry layout states and safely restore widgets back to primary canvas."""
        # --- SESSION SAVE ENGINE ---
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("horiz_splitter_sizes", self.horizontal_splitter.sizes())
        self.settings.setValue("vert_splitter_sizes", self.right_vertical_splitter.sizes())

        mw = FreeCADGui.getMainWindow()
        if mw:
            for dock in self.central_widget.findChildren(QtWidgets.QDockWidget):
                name = dock.objectName().lower()
                if "python" in name or "report" in name:
                    mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
                else:
                    mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

                dock.setFloating(False)
                dock.setVisible(True)
                dock.update()
        event.accept()

def open_window():
    """Factory function to safely instantiate or re-open the MultiMonitor layout."""
    if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
        try:
            FreeCADGui._mm_win_v26.close()
        except:
            pass

    FreeCADGui._mm_win_v26 = MultiMonitorWindow6()
    FreeCADGui._mm_win_v26.show()
    FreeCADGui._mm_win_v26.raise_()
    FreeCADGui._mm_win_v26.activateWindow()
    FreeCAD.Console.PrintMessage("MultiMonitor: Secondary window running smoothly as background Addon.\n")
