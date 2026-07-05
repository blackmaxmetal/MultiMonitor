#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2026 BlackMaxMetal                                      *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import FreeCAD
import FreeCADGui
# Use unified PySide wrapper for cross-version stability in FreeCAD 26.3
from PySide import QtWidgets, QtCore

class TabContextMenuFilter(QtCore.QObject):
    """Event filter to append 'Open Clone View' and 'Four View Clone' actions to FreeCAD's native document tabs."""
    def __init__(self, tab_bar, main_addon_window_class):
        super().__init__(tab_bar)
        self.tab_bar = tab_bar
        self.window_class = main_addon_window_class

    def eventFilter(self, obj, event):
        # Intercept the context menu event on native document tabs
        if obj == self.tab_bar and event.type() == QtCore.QEvent.ContextMenu:
            local_pos = self.tab_bar.mapFromGlobal(event.globalPos())
            tab_index = self.tab_bar.tabAt(local_pos)

            if tab_index != -1:
                # Force the menu layout to process immediately
                QtCore.QTimer.singleShot(10, lambda: self.inject_clone_action(tab_index))

        return super().eventFilter(obj, event)

    def inject_clone_action(self, tab_index):
        """Finds FreeCAD's active QMenu and appends the custom 3D duplication routines."""
        QtWidgets.QApplication.processEvents()

        active_widget = QtWidgets.QApplication.activePopupWidget() or QtWidgets.QApplication.activeModalWidget()
        if not active_widget:
            active_widget = QtWidgets.QApplication.activeWindow()

        if active_widget:
            native_menu = active_widget.findChild(QtWidgets.QMenu) or (active_widget if isinstance(active_widget, QtWidgets.QMenu) else None)

            if native_menu:
                # Prevent duplicate entries in the menu
                for action in native_menu.actions():
                    if action.text() in ["Open Clone View on Second Monitor", "Four View Clone"]:
                        return

                native_menu.addSeparator()

                # Action 1: Standard single clone
                clone_action = native_menu.addAction("Open Clone View on Second Monitor")
                clone_action.triggered.connect(lambda: self.clone_in_new_standalone_window(tab_index))

                # Action 2: New quad view matrix clone
                quad_action = native_menu.addAction("Four View Clone")
                quad_action.triggered.connect(lambda: self.clone_in_four_view_window(tab_index))

                # --- MENU REPOSITIONING ENGINE ---
                menu_geo = native_menu.geometry()
                screen_height = QtWidgets.QApplication.primaryScreen().geometry().height() if hasattr(QtWidgets.QApplication, 'primaryScreen') else 1080

                if menu_geo.y() + menu_geo.height() > (screen_height - 100) or menu_geo.y() > (screen_height - 250):
                    new_y = menu_geo.y() - menu_geo.height() - 40
                    native_menu.move(menu_geo.x(), max(10, new_y))

    def clone_in_new_standalone_window(self, tab_index):
        """Creates a twin 3D View and detaches it into a completely standalone top-level window."""
        mw = FreeCADGui.getMainWindow()
        mdi_area = mw.findChild(QtWidgets.QMdiArea)
        if not mdi_area or tab_index >= len(mdi_area.subWindowList()):
            return

        target_sub_win = mdi_area.subWindowList()[tab_index]
        target_sub_win.setFocus()

        gui_doc = FreeCADGui.activeDocument()
        if not gui_doc:
            return

        try:
            sub_windows = mdi_area.subWindowList()
            QtCore.QTimer.singleShot(0, lambda: self._execute_view_extraction(mdi_area, sub_windows, target_sub_win, gui_doc, mw))
        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed single clone trigger): {str(e)}\n")

    def _execute_view_extraction(self, mdi_area, sub_windows, target_sub_win, gui_doc, mw):
        """Internal sub-routine to build and display the single isolated clone viewport."""
        try:
            gui_doc.createView("Gui::View3DInventor")
            fresh_sub_windows = mdi_area.subWindowList()

            if fresh_sub_windows and len(fresh_sub_windows) > len(sub_windows):
                new_view_subwin = fresh_sub_windows[-1]

                new_view_subwin.setParent(None)
                new_view_subwin.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint)

                new_view_subwin.setWindowTitle(f"3D Clone View - {target_sub_win.windowTitle()}")
                new_view_subwin.setStyleSheet("QWidget { background-color: #2b2b2b; }")

                if not hasattr(FreeCADGui, '_mm_standalone_clones'):
                    FreeCADGui._mm_standalone_clones = []
                FreeCADGui._mm_standalone_clones.append(new_view_subwin)

                new_view_subwin.showNormal()
                self._apply_monitor_and_geometry(new_view_subwin, mw, 850, 600)
                new_view_subwin.raise_()
                new_view_subwin.activateWindow()
        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed single clone extraction): {str(e)}\n")

    def clone_in_four_view_window(self, tab_index):
        """Creates an independent container window splitting 4 automated viewpoint clones into a 2x2 grid."""
        mw = FreeCADGui.getMainWindow()
        mdi_area = mw.findChild(QtWidgets.QMdiArea)
        if not mdi_area or tab_index >= len(mdi_area.subWindowList()):
            return

        target_sub_win = mdi_area.subWindowList()[tab_index]
        target_sub_win.setFocus()

        gui_doc = FreeCADGui.activeDocument()
        if not gui_doc:
            return

        try:
            QtCore.QTimer.singleShot(0, lambda: self._execute_four_view_extraction(mdi_area, target_sub_win, gui_doc, mw))
        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed quad clone trigger): {str(e)}\n")

    def _execute_four_view_extraction(self, mdi_area, target_sub_win, gui_doc, mw):
        """Assembles the 2x2 grid layout, generates 4 independent views, and overrides their camera angles."""
        try:
            # Create a native top-level container window for the 4 viewpoints
            quad_frame = QtWidgets.QMainWindow(None, QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint)
            # UPDATED: Adjusted title to represent the new LEFT orientation tracking sequence
            quad_frame.setWindowTitle(f"Four View Matrix Clone (TOP, FRONT, LEFT, ISOMETRIC) - {target_sub_win.windowTitle()}")
            quad_frame.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")

            central_widget = QtWidgets.QWidget(quad_frame)
            grid_layout = QtWidgets.QGridLayout(central_widget)
            grid_layout.setContentsMargins(4, 4, 4, 4)
            grid_layout.setSpacing(6)
            quad_frame.setCentralWidget(central_widget)

            # Map coordinates layout configuration layout grid parameters
            # UPDATED: Replaced REAR with LEFT configuration tracking profile mapping
            view_configs = [
                (0, 0, "TOP"),
                (0, 1, "LEFT"),
                (1, 0, "FRONT"),
                (1, 1, "ISOMETRIC")
            ]

            # Fetch active view and securely save user orientation using native API routines
            main_active_view = FreeCADGui.activeDocument().ActiveView
            if main_active_view and hasattr(main_active_view, 'saveOrientation'):
                main_active_view.saveOrientation()

            for row, col, orientation in view_configs:
                # Invoke high-level orientation functions directly on the view object safely
                if main_active_view:
                    if orientation == "TOP":
                        main_active_view.viewTop()
                    elif orientation == "LEFT":
                        # UPDATED: Invoking core native viewLeft C++ macro operation mapping function
                        main_active_view.viewLeft()
                    elif orientation == "FRONT":
                        main_active_view.viewFront()
                    elif orientation == "ISOMETRIC":
                        main_active_view.viewAxonometric()
                    main_active_view.fitAll()
                    QtWidgets.QApplication.processEvents()

                current_stack = mdi_area.subWindowList()
                # Request FreeCAD to clone the current active view state layout structure
                gui_doc.createView("Gui::View3DInventor")
                updated_stack = mdi_area.subWindowList()

                if updated_stack and len(updated_stack) > len(current_stack):
                    cloned_subwin = updated_stack[-1]

                    # Convert the window to an embedded fixed layout widget item
                    cloned_subwin.setWindowFlags(QtCore.Qt.Widget | QtCore.Qt.FramelessWindowHint | QtCore.Qt.CustomizeWindowHint)

                    # Append the view perspective title directly into the window title parameter description
                    cloned_subwin.setWindowTitle(f"=== {orientation} VIEW ===")

                    grid_layout.addWidget(cloned_subwin, row, col)
                    cloned_subwin.show()

            # Restore primary viewport camera using native C++ environment stack methods
            if main_active_view and hasattr(main_active_view, 'restoreOrientation'):
                main_active_view.restoreOrientation()
                main_active_view.fitAll()

            if not hasattr(FreeCADGui, '_mm_standalone_clones'):
                FreeCADGui._mm_standalone_clones = []
            FreeCADGui._mm_standalone_clones.append(quad_frame)

            # Show window layout container before repositioning monitors
            quad_frame.showNormal()
            self._apply_monitor_and_geometry(quad_frame, mw, 1200, 850)

            quad_frame.raise_()
            quad_frame.activateWindow()

        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed quad clone assembly): {str(e)}\n")

    def _apply_monitor_and_geometry(self, window_instance, fallback_mw, default_w, default_h):
        """Unified geometric calculations module targeting the primary addon multi-monitor widget frame."""
        if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
            target_frame = FreeCADGui._mm_win_v26
        else:
            target_frame = fallback_mw

        # Sync physical monitor screen pointer references to prevent secondary display escaping
        if target_frame.windowHandle() and target_frame.windowHandle().screen():
            window_instance.windowHandle().setScreen(target_frame.windowHandle().screen())
        else:
            target_screen = QtWidgets.QApplication.screenAt(target_frame.geometry().center())
            if target_screen:
                window_instance.windowHandle().setScreen(target_screen)

        # Enforce exact viewport centering math calculation operations
        frame_geo = target_frame.geometry()
        x_pos = frame_geo.x() + (frame_geo.width() - default_w) // 2
        y_pos = frame_geo.y() + (frame_geo.height() - default_h) // 2
        window_instance.setGeometry(x_pos, y_pos, default_w, default_h)

