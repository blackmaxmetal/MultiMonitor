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

# --- SPREADSHEET REVERSIBLE WINDOW LAYER ---
class DetachedSpreadsheetWindow(QtWidgets.QMainWindow):
    """Custom top-level window layout dedicated to hosting extracted spreadsheets and cleaning up tabs safely."""
    def __init__(self, sheet_widget, mdi_subwin, notice_label, doc_name, filter_instance):
        super(DetachedSpreadsheetWindow, self).__init__(None, QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint)
        self.sheet_widget = sheet_widget
        self.mdi_subwin = mdi_subwin
        self.notice_label = notice_label
        self.target_doc_name = doc_name
        self.filter_instance = filter_instance

        self.setWindowTitle(f"Detached Spreadsheet - {mdi_subwin.windowTitle()}")
        self.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")
        self.setCentralWidget(sheet_widget)
        sheet_widget.show()

    def closeEvent(self, event):
        """Intercepts closure to cleanly destroy the courtesy notice and shut down the native MDI window shell."""
        try:
            # 1. Clean up centralized global menu inhibition tracking array
            if hasattr(self, "target_doc_name") and self.target_doc_name:
                if hasattr(FreeCADGui, '_mm_disabled_sheets') and self.target_doc_name in FreeCADGui._mm_disabled_sheets:
                    FreeCADGui._mm_disabled_sheets.remove(self.target_doc_name)

            # 2. Safely evacuate and isolate the spreadsheet grid widget before destroying this frame
            if self.sheet_widget:
                self.setCentralWidget(None)
                self.sheet_widget.setParent(None)

            if self.notice_label:
                self.notice_label.setParent(None)
                self.notice_label.deleteLater()

            # 3. CLEAN NATIVE MDI CLOSURE
            # We explicitly trigger the standard C++ close handler on the native MDI sub-window framework.
            # This forces FreeCAD to execute a natural window tab deletion, which prevents the application
            # from forcing any automatic tiling or rimpicciolimento on surrounding 3D windows.
            if self.mdi_subwin:
                try:
                    self.mdi_subwin.setWidget(None)
                    self.mdi_subwin.close()
                except Exception:
                    pass

            QtWidgets.QApplication.processEvents()
        except Exception:
            pass

        if hasattr(FreeCADGui, '_mm_standalone_clones') and FreeCADGui._mm_standalone_clones:
            try:
                if self in FreeCADGui._mm_standalone_clones:
                    FreeCADGui._mm_standalone_clones.remove(self)
            except Exception:
                pass
        event.accept()




