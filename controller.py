from src.plugin_interface import PluginInterface
from src.models.model_apps import Model, ModelApps
from PyQt6 import QtWidgets, QtCore, QtGui
from .surveillance import Ui_Form
from .ui_setup import Ui_Setup

MAX_MONITOR_INDEX = 8


class GridManager:
    def __init__(self):
        self.slots = [None] * 8

    def get_index_of_slot(self, element):
        try:
            index = self.slots.index(element)
            return index + 1
        except ValueError:
            return -1

    def get_slot_by_index(self, index):
        if 1 <= index <= len(self.slots):
            return self.slots[index - 1]
        return None

    def get_empty_slots(self):
        return [i + 1 for i, slot in enumerate(self.slots) if slot is None]

    def get_used_slots(self):
        return [i + 1 for i, slot in enumerate(self.slots) if slot is not None]

    def set_slot(self, index, element):
        if 1 <= index <= len(self.slots):
            self.slots[index - 1] = element

    def clear_slot(self, index):
        if 1 <= index <= len(self.slots):
            self.slots[index - 1] = None


# for the setup dialog
class SetupDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()

    # get the slot and signal of the result image (rectilinear) so it can be connected and display it continously
    def setup_result_signal(self, slot, signal):
        self.result_slot = slot
        self.result_signal = signal
        self.result_signal.connect(self.result_slot)

    # get the slot and signal of the original image (fisheye) so it can be connected and display it continously
    def setup_original_signal(self, slot, signal):
        self.original_slot = slot
        self.original_signal = signal
        self.original_signal.connect(self.original_slot)

    # Escape Key does not invoke closeEvent (to disconnect the signals and slots), so need to do it manually
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close_function()
        else:
            super().keyPressEvent(event)

    # need to disconnect the signals and slots else RuntimeError: wrapped C/C++ object of type QLabel has been deleted
    # because the QLabel's lifetime will be over when the Setup Dialog is closed but the previous slot and signal will still call it
    def closeEvent(self, event):
        self.close_function()
        super().closeEvent(event)

    def close_function(self):
        self.disconnect_signals()
        self.reject()
        self.close()

    def accept_function(self):
        self.disconnect_signals()
        self.accept()
        self.close()

    def disconnect_signals(self):
        self.result_signal.disconnect(self.result_slot)
        self.original_signal.disconnect(self.original_slot)


