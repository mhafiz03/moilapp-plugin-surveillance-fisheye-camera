from src.plugin_interface import PluginInterface
from src.models.model_apps import Model, ModelApps
from PyQt6 import QtWidgets, QtCore, QtGui
from .surveillance import Ui_Form
from .ui_setup import Ui_Setup


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
            self.close()
        else:
            super().keyPressEvent(event)

    # need to disconnect the signals and slots else RuntimeError: wrapped C/C++ object of type QLabel has been deleted
    # because the QLabel's lifetime will be over when the Setup Dialog is closed but the previous slot and signal will still call it
    def closeEvent(self, event):
        self.result_signal.disconnect(self.result_slot)
        self.original_signal.disconnect(self.original_slot)
        super().closeEvent(event)


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

        # this dictionary (it was previously a list) is to keep the ModelApps instance (created later) alive in this class object
        self.each_tile = {}
        self.set_stylesheet()

    # find every QPushButton, QLabel, QScrollArea, and Line, this works because this class is a subclass of QWidget
    def set_stylesheet(self):
        [button.setStyleSheet(self.model.style_pushbutton()) for button in self.findChildren(QtWidgets.QPushButton)]
        [label.setStyleSheet(self.model.style_label()) for label in self.findChildren(QtWidgets.QLabel)]
        [scroll_area.setStyleSheet(self.model.style_scroll_area()) for scroll_area in self.findChildren(QtWidgets.QScrollArea)]
        self.ui.line.setStyleSheet(self.model.style_line())
        self.ui.line_2.setStyleSheet(self.model.style_line())
        self.ui.line_3.setStyleSheet(self.model.style_line())

    # create new widget with ui_tile design and add it into the tile_layout
    def add_clicked(self):
        widget_tile = QtWidgets.QWidget()
        ui_tile = Ui_Form()
        ui_tile.setupUi(widget_tile)
        [w.setStyleSheet(self.model.style_label()) for w in widget_tile.findChildren(QtWidgets.QLabel)]
        [w.setStyleSheet(self.model.style_pushbutton()) for w in widget_tile.findChildren(QtWidgets.QPushButton)]
        [w.setStyleSheet(self.model.style_slider()) for w in widget_tile.findChildren(QtWidgets.QSlider)]

        # I have no idea how this works but I think the order of calling these is important
        model_apps = ModelApps()
        model_apps.create_moildev()
        model_apps.create_image_original()
        model_apps.update_file_config()
        source_type, cam_type, media_source, params_name = self.model.select_media_source()
        model_apps.set_media_source(source_type, cam_type, media_source, params_name)
        # model_apps.create_maps_fov() # no clue what this does

        model_apps.image_result.connect(lambda img: self.update_label_image(img, ui_tile.displayLab1))
        # the above is sufficient if wanting to display videos, but the below one is needed to display images
        self.update_label_image(model_apps.image, ui_tile.displayLab1)

        ui_tile.setupButton1.clicked.connect(lambda: self.setup_tile(widget_tile, ui_tile, model_apps))

        # to make the model_apps instance alive
        self.each_tile[widget_tile] = {'model_apps': model_apps, 'ui': ui_tile}

    def update_label_image(self, image, ui_label, width=400, scale_content=True):
        self.model.show_image_to_label(ui_label, image, width=width, scale_content=scale_content)

    def setup_tile(self, widget_tile, ui_tile, model_apps: ModelApps):
        ui_setup = Ui_Setup()
        dialog = SetupDialog()
        ui_setup.setupUi(dialog)

        # setup and gracefully close the slots and signals of image_result and signal_image_original from ModelApps
        update_result_label_slot = lambda img: self.update_label_image(img, ui_setup.label_image_result, 320, False)
        dialog.setup_result_signal(update_result_label_slot, model_apps.image_result)
        update_original_label_slot = lambda img: self.update_label_image(img, ui_setup.label_image_original, 320, False)
        dialog.setup_original_signal(update_original_label_slot, model_apps.signal_image_original)

        model_apps.alpha_beta.connect(self.alpha_beta_from_coordinate)
        model_apps.state_rubberband = False  # no idea what this is

        # set up Anypoint Mode 1 with state_recent_view = "AnypointView"
        # and change_anypoint_mode = "mode_1" then create_maps_anypoint_mode_1()
        model_apps.state_recent_view = "AnypointView"
        model_apps.change_anypoint_mode = "mode_1"
        model_apps.set_draw_polygon = True
        model_apps.create_maps_anypoint_mode_1()

        # setup mouse events
        # just mouseMoveEvent is sufficient but without mousePressEvent, it will be laggy (on my machine, YMMV)
        # ui_setup.label_image_original.mouseReleaseEvent =
        ui_setup.label_image_original.mouseMoveEvent = lambda event: model_apps.label_original_mouse_move_event(
            ui_setup.label_image_original, event)
        ui_setup.label_image_original.mousePressEvent = lambda event: model_apps.label_original_mouse_move_event(
            ui_setup.label_image_original, event)
        ui_setup.label_image_original.leaveEvent = lambda event: model_apps.label_original_mouse_leave_event()
        # ui_setup.label_image_original.mouseDoubleClickEvent =

        # start setup dialog
        dialog.exec()

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

    # def __tileLayoutResize(self, a0):
    #     self.tile_layout.updateGlobalSize(a0)


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