class TabContextMenuFilter(QtCore.QObject):
    """Event filter using PySide to handle UI tab states, 3D clone extractions, and spreadsheet detachment logic."""
    def __init__(self, tab_bar, main_addon_window_class):
        super(TabContextMenuFilter, self).__init__(tab_bar)
        self.tab_bar = tab_bar
        self.window_class = main_addon_window_class

        # Keep track of active document names that currently have an extracted spreadsheet
        self._disabled_sheets = []

        mw = FreeCADGui.getMainWindow()
        self.mdi_area = mw.findChild(QtWidgets.QMdiArea) if mw else None
        if self.mdi_area:
            self.mdi_area.subWindowActivated.connect(self._handle_mdi_window_change)

    def _handle_mdi_window_change(self, active_subwin):
        """Monitors MDI state changes and cross-references active views to force-close orphaning clones."""
        try:
            current_docs = [doc.Name for doc in FreeCAD.listDocuments().values()]

            if hasattr(FreeCADGui, '_mm_standalone_clones') and FreeCADGui._mm_standalone_clones:
                for win in list(FreeCADGui._mm_standalone_clones):
                    if win:
                        try:
                            win_doc_name = getattr(win, "target_doc_name", None)
                            if win_doc_name and win_doc_name not in current_docs:
                                win.close()
                                if win in FreeCADGui._mm_standalone_clones:
                                    FreeCADGui._mm_standalone_clones.remove(win)
                                continue
                        except Exception:
                            pass
        except Exception:
            pass

    def eventFilter(self, obj, event):
        if obj == self.tab_bar and event.type() == QtCore.QEvent.ContextMenu:
            local_pos = self.tab_bar.mapFromGlobal(event.globalPos())
            tab_index = self.tab_bar.tabAt(local_pos)
            if tab_index != -1:
                QtCore.QTimer.singleShot(10, lambda: self.inject_clone_action(tab_index))
        return super(TabContextMenuFilter, self).eventFilter(obj, event)

    def _force_close_clones_by_name(self, doc_name):
        """Forcefully destroys external cloned views matching the target document name to unlock C++ memory."""
        if not doc_name:
            return
        if hasattr(FreeCADGui, '_mm_standalone_clones') and FreeCADGui._mm_standalone_clones:
            to_remove = []
            for win in list(FreeCADGui._mm_standalone_clones):
                try:
                    if win and hasattr(win, "windowTitle"):
                        win_doc_name = getattr(win, "target_doc_name", None)
                        title = win.windowTitle()
                        if win_doc_name == doc_name or f"- {doc_name}" in title or doc_name in title:
                            win.setParent(None)
                            win.close()
                            win.deleteLater()
                            to_remove.append(win)
                except Exception:
                    pass
            for win in to_remove:
                if win in FreeCADGui._mm_standalone_clones:
                    FreeCADGui._mm_standalone_clones.remove(win)

    def inject_clone_action(self, tab_index):
        """Dynamically evaluates the underlying widget type of the tab and injects only relevant contextual actions."""
        if not self.mdi_area or tab_index >= len(self.mdi_area.subWindowList()):
            return

        QtWidgets.QApplication.processEvents()
        active_widget = QtWidgets.QApplication.activePopupWidget() or QtWidgets.QApplication.activeModalWidget()
        if not active_widget:
            active_widget = QtWidgets.QApplication.activeWindow()

        if active_widget:
            native_menu = active_widget.findChild(QtWidgets.QMenu) or (active_widget if isinstance(active_widget, QtWidgets.QMenu) else None)
            if native_menu:
                for action in native_menu.actions():
                    if action.text() in ["Open 3D View on Second Monitor", "Open Four View on Second Monitor", "Open Spreadsheet on Second Monitor"]:
                        return
                native_menu.addSeparator()

                target_sub_win = self.mdi_area.subWindowList()[tab_index]
                widget_item = target_sub_win.widget()
                if not widget_item:
                    return

                class_name = widget_item.metaObject().className().lower()
                is_spreadsheet = "spreadsheet" in class_name or widget_item.findChild(QtWidgets.QTableView) is not None
                is_3d_view = "view3dinventor" in class_name

                if is_3d_view:
                    clone_action = native_menu.addAction("Open 3D View on Second Monitor")
                    clone_action.triggered.connect(lambda: self.clone_in_new_standalone_window(tab_index))

                    quad_action = native_menu.addAction("Open Four View on Second Monitor")
                    quad_action.triggered.connect(lambda: self.clone_in_four_view_window(tab_index))

                elif is_spreadsheet:
                    sheet_action = native_menu.addAction("Open Spreadsheet on Second Monitor")
                    sheet_action.triggered.connect(lambda: self.detach_spreadsheet_window(tab_index))

                    # GLOBAL ALIGNMENT CHECK: Look into centralized global listing to block item
                    if hasattr(FreeCADGui, '_mm_disabled_sheets') and FreeCADGui._mm_disabled_sheets:
                        gui_doc = FreeCADGui.activeDocument()
                        if gui_doc and gui_doc.Document.Name in FreeCADGui._mm_disabled_sheets:
                            sheet_action.setEnabled(False)

                menu_geo = native_menu.geometry()
                screen_height = QtWidgets.QApplication.primaryScreen().geometry().height() if hasattr(QtWidgets.QApplication, 'primaryScreen') else 1080
                if menu_geo.y() + menu_geo.height() > (screen_height - 100) or menu_geo.y() > (screen_height - 250):
                    new_y = menu_geo.y() - menu_geo.height() - 40
                    native_menu.move(menu_geo.x(), max(10, new_y))

    def clone_in_new_standalone_window(self, tab_index):
        """Creates a twin 3D View and detaches it into a completely standalone top-level window using PySide."""
        mw = FreeCADGui.getMainWindow()
        if not self.mdi_area or tab_index >= len(self.mdi_area.subWindowList()):
            return
        target_sub_win = self.mdi_area.subWindowList()[tab_index]
        target_sub_win.setFocus()
        gui_doc = FreeCADGui.activeDocument()
        if not gui_doc:
            return
        try:
            sub_windows = self.mdi_area.subWindowList()
            QtCore.QTimer.singleShot(0, lambda: self._execute_view_extraction(self.mdi_area, sub_windows, target_sub_win, gui_doc, mw))
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

                # Explicitly tag the window with the document's C++ internal name for strict tracking
                new_view_subwin.target_doc_name = gui_doc.Document.Name

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
        if not self.mdi_area or tab_index >= len(self.mdi_area.subWindowList()):
            return
        target_sub_win = self.mdi_area.subWindowList()[tab_index]
        target_sub_win.setFocus()
        gui_doc = FreeCADGui.activeDocument()
        if not gui_doc:
            return
        try:
            QtCore.QTimer.singleShot(0, lambda: self._execute_four_view_extraction(self.mdi_area, target_sub_win, gui_doc, mw))
        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed quad clone trigger): {str(e)}\n")

    def _execute_four_view_extraction(self, mdi_area, target_sub_win, gui_doc, mw):
        """Assembles the 2x2 grid layout, generates 4 independent views, and overrides their camera angles."""
        try:
            quad_frame = QtWidgets.QMainWindow(None, QtCore.Qt.Window | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowMinMaxButtonsHint | QtCore.Qt.WindowCloseButtonHint)
            quad_frame.setWindowTitle(f"Four View Matrix Clone (TOP, FRONT, LEFT, ISOMETRIC) - {target_sub_win.windowTitle()}")
            quad_frame.setStyleSheet("QMainWindow { background-color: #2b2b2b; }")

            # Explicitly tag the quad container with the document's C++ internal name for strict tracking
            quad_frame.target_doc_name = gui_doc.Document.Name

            central_widget = QtWidgets.QWidget(quad_frame)
            grid_layout = QtWidgets.QGridLayout(central_widget)
            grid_layout.setContentsMargins(4, 4, 4, 4)
            grid_layout.setSpacing(6)
            quad_frame.setCentralWidget(central_widget)

            view_configs = [(0, 0, "TOP"), (0, 1, "LEFT"), (1, 0, "FRONT"), (1, 1, "ISOMETRIC")]
            main_active_view = FreeCADGui.activeDocument().ActiveView
            if main_active_view and hasattr(main_active_view, 'saveOrientation'):
                main_active_view.saveOrientation()

            for row, col, orientation in view_configs:
                if main_active_view:
                    if orientation == "TOP": main_active_view.viewTop()
                    elif orientation == "LEFT": main_active_view.viewLeft()
                    elif orientation == "FRONT": main_active_view.viewFront()
                    elif orientation == "ISOMETRIC": main_active_view.viewAxonometric()
                    main_active_view.fitAll()
                    QtWidgets.QApplication.processEvents()

                current_stack = mdi_area.subWindowList()
                gui_doc.createView("Gui::View3DInventor")
                updated_stack = mdi_area.subWindowList()

                if updated_stack and len(updated_stack) > len(current_stack):
                    cloned_subwin = updated_stack[-1]
                    cloned_subwin.setWindowFlags(QtCore.Qt.Widget | QtCore.Qt.FramelessWindowHint | QtCore.Qt.CustomizeWindowHint)
                    cloned_subwin.setWindowTitle(f"=== {orientation} VIEW ===")
                    grid_layout.addWidget(cloned_subwin, row, col)
                    cloned_subwin.show()

            if main_active_view and hasattr(main_active_view, 'restoreOrientation'):
                main_active_view.restoreOrientation()
                main_active_view.fitAll()

            if not hasattr(FreeCADGui, '_mm_standalone_clones'):
                FreeCADGui._mm_standalone_clones = []
            FreeCADGui._mm_standalone_clones.append(quad_frame)
            quad_frame.showNormal()
            self._apply_monitor_and_geometry(quad_frame, mw, 1200, 850)
            quad_frame.raise_()
            quad_frame.activateWindow()
        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed quad clone assembly): {str(e)}\n")

    def detach_spreadsheet_window(self, tab_index):
        """Extracts the native spreadsheet widget safely and mounts a courtesy splash card inside the MDI shell container."""
        if not self.mdi_area or tab_index >= len(self.mdi_area.subWindowList()):
            return

        target_sub_win = self.mdi_area.subWindowList()[tab_index]
        target_sub_win.setFocus()

        gui_doc = FreeCADGui.activeDocument()
        if not gui_doc:
            return

        try:
            sheet_widget = target_sub_win.widget()
            if not sheet_widget:
                return

            # Verify that the chosen tab contains a valid spreadsheet view profile architecture
            class_name = sheet_widget.metaObject().className().lower()
            has_table = "spreadsheet" in class_name or sheet_widget.findChild(QtWidgets.QTableView) is not None
            if not has_table:
                FreeCAD.Console.PrintWarning("MultiMonitor: Selected tab is not an active Spreadsheet canvas.\n")
                return

            doc_name = gui_doc.Document.Name
            original_title = target_sub_win.windowTitle()

            # Initialize centralized tracking array inside FreeCADGui global memory if not present
            if not hasattr(FreeCADGui, '_mm_disabled_sheets'):
                FreeCADGui._mm_disabled_sheets = []

            # Append the document token name inside our central global block list to handle item inhibition
            if doc_name not in FreeCADGui._mm_disabled_sheets:
                FreeCADGui._mm_disabled_sheets.append(doc_name)

            # MDI VISUAL ANCHOR GUARD: Inject a clean courtesy splash layout card inside the vacant MDI shell container.
            # This masks the extraction so FreeCAD's layout engine believes the window structure is active, preserving tiled sizes.
            notice_card = QtWidgets.QWidget()
            notice_card.setStyleSheet("background-color: #2b2b2b;")
            card_layout = QtWidgets.QVBoxLayout(notice_card)

            lbl_notice = QtWidgets.QLabel("🖥️ Spreadsheet detached on secondary monitor\n\nClosing the external window will destroy this tab.", notice_card)
            lbl_notice.setAlignment(QtCore.Qt.AlignCenter)
            lbl_notice.setStyleSheet("color: #888888; font-size: 13px; font-weight: bold;")
            card_layout.addWidget(lbl_notice)

            # Instantiate our specialized separate window container passing pointers to clean them up
            sheet_frame = DetachedSpreadsheetWindow(sheet_widget, target_sub_win, notice_card, doc_name, self)
            sheet_frame.target_doc_name = doc_name

            # Mount the notice layout card directly into the native active MDI frame shell to freeze titles and positions
            target_sub_win.setWidget(notice_card)

            if not hasattr(FreeCADGui, '_mm_standalone_clones'):
                FreeCADGui._mm_standalone_clones = []
            FreeCADGui._mm_standalone_clones.append(sheet_frame)

            # Render frame container on secondary screen layout geometry borders safely
            sheet_frame.showNormal()
            self._apply_monitor_and_geometry(sheet_frame, FreeCADGui.getMainWindow(), 1000, 700)
            sheet_frame.raise_()
            sheet_frame.activateWindow()

            FreeCAD.Console.PrintLog("MultiMonitor: Spreadsheet safely isolated and detached onto secondary monitor.\n")

        except Exception as e:
            FreeCAD.Console.PrintError(f"MultiMonitor Error (Failed spreadsheet window extraction): {str(e)}\n")



    def _apply_monitor_and_geometry(self, window_instance, fallback_mw, default_w, default_h):
        """Unified geometric calculations module targeting multi-monitor window positioning using PySide."""
        if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
            target_frame = FreeCADGui._mm_win_v26
        else:
            target_frame = fallback_mw
        if target_frame.windowHandle() and target_frame.windowHandle().screen():
            window_instance.windowHandle().setScreen(target_frame.windowHandle().screen())
        else:
            target_screen = QtWidgets.QApplication.screenAt(target_frame.geometry().center())
            if target_screen: window_instance.windowHandle().setScreen(target_screen)
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
        super(MultiMonitorWindow6, self).__init__(None, QtCore.Qt.Window)
        self.settings = QtCore.QSettings("FreeCAD", "MultiMonitor")
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self._extracted_views = []
        self._tree_view_data = None

        if not is_standalone_doc:
            self.setWindowTitle("FreeCAD - Secondary Monitor Layout")
            self.resize(1200, 800)

            self.main_layout = QtWidgets.QHBoxLayout(self.central_widget)
            self.main_layout.setContentsMargins(2, 2, 2, 2)

            self.horizontal_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.central_widget)
            self.main_layout.addWidget(self.horizontal_splitter)

            self.right_vertical_splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.horizontal_splitter)
            self.horizontal_splitter.addWidget(self.right_vertical_splitter)

            # INCREASED DELAY: Give FreeCAD 800ms to stabilize the core C++ dock state before extraction
            QtCore.QTimer.singleShot(800, self.extract_widgets)
        else:
            self.setWindowTitle("FreeCAD - Detached Document Canvas")
            self.resize(1200, 800)

            local_layout = QtWidgets.QHBoxLayout(self.central_widget)
            local_layout.setContentsMargins(2, 2, 2, 2)

            self.document_tabs = QtWidgets.QTabWidget(self.central_widget)
            local_layout.addWidget(self.document_tabs)

            if self.settings.contains("standalone_geometry"):
                self.restoreGeometry(self.settings.value("standalone_geometry"))

    def extract_widgets(self):
        """Locates FreeCAD's native dock panels, isolates them, and loads splitters layout configurations securely."""
        mw = FreeCADGui.getMainWindow()
        if not mw:
            return

        # Force Qt to process any pending UI refresh cycles before we alter dock frames
        QtWidgets.QApplication.processEvents()

        dock_combo = None
        dock_selection = None
        dock_python = None
        dock_report = None

        # Deep scan active dock widgets inside FreeCAD's core shell
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

        # 1. Mount Property/Combo View into the primary left column layout slot
        if dock_combo:
            mw.removeDockWidget(dock_combo)
            dock_combo.setParent(None)
            dock_combo.setFloating(False)
            self.horizontal_splitter.insertWidget(0, dock_combo)
            dock_combo.show()
            dock_combo.update()

        # 2. Mount Selection View into the central column layout slot
        if dock_selection:
            mw.removeDockWidget(dock_selection)
            dock_selection.setParent(None)
            dock_selection.setFloating(False)
            self.horizontal_splitter.insertWidget(1, dock_selection)
            dock_selection.show()
            dock_selection.update()

        # 3. Mount Python Console into the top slot of the right column vertical splitter
        if dock_python:
            mw.removeDockWidget(dock_python)
            dock_python.setParent(None)
            dock_python.setFloating(False)
            self.right_vertical_splitter.addWidget(dock_python)
            dock_python.show()
            dock_python.update()

        # 4. Mount Report/Output View into the bottom slot of the right column vertical splitter
        if dock_report:
            mw.removeDockWidget(dock_report)
            dock_report.setParent(None)
            dock_report.setFloating(False)
            self.right_vertical_splitter.addWidget(dock_report)
            dock_report.show()
            dock_report.update()

        # Force layout recalculation before loading sizes into the splitters engine
        QtWidgets.QApplication.processEvents()

        # --- SESSION LAYOUT RESTORE ENGINE ---
        saved_geometry = self.settings.value("window_geometry")
        if saved_geometry:
            self.restoreGeometry(saved_geometry)

        saved_horiz_splitter = self.settings.value("horiz_splitter_sizes")
        if saved_horiz_splitter:
            self.horizontal_splitter.setSizes([int(x) for x in saved_horiz_splitter])

        saved_vert_splitter = self.settings.value("vert_splitter_sizes")
        if saved_vert_splitter:
            self.right_vertical_splitter.setSizes([int(x) for x in saved_vert_splitter])

        # Ultimate visual anchor refresh
        self.update()

    def closeEvent(self, event):
        """Intercepts the window close event to hide the window instead of destroying it, preserving widgets."""
        is_primary_addon_win = hasattr(self, 'right_vertical_splitter')

        # --- SESSION LAYOUT SAVE ENGINE ---
        if is_primary_addon_win:
            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.setValue("horiz_splitter_sizes", self.horizontal_splitter.sizes())
            self.settings.setValue("vert_splitter_sizes", self.right_vertical_splitter.sizes())
        else:
            self.settings.setValue("standalone_geometry", self.saveGeometry())

        # If it is the main secondary monitor window, hide it and ignore the destruction request
        if is_primary_addon_win:
            event.ignore()  # Prevent Qt from destroying the window reference
            self.hide()     # Safely hide the window while keeping all extracted widgets alive inside
            FreeCAD.Console.PrintMessage("MultiMonitor: Window hidden successfully, preserving panel state.\n")
            return

        if hasattr(FreeCADGui, '_mm_isolated_windows') and self in FreeCADGui._mm_isolated_windows:
            FreeCADGui._mm_isolated_windows.remove(self)

        event.accept()