class MultiMonitorWindow6(QtWidgets.QMainWindow):
    @staticmethod
    def move_document_to_isolated_window_static(tab_index, window_class):
        """Static bridge to safely trigger the extraction logic from the context menu event."""
        # Creiamo un'istanza al volo della classe del filtro per usare la logica di movimento esistente
        dummy_filter = TabContextMenuFilter(None, window_class)
        dummy_filter.move_document_to_isolated_window(tab_index)


    def __init__(self, is_standalone_doc=False):
        super().__init__(None, QtCore.Qt.Window)
        self.settings = QtCore.QSettings("FreeCAD", "MultiMonitor")

        # UI Styling block for theme isolation
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; color: #ffffff; }
            QDockWidget { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; }
            QDockWidget::title { background-color: #313335; color: #ffffff; padding-top: 4px; }
            QTextEdit, QTreeView, QTableView, QWidget { background-color: #2b2b2b; color: #ffffff; }
            QTabBar::tab { background-color: #3c3f41; color: #ffffff; border: 1px solid #555555; padding: 6px; }
            QTabBar::tab:selected { background-color: #555555; }
        """)

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        # Track internal structures dynamically to ensure safe C++ memory restoration on close
        self._extracted_views = []      # Format: (View_Widget, Original_MDI_SubWindow)
        self._tree_view_data = None     # Format: (TreeWidget_Widget, Original_Parent_Widget)

        # CORE INTERFACES INITIALIZATION BRANCH
        if not is_standalone_doc:
            # 1. PRIMARY WINDOW BRANCH: Instantiates your original untouched 4-panels layout matrix
            self.setWindowTitle("FreeCAD 26.3dev - Secondary Monitor Layout")
            self.resize(1200, 800)

            self.main_layout = QtWidgets.QHBoxLayout(self.central_widget)
            self.main_layout.setContentsMargins(2, 2, 2, 2)

            self.horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.central_widget)
            self.main_layout.addWidget(self.horizontal_splitter)

            self.right_vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.horizontal_splitter)
            self.horizontal_splitter.addWidget(self.right_vertical_splitter)

            # Controlled asynchronous timer to allow FreeCAD UI synchronization
            QtCore.QTimer.singleShot(400, self.extract_widgets)
        else:
            # 2. STANDALONE DOCUMENT BRANCH: Creates an isolated window layout for right-clicked tabs
            self.setWindowTitle("FreeCAD 26.3dev - Detached Document Canvas")
            self.resize(1200, 800)

            local_layout = QtWidgets.QHBoxLayout(self.central_widget)
            local_layout.setContentsMargins(2, 2, 2, 2)

            self.document_tabs = QtWidgets.QTabWidget(self.central_widget)
            local_layout.addWidget(self.document_tabs)

            if self.settings.contains("standalone_geometry"):
                self.restoreGeometry(self.settings.value("standalone_geometry"))

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

        # --- INTEGRATION: MOUNT EVENT FILTER ONTO NATIVE TAB BAR ---
        mdi_area = mw.findChild(QtWidgets.QMdiArea)
        if mdi_area:
            native_tab_bar = mdi_area.findChild(QtWidgets.QTabBar)
            if native_tab_bar:
                self.tab_filter = TabContextMenuFilter(native_tab_bar, MultiMonitorWindow6)
                native_tab_bar.installEventFilter(self.tab_filter)

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
        mw = FreeCADGui.getMainWindow()
        is_primary_addon_win = hasattr(self, 'right_vertical_splitter')

        # --- SESSION SAVE ENGINE ---
        if is_primary_addon_win:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.setValue("horiz_splitter_sizes", self.horizontal_splitter.sizes())
            self.settings.setValue("vert_splitter_sizes", self.right_vertical_splitter.sizes())
        else:
            self.settings.setValue("standalone_geometry", self.saveGeometry())

        if mw:
            # 1. RESTORE STANDALONE 3D VIEW WINDOW DOCUMENTS BACK TO MDI AREA
            for view_widget, sub_win in self._extracted_views:
                try:
                    view_widget.setParent(None)
                    sub_win.setWidget(view_widget)
                except Exception as e:
                    FreeCAD.Console.PrintError(f"MultiMonitor Error (Document Restore Failed): {str(e)}\n")

            # 2. RESTORE NATIVE MODEL TREE VIEW COMPONENT IF APPLICABLE
            if self._tree_view_data:
                try:
                    t_widget, t_parent = self._tree_view_data
                    t_widget.setParent(None)
                    if t_parent:
                        if hasattr(t_parent, 'addWidget'):
                            t_parent.addWidget(t_widget)
                        else:
                            t_widget.setParent(t_parent)
                    t_widget.show()
                except Exception as e:
                    FreeCAD.Console.PrintError(f"MultiMonitor Error (ModelTree Restore Failed): {str(e)}\n")

            # 3. RESTORE PRIMARY SYSTEM UTILITY PANELS (Only if this instance is the main window)
            if is_primary_addon_win:
                mdi_area = mw.findChild(QtWidgets.QMdiArea)
                if mdi_area:
                    native_tab_bar = mdi_area.findChild(QtWidgets.QTabBar)
                    if native_tab_bar and hasattr(self, 'tab_filter'):
                        native_tab_bar.removeEventFilter(self.tab_filter)

                for dock in self.central_widget.findChildren(QtWidgets.QDockWidget):
                    name = dock.objectName().lower()
                    if "python" in name or "report" in name:
                        mw.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
                    else:
                        mw.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)

                    dock.setFloating(False)
                    dock.setVisible(True)
                    dock.update()

        # Clean tracing references inside global memory listing
        if hasattr(FreeCADGui, '_mm_isolated_windows') and self in FreeCADGui._mm_isolated_windows:
            FreeCADGui._mm_isolated_windows.remove(self)

        event.accept()

def open_window():
    """Factory function to safely instantiate or re-open the MultiMonitor layout."""
    if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
        try:
            FreeCADGui._mm_win_v26.close()
            FreeCADGui._mm_win_v26 = None
        except:
            pass

    # Clean up any leftover isolated document windows before spawning a new main layout
    if hasattr(FreeCADGui, '_mm_isolated_windows') and FreeCADGui._mm_isolated_windows:
        for win in list(FreeCADGui._mm_isolated_windows):
            try:
                win.close()
            except:
                pass
        FreeCADGui._mm_isolated_windows = []

    FreeCADGui._mm_win_v26 = MultiMonitorWindow6()
    FreeCADGui._mm_win_v26.show()
    FreeCADGui._mm_win_v26.raise_()
    FreeCADGui._mm_win_v26.activateWindow()
    FreeCAD.Console.PrintMessage("MultiMonitor: Secondary window running smoothly as background Addon.\n")

