from src.plugin_interface import PluginInterface
from src.models.model_apps import Model, ModelApps
from PyQt6 import QtWidgets, QtCore, QtGui
from .ui_main import Ui_Main
from .ui_tile import Ui_Tile
from .ui_setup import Ui_Setup
from .QTileLayout6 import QTileLayout

class CustomDialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
    
    def setup_result_signal(self, slot, signal):
        self.result_slot = slot
        self.result_signal = signal
        self.result_signal.connect(self.result_slot)

    def setup_original_signal(self, slot, signal):
        self.original_slot = slot
        self.original_signal = signal
        self.original_signal.connect(self.original_slot)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Escape:
            event.ignore()  
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.result_signal.disconnect(self.result_slot)
        self.original_signal.disconnect(self.original_slot)
        super().closeEvent(event)

class Controller(QtWidgets.QWidget):

    def __init__(self, model: Model):
        super().__init__()
        
        self.model = model

        self.ui = Ui_Main()
        self.ui.setupUi(self)

        self.ui.addButton.clicked.connect(self.add_clicked)
        self.ui.fisheyeButton.clicked.connect(self.fisheye_clicked)
        self.ui.parameterButton.clicked.connect(self.parameter_clicked)
        self.ui.recordedButton.clicked.connect(self.recorded_clicked)
        self.ui.capturedButton.clicked.connect(self.captured_clicked)

        row_number = 2
        column_number = 4
        vertical_span = 200
        horizontal_span = 300
        spacing = 5

        self.tile_layout = QTileLayout(
            rowNumber=row_number,
            columnNumber=column_number,
            verticalSpan=vertical_span,
            horizontalSpan=horizontal_span,
            verticalSpacing=spacing,
            horizontalSpacing=spacing,
        )
        
        self.tile_layout.acceptDragAndDrop(True)
        self.tile_layout.acceptResizing(True)
        self.tile_layout.setCursorIdle(QtCore.Qt.CursorShape.ArrowCursor)
        self.tile_layout.setCursorGrab(QtCore.Qt.CursorShape.OpenHandCursor)
        self.tile_layout.setCursorResizeHorizontal(QtCore.Qt.CursorShape.SizeHorCursor)
        self.tile_layout.setCursorResizeVertical(QtCore.Qt.CursorShape.SizeVerCursor)
        self.tile_layout.setColorIdle((240, 240, 240))
        self.tile_layout.setColorResize((211, 211, 211))
        self.tile_layout.setColorDragAndDrop((211, 211, 211))
        self.tile_layout.setColorEmptyCheck((150, 150, 150))
        self.tile_layout.activateFocus(False)

        self.ui.scrollAreaWidgetContents.setLayout(self.tile_layout)
        self.ui.scrollArea.setWidgetResizable(True)
        self.ui.scrollArea.setContentsMargins(0, 0, 0, 0)
        self.ui.scrollArea.resizeEvent = self.__tileLayoutResize
        vertical_margins = self.tile_layout.contentsMargins().top() + self.tile_layout.contentsMargins().bottom()
        horizontal_margins = self.tile_layout.contentsMargins().left() + self.tile_layout.contentsMargins().right()
        self.ui.scrollArea.setMinimumHeight(
            row_number * vertical_span + (row_number - 1) * spacing + vertical_margins + 2
        )
        self.ui.scrollArea.setMinimumWidth(
            column_number * horizontal_span + (column_number - 1) * spacing + horizontal_margins + 2
        )

        self.each_tile = {}
        self.set_stylesheet()
    
    def set_stylesheet(self):
        [button.setStyleSheet(self.model.style_pushbutton()) for button in self.findChildren(QtWidgets.QPushButton)]
        [label.setStyleSheet(self.model.style_label()) for label in self.findChildren(QtWidgets.QLabel)]
        [scroll_area.setStyleSheet(self.model.style_scroll_area()) for scroll_area in self.findChildren(QtWidgets.QScrollArea)]
        self.ui.line.setStyleSheet(self.model.style_line())
        
    def add_clicked(self):
        widget_tile = QtWidgets.QWidget()
        ui_tile = Ui_Tile()
        ui_tile.setupUi(widget_tile)
        [w.setStyleSheet(self.model.style_label()) for w in widget_tile.findChildren(QtWidgets.QLabel)]
        [w.setStyleSheet(self.model.style_pushbutton()) for w in widget_tile.findChildren(QtWidgets.QPushButton)]
        [w.setStyleSheet(self.model.style_slider()) for w in widget_tile.findChildren(QtWidgets.QSlider)]
        
        i_row, i_column = 0, 0
        while not self.tile_layout.isAreaEmpty(i_row, i_column, 1, 1):
            i_column += 1
            if i_column > 4:
                i_row = (i_row + 1) % 2
                i_column = 0

        self.tile_layout.addWidget(
            widget=widget_tile,
            fromRow=i_row,
            fromColumn=i_column,
        )        

        model_apps = ModelApps()
        model_apps.create_moildev()
        model_apps.create_image_original()
        model_apps.update_file_config()
        source_type, cam_type, media_source, params_name = self.model.select_media_source()
        model_apps.set_media_source(source_type, cam_type, media_source, params_name)
        # model_apps.create_maps_fov()
        model_apps.image_result.connect(lambda img: self.update_label_image(img, ui_tile.videoLabel))
        self.update_label_image(model_apps.image, ui_tile.videoLabel)
        ui_tile.setupButton.clicked.connect(lambda : self.setup_tile(widget_tile, ui_tile, model_apps))
        self.each_tile[widget_tile] = {'model_apps' : model_apps, 'ui' : ui_tile}

    def update_label_image(self, image, ui_label, width=400, scale_content=True):
        self.model.show_image_to_label(ui_label, image, width=width, scale_content=scale_content)

    def setup_tile(self, widget_tile, ui_tile, model_apps : ModelApps):
        ui_setup = Ui_Setup()
        dialog = CustomDialog()
        ui_setup.setupUi(dialog)
        update_result_label_slot = lambda img: self.update_label_image(img, ui_setup.label_image_result, 320, False)
        dialog.setup_result_signal(update_result_label_slot, model_apps.image_result)
        update_original_label_slot = lambda img: self.update_label_image(img, ui_setup.label_image_original, 320, False)
        dialog.setup_original_signal(update_original_label_slot, model_apps.signal_image_original)
        model_apps.state_rubberband = False
        model_apps.state_recent_view = "AnypointView"
        model_apps.change_anypoint_mode = "mode_1"
        model_apps.set_draw_polygon = True
        model_apps.create_maps_anypoint_mode_1()
        model_apps.update_file_config()
        model_apps.create_image_result()
        # dialog.setWindowFlags(dialog.windowFlags() & ~QtCore.Qt.WindowType.WindowCloseButtonHint)
        dialog.exec()

    def captured_clicked(self):
        pass

    def parameter_clicked(self):
        self.model.form_camera_parameter()

    def fisheye_clicked(self):
        print('fisheye_clicked')

    def recorded_clicked(self):
        print('recorded_clicked')
    
    def __tileLayoutResize(self, a0):
        self.tile_layout.updateGlobalSize(a0)
    

class SurveillanceFisheyeCamera(PluginInterface):
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