class MultiMonitorAddon:
    """Core addon coordinator responsible for hooks injection and event lifecycle tracking using PySide."""
    def __init__(self):
        self.filter_instance = None
        self.active_tabbar = None
        # Setup continuous monitoring loop for active tab swaps or tab recreations
        self.lifecycle_timer = QtCore.QTimer()
        self.lifecycle_timer.setInterval(2000) # Every 2 seconds
        self.lifecycle_timer.timeout.connect(self.insinuated_tabbar_search)

    def Setup(self):
        """Initial injection step when FreeCAD finishes subsystem initialization."""
        self.lifecycle_timer.start()
        self.insinuated_tabbar_search()
        FreeCAD.Console.PrintLog("MultiMonitor Addon loaded successfully.\n")

    def insinuated_tabbar_search(self):
        """Crawls FreeCAD main application hierarchy to lock onto the current native QTabBar."""
        try:
            mw = FreeCADGui.getMainWindow()
            if not mw:
                return

            # Target FreeCAD's underlying document tab layout system
            mdi_area = mw.findChild(QtWidgets.QMdiArea)
            if not mdi_area:
                return

            # Pick native active tab bar engine
            tab_bar = mdi_area.findChild(QtWidgets.QTabBar)
            if not tab_bar:
                return

            # If a new tab bar workspace is generated or replaced, switch filters safely
            if tab_bar != self.active_tabbar:
                if self.active_tabbar and self.filter_instance:
                    try:
                        self.active_tabbar.removeEventFilter(self.filter_instance)
                    except Exception:
                        pass

                self.active_tabbar = tab_bar
                self.filter_instance = TabContextMenuFilter(self.active_tabbar, self)
                self.active_tabbar.installEventFilter(self.filter_instance)
        except Exception:
            pass