class Controller(QtWidgets.QWidget):

    def __init__(self, model: Model):
        super().__init__()

        self.model = model

        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.ui.addButton.clicked.connect(self.add_clicked)
        self.ui.fisheyeButton.clicked.connect(self.fisheye_clicked)
        self.ui.paramButton.clicked.connect(self.parameter_clicked)
        self.ui.recordedButton.clicked.connect(self.recorded_clicked)
        self.ui.capturedButton.clicked.connect(self.captured_clicked)

        self.grid_manager = GridManager()

        self.set_stylesheet()

    # find every QPushButton, QLabel, QScrollArea, and Line, this works because this class is a subclass of QWidget
    def set_stylesheet(self):
        [button.setStyleSheet(self.model.style_pushbutton()) for button in self.findChildren(QtWidgets.QPushButton)]
        [label.setStyleSheet(self.model.style_label()) for label in self.findChildren(QtWidgets.QLabel)]
        [scroll_area.setStyleSheet(self.model.style_scroll_area()) for scroll_area in
         self.findChildren(QtWidgets.QScrollArea)]
        self.ui.line.setStyleSheet(self.model.style_line())
        self.ui.line_2.setStyleSheet(self.model.style_line())
        self.ui.line_3.setStyleSheet(self.model.style_line())

    def add_clicked(self):
        ui_idx = self.grid_manager.get_empty_slots()[0]
        label, setup_button, capture_button, delete_button = self.get_monitor_ui_by_idx(ui_idx)

        # I have no idea how this works but I think the order of calling these is important
        # model_apps.create_moildev()
        # model_apps.create_image_original()
        source_type, cam_type, media_source, params_name = self.model.select_media_source()
        if media_source is not None:
            model_apps = ModelApps()
            model_apps.update_file_config()
            model_apps.set_media_source(source_type, cam_type, media_source, params_name)
            # model_apps.create_maps_fov() # no clue what this does

            return_status = self.setup_monitor(model_apps)
            if return_status is False:
                self.delete_monitor(model_apps)
                del model_apps
                return

            model_apps.image_result.connect(lambda img: self.update_label_image(label, img))
            model_apps.create_image_result()

            setup_button.clicked.connect(
                lambda: self.setup_clicked(ui_idx, (source_type, cam_type, media_source, params_name)))
            delete_button.clicked.connect(lambda: self.delete_monitor(model_apps))

            # to keep the model_apps instance alive
            self.grid_manager.set_slot(ui_idx, model_apps)

    def setup_clicked(self, ui_idx: int, media_sources: tuple):
        label, setup_button, capture_button, delete_button = self.get_monitor_ui_by_idx(ui_idx)
        prev_model_apps = self.grid_manager.get_slot_by_index(ui_idx)
        model_apps = ModelApps()
        model_apps.update_file_config()
        model_apps.set_media_source(*media_sources)

        return_status = self.setup_monitor(model_apps)
        if return_status is False:
            del model_apps
            return

        self.delete_monitor(prev_model_apps)
        model_apps.image_result.connect(lambda img: self.update_label_image(label, img))
        model_apps.create_image_result()
        setup_button.clicked.connect(lambda: self.setup_clicked(ui_idx, media_sources))
        delete_button.clicked.connect(lambda: self.delete_monitor(model_apps))
        self.grid_manager.set_slot(ui_idx, model_apps)

    def update_label_image(self, ui_label, image, width=300, scale_content=False):
        self.model.show_image_to_label(ui_label, image, width=width, scale_content=scale_content)

    def setup_monitor(self, model_apps: ModelApps):
        ui_setup = Ui_Setup()
        dialog = SetupDialog()

        ui_setup.setupUi(dialog)
        ui_setup.cancelButton.clicked.connect(dialog.close_function)
        ui_setup.okButton.clicked.connect(dialog.accept_function)

        # set up Anypoint Mode 1 or 2 with state_recent_view = "AnypointView"
        def mode_select_clicked():
            if ui_setup.m1Button.isChecked():
                print('anypoint mode 1')
                model_apps.state_recent_view = "AnypointView"
                model_apps.change_anypoint_mode = "mode_1"
                model_apps.create_maps_anypoint_mode_1()
            else:
                print('anypoint mode 2')
                model_apps.state_recent_view = "AnypointView"
                model_apps.change_anypoint_mode = "mode_2"
                model_apps.create_maps_anypoint_mode_2()

        ui_setup.m1Button.setChecked(True)
        ui_setup.modeSelectGroup.buttonClicked.connect(mode_select_clicked)
        
        mode_select_clicked()
        
        # setup and gracefully close the slots and signals of image_result and signal_image_original from ModelApps
        update_result_label_slot = lambda img: self.update_label_image(ui_setup.label_image_result, img, 320, False)
        dialog.setup_result_signal(update_result_label_slot, model_apps.image_result)
        update_original_label_slot = lambda img: self.update_label_image(ui_setup.label_image_original, img, 320, False)
        dialog.setup_original_signal(update_original_label_slot, model_apps.signal_image_original)

        model_apps.alpha_beta.connect(self.alpha_beta_from_coordinate)
        model_apps.state_rubberband = False  # no idea what this is
        model_apps.set_draw_polygon = True

        # setup mouse events
        # ui_setup.label_image_original.mouseReleaseEvent =
        ui_setup.label_image_original.mouseMoveEvent = lambda event: model_apps.label_original_mouse_move_event(
            ui_setup.label_image_original, event)
        ui_setup.label_image_original.mousePressEvent = lambda event: model_apps.label_original_mouse_move_event(
            ui_setup.label_image_original, event)
        ui_setup.label_image_original.leaveEvent = lambda event: model_apps.label_original_mouse_leave_event()
        # ui_setup.label_image_original.mouseDoubleClickEvent =

        # start setup dialog
        result = dialog.exec()
        if result == QtWidgets.QDialog.DialogCode.Accepted:
            return True
        elif result == QtWidgets.QDialog.DialogCode.Rejected:
            # import os, re
            # os.remove('./models/cached/cache_config.yaml')
            # with open('./models/cached/plugin_cached.yaml', 'w', encoding='utf-8') as fp:
            #     fp.write('plugin_run: 0\n')
            return False
    
    # def mode_select_clicked(self, ui_setup, model_apps):
        

    def delete_monitor(self, model_apps):
        if model_apps is not None:
            model_apps.timer.stop()
            model_apps.__image_result = None
            model_apps.image = None
            model_apps.image_resize = None

            model_apps.reset_config()

            if model_apps.cap is not None:
                try:
                    model_apps.cap.close()
                except:
                    pass
                model_apps.cap = None
            
        ui_idx = self.grid_manager.get_index_of_slot(model_apps)
        if ui_idx == -1: return

        label, setup_button, capture_button, _ = self.get_monitor_ui_by_idx(ui_idx)
        label.setText(' ')
        # delete_button.blockSignals(True)
        setup_button.clicked.disconnect()
        # capture_button.clicked.disconnect()
        # delete_button.clicked.disconnect()

        # delete_button.blockSignals(False)

        self.grid_manager.clear_slot(ui_idx)

    def get_monitor_ui_by_idx(self, ui_idx):
        label = getattr(self.ui, "displayLab%s" % ui_idx)
        setup_button = getattr(self.ui, "setupButton%s" % ui_idx)
        capture_button = getattr(self.ui, "captureButton%s" % ui_idx)
        delete_button = getattr(self.ui, "deleteButton%s" % ui_idx)
        return label, setup_button, capture_button, delete_button

    def alpha_beta_from_coordinate(self, alpha_beta):
        print(alpha_beta)

    def captured_clicked(self):
        pass

    def parameter_clicked(self):
        self.model.form_camera_parameter()

    def fisheye_clicked(self):
        print('fisheye_clicked')

    def recorded_clicked(self):
        print('recorded_clicked')


class Surveillance(PluginInterface):
    def __init__(self):
        super().__init__()
        self.widget = None
        self.description = "This is our plugin application for the surveillance camera project"

    def set_plugin_widget(self, model):
        self.widget = Controller(model)
        return self.widget

    def set_icon_apps(self):
        return "icon.png"

    def change_stylesheet(self):
        self.widget.set_stylesheet()