def open_window():
    """Factory function to safely instantiate, re-open, or restore the MultiMonitor layout using PySide."""
    # Check if the primary window instance already exists globally and is a valid runtime reference
    if hasattr(FreeCADGui, '_mm_win_v26') and FreeCADGui._mm_win_v26:
        try:
            # If the window was hidden by our closeEvent override, bring it back to screen layout
            if FreeCADGui._mm_win_v26.isHidden():
                FreeCADGui._mm_win_v26.show()

            if FreeCADGui._mm_win_v26.isMinimized():
                FreeCADGui._mm_win_v26.showNormal()

            FreeCADGui._mm_win_v26.raise_()
            FreeCADGui._mm_win_v26.activateWindow()
            FreeCAD.Console.PrintMessage("MultiMonitor: Existing layout window revealed and brought to front.\n")
            return
        except Exception:
            # Fallback if the reference became corrupted or dropped by the C++ engine
            FreeCADGui._mm_win_v26 = None

    if hasattr(FreeCADGui, '_mm_isolated_windows') and FreeCADGui._mm_isolated_windows:
        for win in list(FreeCADGui._mm_isolated_windows):
            try:
                win.close()
            except Exception:
                pass
        FreeCADGui._mm_isolated_windows = []

    # Fallback/Initial Boot: Instantiate a completely fresh main secondary monitor window
    FreeCADGui._mm_win_v26 = MultiMonitorWindow6()
    FreeCADGui._mm_win_v26.show()
    FreeCADGui._mm_win_v26.raise_()
    FreeCADGui._mm_win_v26.activateWindow()

class MultiMonitorMenuCommand:
    """Native FreeCAD Command class to handle action triggering safely."""
    def GetResources(self):
        return {
            'MenuText': "MultiMonitor Manager",
            'ToolTip': "Open or restore the multi-monitor interface panels"
        }

    def Activated(self):
        open_window()

def inject_button_into_statusbar():
    """Uses PySide to inject a dedicated button directly into FreeCAD's native status bar safely."""
    try:
        mw = FreeCADGui.getMainWindow()
        if not mw:
            return

        status_bar = mw.statusBar()
        if not status_bar:
            return

        # Guard clause: Prevent injecting multiple duplicate buttons into the layout
        if status_bar.findChild(QtWidgets.QPushButton, "btn_multimonitor_manager"):
            return

        # Create a clean, lightweight push button utilizing pure PySide styling
        btn = QtWidgets.QPushButton("🖥️ MultiMonitor", status_bar)
        btn.setObjectName("btn_multimonitor_manager")

        # Apply a subtle flat layout style that fits seamlessly into FreeCAD's theme
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 1px 6px;
                color: #aaaaaa;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3b3b3b;
                color: #ffffff;
                border-color: #888888;
            }
            QPushButton:pressed {
                background-color: #2b2b2b;
            }
        """)

        btn.setToolTip("Open or restore the multi-monitor interface panels")

        # Connect the button click event directly to our safe open_window factory
        btn.clicked.connect(open_window)

        # Insert the button onto the right side of the native status bar layout
        status_bar.addPermanentWidget(btn)
        FreeCAD.Console.PrintLog("MultiMonitor: Status bar trigger widget successfully mounted.\n")

    except Exception as e:
        FreeCAD.Console.PrintWarning(f"MultiMonitor Status Bar Notice (Widget injection bypassed): {str(e)}\n")

# ENVIRONMENT REGISTRATION ENTRY POINT
if FreeCADGui.getMainWindow():
    try:
        # Register the command inside FreeCAD's internal registry for macro execution compliance
        FreeCADGui.addCommand("MultiMonitor_Manager", MultiMonitorMenuCommand())
    except Exception:
        pass

    # Launch the continuous background monitoring loop for native document tabs
    if not hasattr(FreeCADGui, '_mm_addon_instance'):
        FreeCADGui._mm_addon_instance = MultiMonitorAddon()
        FreeCADGui._mm_addon_instance.Setup()

    # Asynchronously inject the status bar button to allow FreeCAD UI sub-structures to settle
    QtCore.QTimer.singleShot(1500, inject_button_into_statusbar)

    # Launch the window independently to instantly restore secondary monitor geometry settings
    QtCore.QTimer.singleShot(500, open_window)

