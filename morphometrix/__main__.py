#usr/bin/env python
import os
import sys
import csv
import traceback
import platform
from datetime import date
from itertools import cycle, islice
import numpy as np
import webbrowser
from scipy.linalg import pascal
from scipy.sparse import diags
from scipy.optimize import root_scalar

from PySide6 import QtGui, QtCore
from PySide6.QtWidgets import QSlider ,QColorDialog ,QGraphicsTextItem ,QComboBox, QMainWindow, QApplication, QGraphicsView, QGraphicsScene, QWidget, QToolBar, QPushButton, QLabel, QLineEdit, QPlainTextEdit, QGridLayout, QFileDialog, QGraphicsLineItem, QGraphicsPixmapItem,QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsItem, QMessageBox, QInputDialog, QDockWidget, QSizePolicy, QRadioButton
from PySide6.QtGui import QShortcut, QFont, QPixmap, QCursor
from PySide6.QtCore import Qt

# ------------------------------
#   Developed By:
#   Walter Torres
#   Kevin Bierlich
#   Clara Bird
#   Elliott Chimienti
# ------------------------------
#   Packages (Universal2 Installs and Wheels for MacOS!):
#   Python 3.10.8
#   PyQt6 6.5.1
#   Numpy 1.21.6
#   Scipy 1.9.1
# ------------------------------


def bezier(t,P,k,arc = False):
    """
    Matrix representation of Bezier curve following
    https://pomax.github.io/bezierinfo/#arclength
    """
    signs = np.array([i for j,i in zip(range(k+1),islice(cycle([1, -1]),0,None))]) #create array alternating 0,1s for diagonals
    A = pascal(k+1, kind='lower') #generate Pascal triangle matrix
    S = diags(signs, [i-k for i in range(k+1)][::-1], shape=(k+1, k+1)).toarray() #create signs matrix
    M = A*S #multiply pascals by signs to get Bernoulli polynomial matrix
    coeff = A[-1,:]
    C = M*coeff[:,None] #broadcast
    T = np.array( [t**i for i in range(k+1)] ).T

    B = T.dot( C.dot(P) )

    if arc:
        return np.linalg.norm(B, axis = 1)
    else:
        return B

def gauss_legendre(b, f, P, k, arc, loc = 0.0, L = 1, degree = 24, a = 0):
    """
    Gauss-Legendre Quadrature for bezier curve arc length
    """
    x, w = np.polynomial.legendre.leggauss(degree)
    t = 0.5*(b-a)*x + 0.5*(b+a)

    return 0.5*(b-a)*np.sum( w*bezier(t,P,k,arc) )/L - loc


class Window(QWidget):

    def __init__(self, iw):
        #init methods runs every time, use for core app stuff)
        super(Window, self).__init__()
        self.iw = iw    # Reference for color picker

        self.label_id = QLabel("Image ID")
        self.id = QLineEdit()
        self.id.setText('0000')

        #Define custom attributes for pixel -> SI conversion
        self.label_foc = QLabel("Focal Length (mm):")
        self.focal = QLineEdit()
        self.focal.setText('50')

        self.label_alt = QLabel("Altitude (m):")
        self.altitude = QLineEdit()
        self.altitude.setText('50')

        self.label_pd = QLabel("Pixel Dimension (mm/pixel)")
        self.pixeldim = QLineEdit()
        self.pixeldim.setText('0.00391667')

        self.label_widths = QLabel("# Width Segments:")
        self.numwidths = QLineEdit()
        self.numwidths.setText('10')

        self.label_side = QLabel("Mirror Side:")
        self.side_bias = QComboBox()
        self.side_bias.addItems(["None","Side A", "Side B"])

        self.label_scale = QLabel("Crosshair Size")
        self.scale_slider = QSlider(orientation=Qt.Orientation.Horizontal)
        self.scale_slider.setMaximum(20)
        self.scale_slider.setValue(10)
        self.scale_slider.valueChanged.connect(self.slider_changed)

        self.label_not = QLabel("Notes:")
        self.notes = QPlainTextEdit()

        self.label_color = QLabel("Crosshair Color: ")
        self.button_color = QPushButton()
        self.button_color.setStyleSheet("background-color: red")
        self.button_color.clicked.connect(self.color_changed)

        self.manual = QPushButton("Manual", self)
        self.manual.clicked.connect(lambda: webbrowser.open('https://github.com/wingtorres/morphometrix'))

        self.exit = QPushButton("Exit", self)
        self.exit.clicked.connect(self.close_application)

        self.grid = QGridLayout()
        self.grid.addWidget(self.label_id, 1, 0)
        self.grid.addWidget(self.id, 1, 1)
        self.grid.addWidget(self.label_foc, 2, 0)
        self.grid.addWidget(self.focal, 2, 1)
        self.grid.addWidget(self.label_alt, 3, 0)
        self.grid.addWidget(self.altitude, 3, 1)
        self.grid.addWidget(self.label_pd, 4, 0)
        self.grid.addWidget(self.pixeldim, 4, 1)
        self.grid.addWidget(self.label_widths, 5, 0)
        self.grid.addWidget(self.numwidths, 5, 1)
        self.grid.addWidget(self.label_side,6,0)
        self.grid.addWidget(self.side_bias,6,1)
        self.grid.addWidget(self.label_scale,7,0)
        self.grid.addWidget(self.scale_slider,7,1)
        self.grid.addWidget(self.label_not, 8, 0)
        self.grid.addWidget(self.notes, 8, 1)
        self.grid.addWidget(self.label_color,9,0)
        self.grid.addWidget(self.button_color,9,1)
        self.grid.addWidget(self.manual, 10, 3)
        self.grid.addWidget(self.exit, 11, 3)
        self.setLayout(self.grid)

    def color_changed(self):
        color = QColorDialog().getColor()   # Returns QColor
        self.button_color.setStyleSheet("background-color: "+color.name())
        self.iw.picked_color = color

    def slider_changed(self):
        self.scale_slider.value() # Value grab lags behind actually value?
        self.iw.slider_moved(self.scale_slider.value())

    def close_application(self):
        choice = QMessageBox.question(self, 'exit', "Exit program?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if choice == QMessageBox.StandardButton.Yes:
            self.parent().deleteLater()
            self.parent().close()
        else:
            pass

#references:
#https://stackoverflow.com/questions/26901540/arc-in-qgraphicsscene/26903599#26903599
#https://stackoverflow.com/questions/27109629/how-can-i-resize-the-main-window-depending-on-screen-resolution-using-pyqt
class MainWindow(QMainWindow):

    def __init__(self, parent = None):
        super(MainWindow, self).__init__()

        D = self.screen().availableGeometry()
        self.move(0,0)#center.x() + .25*D.width() , center.y() - .5*D.height() )
        self.resize( int(.95*D.width()), int(6*D.height()) )

        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized
                            | QtCore.Qt.WindowState.WindowActive)
        self.activateWindow()


        self.iw = imwin()           # Image window
        self.subWin = Window(self.iw)
        self.setCentralWidget(self.iw)

        #Stacked dock widgets
        docked1 = QDockWidget("", self)
        docked2 = QDockWidget("", self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, docked1)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, docked2)
        docked1.setWidget(self.subWin)
        docked1.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        self.setCorner(QtCore.Qt.Corner.TopLeftCorner, QtCore.Qt.DockWidgetArea.LeftDockWidgetArea);
        self.setCorner(QtCore.Qt.Corner.TopRightCorner, QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(QtCore.Qt.Corner.BottomLeftCorner, QtCore.Qt.DockWidgetArea.LeftDockWidgetArea);
        self.setCorner(QtCore.Qt.Corner.BottomRightCorner, QtCore.Qt.DockWidgetArea.RightDockWidgetArea)
        self.resizeDocks( (docked1,docked2), (400,400), QtCore.Qt.Orientation.Horizontal )

        self.exportButton = QPushButton("Export Measurements", self)
        self.exportButton.clicked.connect(self.export_measurements)
        self.exportButton.setEnabled(False)

        self.importImage = QPushButton("New Image", self)
        self.importImage.clicked.connect(self.file_open)

        self.lengthButton = QPushButton("Measure Length", self)
        self.lengthButton.clicked.connect(self.measure_length)
        self.lengthButton.setEnabled(False)
        self.lengthButton.setCheckable(True)
        self.lengthNames = []

        self.widthsButton = QPushButton("Measure Widths", self)
        self.widthsButton.clicked.connect(self.measure_widths)
        self.widthsButton.setEnabled(False)
        self.widthsButton.setCheckable(True)
        self.widthNames = []

        self.areaButton = QPushButton("Measure Area", self)
        self.areaButton.clicked.connect(self.measure_area)
        self.areaButton.setEnabled(False)
        self.areaButton.setCheckable(True)
        self.areaNames = []

        self.angleButton = QPushButton("Measure Angle", self)
        self.angleButton.clicked.connect(self.measure_angle)
        self.angleButton.setEnabled(False)
        self.angleButton.setCheckable(True)
        self.angleNames = []

        shortcut_polyClose = QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Tab), self)
        shortcut_polyClose.activated.connect(self.iw.polyClose)

        self.undoButton = QPushButton("Undo", self)
        self.undoButton.clicked.connect(self.undo)
        self.undoButton.setEnabled(False)

        shortcut_undo = QShortcut(QtGui.QKeySequence('Ctrl+Z'), self)
        shortcut_undo.activated.connect(self.undo)

        self.bezier = QRadioButton("Bezier fit", self)
        self.bezier.setEnabled(True)
        self.bezier.setChecked(True)

        self.piecewise = QRadioButton("Piecewise", self)

        self.statusbar = self.statusBar()
        self.statusbar.showMessage('Select new image to begin')

        self.tb = QToolBar('Toolbar')
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tb.addWidget(spacer)
        self.addToolBar(self.tb)
        self.tb.addWidget(self.importImage)
        self.tb.addWidget(self.exportButton)
        self.tb.addWidget(self.lengthButton)
        self.tb.addWidget(self.widthsButton)
        self.tb.addWidget(self.areaButton)
        self.tb.addWidget(self.angleButton)
        self.tb.addWidget(self.undoButton)
        self.tb.addWidget(self.bezier)
        self.tb.addWidget(self.piecewise)

    def file_open(self):

        self.iw.scene.clear()
        self.image_name = QFileDialog.getOpenFileName(self, 'Open File')
        self.iw.pixmap = QtGui.QPixmap(self.image_name[0])
        self.iw.pixmap_fit = self.iw.pixmap.scaled(
            self.iw.pixmap.width(),
            self.iw.pixmap.height(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation)
        self.iw.scene.addPixmap(self.iw.pixmap_fit)  #add image
        self.iw.setScene(self.iw.scene)

        #Adjust window size automatically?
        self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self.iw.scene.update()
        self.statusbar.showMessage('Select a measurement to make from the toolbar')

        self.lengthButton.setEnabled(True)
        self.areaButton.setEnabled(True)
        self.angleButton.setEnabled(True)
        self.exportButton.setEnabled(True)
        self.undoButton.setEnabled(True)    # Why is this enabled when file is opened?
        self.bezier.setEnabled(True)
        self.bezier.setChecked(True)
        self.widthsButton.setEnabled(False)

        self.angleNames = []
        self.areaNames = []
        self.lengthNames = []
        self.widthNames = []

        self.iw.ellipses = []       # Stores ellipse objects 
        self.iw.widths = []         # Stores calculated width lengths on export
        self.iw.lengths = [[]]      # Stores length objects
        self.iw.L = posData(
            np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #lengths
        self.iw.A = posData(
            np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #area
        self.iw.W = posData(
            np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #widths
        self.iw.T = angleData(np.empty(shape=(0, 0)))  #angles
        self.iw.angleValues = np.empty((0,0))
        self.iw.areaValues = np.empty((0,0))
        
        self.iw._lastpos = None
        self.iw._thispos = None
        self.iw.measuring_length = False
        self.iw.measuring_area = False
        self.iw.measuring_widths = False
        self.iw.measuring_angle = False
        self.iw._zoom = 0
        self.iw.factor = 1.0
        self.iw.d = {}  #dictionary for line items
        self.iw.k = 0  #initialize counter so lines turn yellow
        self.iw.m = None
        self.iw.scene.realline = None
        self.iw.scene.testline = None
        self.iw.scene.ellipseItem = None
        self.iw.scene.area_ellipseItem = None
        self.iw.scene.polyItem = None
        self.iw.image_name = None

    def measure_length(self):

        self.lel = QLineEdit(self)
        self.lel.move(130, 22)
        text, ok = QInputDialog.getText(self, 'Input Dialog', 'Length name')

        if ok:
            self.lel.setText(str(text))
            self.lengthNames.append(self.lel.text())
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)  #change cursor
            self.widthsButton.setChecked(False)
            self.widthsButton.setEnabled(False)
            self.iw.line_count = 0
            self.iw.measuring_length = True
            self.iw.L = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))  #preallocate
            self.iw._lastpos = None
            self.iw._thispos = None
            self.statusbar.showMessage('Click initial point for length measurement')
        else:
            self.lengthButton.setChecked(False)

    def measure_widths(self):
        print("Length names: ", self.lengthNames)
        self.widthNames.append(self.lengthNames[-1])  # Store most recent length name
        self.iw.measure_widths()  # Call width function within graphics view

    def measure_angle(self):

        self.lea = QLineEdit(self)
        self.lea.move(130, 22)
        text, ok = QInputDialog.getText(self, 'Input Dialog', 'Angle name')

        if ok:
            self.lea.setText(str(text))
            self.angleNames.append(self.lea.text())
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)  #change cursor
            self.bezier.setEnabled(False)
            self.iw.measuring_angle = True
            self.iw._lastpos = None
            self.iw._thispos = None
            self.statusbar.showMessage('Click initial point for angle measurement')
        else:
            self.angleButton.setChecked(False)

    def measure_area(self):

        self.lea = QLineEdit(self)
        self.lea.move(130, 22)
        text, ok = QInputDialog.getText(self, 'Input Dialog', 'Area name')

        if ok:
            self.lea.setText(str(text))
            self.areaNames.append(self.lea.text())
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)  #change cursor
            self.bezier.setEnabled(False)
            self.iw.line_count = 0
            self.iw.measuring_area = True
            self.iw._lastpos = None
            self.iw._thispos = None
            self.iw.A = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))  #preallocate
            self.statusbar.showMessage('Click initial point for area measurement')
        else:
            self.areaButton.setChecked(False)

    # Create list (creation_record) of PyQt objects drawn to screen in order of creation
    # Pop length, angle, area, or width measurement lists depending on pop object in creation_record
    def undo(self):

        pass
        # if self.iw.measuring_length:
        #     self.iw._thispos = self.iw._lastpos
        #     self.iw.L.downdate()  #remove data
        #     self.iw.line_count += -1
        #     self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
        #     self.iw.scene.realline = False

        # if self.iw.measuring_area:
        #     self.iw._thispos = self.iw._lastpos
        #     self.iw.A.downdate()  #remove data
        #     self.iw.line_count += -1
        #     self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
        #     self.iw.scene.realline = False

        # if self.iw.measuring_angle:
        #     self.iw.T.downdate()  #remove data
        #     self.iw._thispos = self.iw_lastpos
        #     self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
        #     self.iw.scene.realline = False

    def export_measurements(self):
        # Gets largest image dimension and divides it by its on screen dimension?
        fac = max(self.iw.pixmap.width(), self.iw.pixmap.height()) / max(
            self.iw.pixmap_fit.width(),
            self.iw.pixmap_fit.height())  #scale pixel -> m by scaled image
        # Popup to get user save file input
        name = QFileDialog.getSaveFileName(
            self, 'Save File', self.image_name[0].split('.', 1)[0])[0]
        self.pixeldim = float(self.subWin.pixeldim.text())
        self.altitude = float(self.subWin.altitude.text())
        self.focal = float(self.subWin.focal.text())
        #okay in mm https://www.imaging-resource.com/PRODS/sony-a5100/sony-a5100DAT.HTM
        if name:
            #Convert pixels to meters
            areas = self.iw.areaValues * (
                fac * self.pixeldim * self.altitude / self.focal)**2
            values_optical = np.array([
                self.subWin.id.text(), self.image_name[0], self.focal,
                self.altitude, self.pixeldim
            ])

            names_optical = [
                'Image ID', 'Image Path', 'Focal Length', 'Altitude',
                'Pixel Dimension'
            ]

	        #Write .csv file
            print(f"Writing {name} to file")
            with open(name + '.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Object","Value","Value_unit"])  # Define Columns

                # Writes image & flight data
                for (f, g) in zip(names_optical, values_optical):
                    writer.writerow([f, g, "Metadata"])
                writer.writerow(['Mirror Side', self.subWin.side_bias.currentText(), "Metadata"])     # Side Bias (Not implemented yet)
                writer.writerow(['Notes', self.subWin.notes.toPlainText(), "Metadata"])     # Notes

                # Initial output in meters, then pixels
                self.iw.widths.clear() # Clear array for output
                self.iw.calculate_widths(self.subWin.side_bias.currentText())      # Calculate widths of MovingEllipses at export
                # Measurements in meters  \/ \/ \/ --------------------------------------------
                # Make check for first length line
                if self.lengthNames:
                    width_index = 0
                    for k,m in enumerate(self.lengthNames):
                        l = "{0:.2f}".format(self.iw.lengths[k] * fac * self.pixeldim * self.altitude / self.focal)
                        writer.writerow([m,l, "Meters"])  # Writes [Length Name][Length Measurement meters][Length measurement pixels]
                        if width_index < len(self.widthNames) and self.widthNames[width_index] == m: # Check if current length has widths or if width exists
                            # Iterate over width measurements
                            for idx,width in enumerate(self.iw.widths[width_index]):
                                l = "{0:.2f}".format(width * fac * self.pixeldim * self.altitude / self.focal)
                                width_percent = "{0:.2f}".format(((idx+1)/(len(self.iw.widths[width_index])+1))*100)
                                writer.writerow([self.widthNames[width_index]+"_w"+str(width_percent),l,"Meters"])
                            width_index += 1 # Incease index

                # Write angles (Fix output)
                for k, f in enumerate(self.angleNames):
                    line = "{0:.3f}".format(self.iw.angleValues[k])
                    writer.writerow([f,line, "Degrees"])

                # Write Area ()
                for k, f in enumerate(self.areaNames):
                    line = "{0:.3f}".format(areas[k])
                    writer.writerow([f,line,"Square Meters"])

                # Measurements in pixels \/ \/ \/ --------------------------------------------
                # Make check for first length line
                if self.lengthNames:
                    width_index = 0
                    for k,m in enumerate(self.lengthNames):
                        l = "{0:.1f}".format(self.iw.lengths[k])    # Pixels
                        writer.writerow([m,l, "Pixels"])  # Writes [Length Name][Length Measurement meters][Length measurement pixels]
                        if width_index < len(self.widthNames) and self.widthNames[width_index] == m: # Check if current length has widths or if width exists
                            # Iterate over width measurements
                            for idx,width in enumerate(self.iw.widths[width_index]):
                                l = "{0:.1f}".format(width)
                                width_percent = "{0:.1f}".format(((idx+1)/(len(self.iw.widths[width_index])+1))*100)
                                writer.writerow([self.widthNames[width_index]+"_w"+str(width_percent),l,"Pixels"])
                            width_index += 1 # Incease index

                # Write angles
                for k, f in enumerate(self.angleNames):  #write angles
                    line = "{0:.3f}".format(self.iw.angleValues[k])
                    writer.writerow([f, line,"Degrees"])

                # Write Area
                for k, f in enumerate(self.areaNames):
                    line = "{0:.1f}".format(self.iw.areaValues[k])
                    writer.writerow([f,line,"Pixels"])


            #Export image
            self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            pix = QtGui.QPixmap(self.iw.viewport().size())
            self.iw.viewport().render(pix)
            pix.save(name + '-measurements.png')

class imwin(QGraphicsView):  #Subclass QLabel for interaction w/ QPixmap
    def __init__(self, parent=None):
        super(imwin, self).__init__(parent)
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)

        self.picked_color = QtGui.QColor("red")
        self.slider_pos = 10
        self.pixmap = None
        self._lastpos = None
        self._thispos = None
        self.delta = QtCore.QPointF(0, 0)
        self.nm = None
        self.measuring_length = False
        self.measuring_widths = False
        self.measuring_area = False
        self.measuring_angle = False
        self._zoom = 1
        self.newPos = None
        self.oldPos = None
        self.factor = 1.0
        self.numwidths = None

        self.ellipses = []
        self.lines = []
        self.areas = []
        #self.d = {}  #dictionary for line items
        self.L = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
        self.W = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
        
        self.scene.realline = None
        self.scene.testline = None
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def slider_moved(self, value):
        self.slider_pos = value
        for ellipse_group in self.ellipses:   # iterate over every group of ellipses
            for ellipse in ellipse_group:
                ellipse.update_scale(value)
                

    # Calculates width between corresponding ellipses
    # Calculates distance in pixels and appends widths[] list
    # Input: None
    # Output: None
    def calculate_widths(self,bias):
        for x in range(0,len(self.ellipses)):   # iterate over every group of ellipses
            calculated_widths = []
            for y in range(0,len(self.ellipses[x]),2):  # Iterate over every ellipse in group (might be causing incorrect amount at export issue)
                if bias == 'None':
                    width = np.sqrt(
                            (self.ellipses[x][y].scenePos().x() - self.ellipses[x][y+1].scenePos().x())**2 +
                            (self.ellipses[x][y].scenePos().y() - self.ellipses[x][y+1].scenePos().y())**2)  #calculate width of entire line
                elif bias == 'Side A':
                    # (A point - centerlinePoint) * 2
                    # print("P1x: ",self.ellipses[x][y].scenePos().x())
                    # print("P2x: ",self.ellipses[x][y].cetnerLinePoint.x())
                    width = np.sqrt(
                            ((self.ellipses[x][y].scenePos().x() - self.ellipses[x][y].cetnerLinePoint.x())*2)**2 +
                            ((self.ellipses[x][y].scenePos().y() - self.ellipses[x][y].cetnerLinePoint.y())*2)**2)  #calculate width of entire line
                else:   # Bias B
                    # (B point - centerlinePoint) * 2
                    # print("P1x: ",self.ellipses[x][y+1].scenePos().x())
                    # print("P2x: ",self.ellipses[x][y+1].cetnerLinePoint.x())
                    width = np.sqrt(
                            ((self.ellipses[x][y+1].scenePos().x() - self.ellipses[x][y+1].cetnerLinePoint.x())*2)**2 +
                            ((self.ellipses[x][y+1].scenePos().y() - self.ellipses[x][y+1].cetnerLinePoint.y())*2)**2)  #calculate width of entire line
                calculated_widths.append(width) # Stored widths in temporary array
            self.widths.append(calculated_widths)    # Output is in Pixels

    def qpt2pt(self, x, y):
        Q = self.mapFromScene( self.mapToScene( int(x), int(y)) )
        return Q.x(), Q.y()

    def keyPressEvent(self, event):  #shift modifier for panning
        if event.key() == QtCore.Qt.Key.Key_Shift:
            pos = QtGui.QCursor.pos()
            self.oldPos = self.mapToScene(self.mapFromGlobal(pos))

    # Return cursor to normal after grabbing screen
    def keyReleaseEvent(self, event):
        if event.key() == QtCore.Qt.Key.Key_Shift:
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)  #change cursor

    def mouseMoveEvent(self, event):
        data = self.mapToScene(event.position().toPoint())
        rules = [self.measuring_length, self.measuring_angle, self.measuring_area]

        modifiers = QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.KeyboardModifier.ShiftModifier and self.oldPos:
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            self.newPos = data
            delta = self.newPos - self.oldPos
            self.translate(delta.x(), delta.y())
        elif (any(rules)):
            QApplication.setOverrideCursor(QtCore.Qt.CursorShape.CrossCursor)  #change cursor

        #dragging line
        if self._thispos and any(rules):
            if self.measuring_length:
                self.parent().statusbar.showMessage(
                    'Click to place next point... double click to finish')
            if self.measuring_area:
                self.parent().statusbar.showMessage(
                    'Click to place next point... close polygon to finish')
            if self.measuring_angle:
                self.parent().statusbar.showMessage(
                    'Click point to define vector')

            end = QtCore.QPointF(data)#self.mapToScene(event.pos()))
            start = self._thispos

            if self.measuring_angle and self._lastpos:
                start = self._thispos

            if self.scene.testline:  #remove old line
                self.scene.removeItem(self.scene.testline)
                self.scene.testline = False

            if self.measuring_area and self.line_count > 2:
                intersect, xi, yi, k = self.A.checkIntersect(data.x(),data.y())
                if self.scene.area_ellipseItem: #remove existing intersect
                    self.scene.removeItem(self.scene.area_ellipseItem)
                    self.scene.area_ellipseItem = False
                if self.scene.polyItem:
                    self.scene.removeItem(self.scene.polyItem)
                    self.scene.polyItem = False
                if intersect:
                    #indicate intersect point
                    p = QtCore.QPointF(xi, yi)
                    self.scene.area_ellipseItem = QGraphicsEllipseItem(0, 0, 10, 10)
                    self.scene.area_ellipseItem.setPos(p.x() - 10 / 2, p.y() - 10 / 2)
                    self.scene.area_ellipseItem.setBrush(
                    QtGui.QBrush(QtGui.QColor('blue'))) #, style=QtCore.Qt.BrushStyle.SolidPattern))
                    self.scene.area_ellipseItem.setFlag(
                    QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
                    False)  #size stays small, but doesnt translate if set to false
                    self.scene.addItem(self.scene.area_ellipseItem)
                    #shade polygon region
                    points = [ QtCore.QPointF(x,y) for x,y in zip( self.A.x[k:], self.A.y[k:] ) ]
                    points.append(QtCore.QPointF(xi,yi))
                    self.scene.polyItem = QGraphicsPolygonItem(QtGui.QPolygonF(points))
                    self.scene.polyItem.setBrush( QtGui.QBrush(QtGui.QColor(255,255,255,127)) )
                    self.scene.addItem(self.scene.polyItem)

            self.scene.testline = QGraphicsLineItem(QtCore.QLineF(start, end))
            self.scene.addItem(self.scene.testline)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        #only delete lines if bezier fit
        if self.measuring_length and self.parent().bezier.isChecked() and (len(np.vstack((self.L.x, self.L.y)).T) > 2):
            self.parent().statusbar.showMessage('Length measurement complete.')
            #Remove most recent items drawn (exact lines)
            nl = self.line_count
            for k, i in enumerate(self.scene.items()):
                if k < nl:
                    self.scene.removeItem(i) #set item to false?

        if self._lastpos and self.measuring_length:
            # catmull roms spline instead?
            # or rational bezier curve - tuneable approximating/interpolating. ref. wikipedia
            # https://codeplea.com/introduction-to-splines

            if (self.parent().bezier.isChecked()) and (len(np.vstack((self.L.x, self.L.y)).T) > 1):
                nt = 100 #max(1000, self.numwidths * 50)  #num of interpolating points
                t = np.linspace(0.0, 1.0, nt)
                self.P = np.vstack((self.L.x, self.L.y)).T #control points
                self.kb = len(self.P) - 1 #order of bezier curve # of control points (n) - 1

                B = bezier(t, self.P, k = self.kb) #evaluate bezier curve along t
                self.Q = self.kb*np.diff(self.P, axis = 0)
                self.l = gauss_legendre(b = 1, f = bezier, P = self.Q, k = self.kb - 1, arc = True) #compute total arc length.
                self.lengths[-1] = self.l

                self.xs, self.ys = B[:,0], B[:,1]

                #draw cubic line to interpolated points
                for i in range(1, nt - 1):
                    P0 = QtCore.QPointF( self.xs[i-1], self.ys[i-1] )#.toPoint()
                    P1 = QtCore.QPointF( self.xs[i  ], self.ys[i  ] )#.toPoint()
                    P2 = QtCore.QPointF( self.xs[i+1], self.ys[i+1] )#.toPoint()

                    path = QtGui.QPainterPath(P0)
                    path.cubicTo(P0, P1, P2)
                    self.scene.addPath(path)

            self.lengths.extend([np.nan])

        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)  #change cursor
        if self.parent().bezier.isChecked() or (len(np.vstack((self.L.x, self.L.y)).T) <= 2):
            #measure widths possible if bezier or if single piecewise segment
            self.parent().widthsButton.setEnabled(True)

        self.parent().lengthButton.setChecked(False)
        self.parent().angleButton.setChecked(False)
        self.measuring_length = False
        self.measuring_angle = False
        self._thispos = False

    def polyClose(self): #make into hot key not button
        if self.measuring_area:
            if self.line_count > 2: #cant make polygon w/ two lines
                self.measuring_area = False
                A = self.A.calcArea()
                self.areaValues = np.append(self.areaValues, A) #add area values
                #draw permanent polygon
                points = [ QtCore.QPointF(x,y) for x,y in zip( self.A.x, self.A.y ) ]
                self.scene.polyItem2 = QGraphicsPolygonItem(QtGui.QPolygonF(points))
                self.scene.polyItem2.setBrush( QtGui.QBrush(QtGui.QColor(255,255,255,127)) )
                if self.scene.polyItem:
                    self.scene.removeItem(self.scene.polyItem) #remove mouseover polygon
                    self.scene.polyItem = False #remove mouseover polygon
                self.scene.removeItem(self.scene.testline)
                self.scene.testline = False
                self.scene.addItem(self.scene.polyItem2) #shade in polygon
                self.parent().statusbar.showMessage('Polygon area measurement completed')
                self.parent().areaButton.setChecked(False)
                self.parent().bezier.setEnabled(True) #make bezier fit available again
            else:
                print("cannot draw polygon with fewer than three vertices")

    # Measure widths of aquatic animal (Called when GUI button is pressed)
    def measure_widths(self):

        self.measuring_widths = True
        self.parent().widthsButton.setEnabled(False)
        self.numwidths = int(self.parent().subWin.numwidths.text())-1
        self.k = 0
        self.W = posData(
            np.empty(shape=(0, 0)),
            np.empty(shape=(0, 0)))  #preallocate custom widths
        #self.widths[-1] = np.empty(self.numwidths - 1, dtype='float') #preallocate measurements
        self.nspines = 2 * (self.numwidths) #- 1)
        self.parent().statusbar.showMessage(
            'Drag width segment points to make width measurements perpendicular to the length segment'
        )

        #Bisection method on Gauss-Legendre Quadrature to find equal spaced intervals
        s_i = np.linspace(0,1,self.numwidths+2)[1:-1] #only need to draw widths for inner pts
        # Crashing with two point length measurements
        t_i = np.array([root_scalar(gauss_legendre, x0 = s_i, bracket = [-1,1], method = "bisect", args = (bezier, self.Q, self.kb-1, True, s, self.l) ).root for s in s_i])
        B_i = bezier(np.array(t_i), P = self.P, k = self.kb)
        self.xp, self.yp = B_i[:,0], B_i[:,1]

        #Find normal vectors by applying pi/2 rotation matrix to tangent vector
        bdot = bezier(t_i, P = self.Q, k = self.kb - 1)
        mag = np.linalg.norm(bdot,axis = 1) #normal vector magnitude
        bnorm = np.flip(bdot/mag[:,None],axis = 1)
        bnorm[:,0] *= -1
        self.slopes = bnorm
        ellipse_group = []

        # For Side Bias Label
        font = QFont()
        font.setPointSize(40)
        font.setWeight(QFont.Weight.Bold)
        font.setPixelSize(int(self.pixmap_fit.width()/30))  # Set text size relative to screen dimensions

        for k,(pt,m) in enumerate(zip(B_i,bnorm)):
        #for k,(x,y) in enumerate(zip(self.xp[1:-1], self.yp[1:-1])):
            x1, y1 = pt[0],pt[1]
            vx, vy = m[0], m[1]
            L = self.pixmap_fit.width()
            H = self.pixmap_fit.height()
            # t2 = 0
            # t0 = np.hypot(L,H) #preallocate t0 as diagonal distance

            xi,yi = [], []
            for bound in ([0,0],[L,H]):
                for ev in ([1,0],[0,1]):
                    A = np.matrix([ [vx, ev[0]] , [vy, ev[1]] ])
                    b = np.array([bound[0] - x1, bound[1] - y1])
                    T = np.linalg.solve(A,b)[0] #only need parametric value for our vector, not bound vector

                    xint = x1 + T*vx
                    yint = y1 + T*vy
                    print( f"for line {k}, sol to Ax = B is {T}")
                    if ( (xint<=L + 1) and (xint>=0-1) and (yint<=H+1) and (yint>=0-1) ): #only add intersect if conditions met.
                        #1 pixel fudge factor required?
                        print("success")
                        xi.append(xint)
                        yi.append(yint)

            # Draw width lines (And draw starting points)

            for l, (x, y) in enumerate(zip(xi,yi)):
                index = 2 * k + l

                start = QtCore.QPointF(x1, y1)
                end = QtCore.QPointF(x, y)

                # if this is the first itertion
                if k == 0:
                    # Set distance from linear measurement
                    lineLength = np.sqrt((start.x()-end.x())**2 + (start.y()-end.y())**2)
                    t = (500)/lineLength # Ratio of desired distance from center / total length of line
                    posAB = QtCore.QPointF(((1-t)*start.x()+t*end.x()),((1-t)*start.y()+t*end.y()))
                    if l == 0:
                        A = QGraphicsTextItem(str("A"))
                        A.setFont(font)
                        A.setPos(posAB) # Set to mid-Point
                        self.scene.addItem(A)
                    elif l == 1:
                        B = QGraphicsTextItem(str("B"))
                        B.setFont(font)
                        B.setPos(posAB)
                        self.scene.addItem(B)
                Ell = MovingEllipse(self, start, end, self.slider_pos)
                ellipse_group.append(Ell)
                self.scene.interpLine = QGraphicsLineItem(
                    QtCore.QLineF(start, end))
                self.d["{}".format(index)] = self.scene.interpLine
                self.scene.addItem(self.scene.interpLine)
                self.scene.addItem(ellipse_group[-1])   # Grab last appended ellipse

        self.ellipses.append(ellipse_group) # Store width group

    # detects mouse click of main window
    def mousePressEvent(self, event):
        #http://pyqt.sourceforge.net/Docs/PyQt4/qgraphicsscenemouseevent.html
        #https://stackoverflow.com/questions/21197658/how-to-get-pixel-on-qgraphicspixmapitem-on-a-qgraphicsview-from-a-mouse-click
        data = self.mapToScene(event.pos())

        #draw piecewise lines for non-width measurements
        rules = [self.measuring_length, self.measuring_angle, self.measuring_area]

        if self.scene.testline and self._thispos and any(rules):
            start = self._thispos
            end = QtCore.QPointF(data)

            if self._lastpos and self.measuring_angle:

                a = self._lastpos - self._thispos
                b = data - self._thispos
                a = np.array([a.x(), a.y()])
                b = np.array([b.x(), b.y()])
                self.measuring_angle = False
                t = np.arccos(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
                t *= 180 / np.pi  #convert to degrees
                self.T.update(t)
                self.angleValues = np.append(self.angleValues,t)
                self.parent().statusbar.showMessage('Angle measurement complete')
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)  #change cursor
                self.parent().angleButton.setChecked(False)
                self.parent().bezier.setEnabled(True)

            self.scene.realline = QGraphicsLineItem(QtCore.QLineF(start, end))
            self.scene.addItem(self.scene.realline)

        #Collect piecewise line start/end points
        self._lastpos = self._thispos  # save old position value
        self._thispos = QtCore.QPointF(data)  # update current position

        if self.measuring_length:
            self.L.update(data.x(), data.y())  # update total length
            self.line_count += 1

        elif self.measuring_area:
            self.line_count += 1
            intersect = False
            if self.line_count > 2: #cant make polygon w/ two lines
                intersect, xi, yi, k = self.A.checkIntersect(data.x(),data.y())
                self.parent().areaButton.setEnabled(True)
            if intersect:
                self.measuring_area = False
                self.A.update(xi,yi) #update with intersect point
                self.A.x, self.A.y = self.A.x[k:], self.A.y[k:] #only use points after intersection
                A = self.A.calcArea()
                self.areaValues = np.append(self.areaValues, A) #add area values
                #draw permanent polygon
                points = [ QtCore.QPointF(x,y) for x,y in zip( self.A.x, self.A.y ) ]
                self.scene.polyItem2 = QGraphicsPolygonItem(QtGui.QPolygonF(points))
                self.scene.polyItem2.setBrush( QtGui.QBrush(QtGui.QColor(255,255,255,127)) )
                self.scene.removeItem(self.scene.polyItem) #remove mouseover polygon
                self.scene.polyItem = False #remove mouseover polygon
                self.scene.addItem(self.scene.polyItem2) #shade in polygon
                self.parent().statusbar.showMessage('Polygon area measurement completed')
                self.parent().areaButton.setChecked(False)
                self.parent().bezier.setEnabled(True) #make bezier fit available again
                QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)  #change cursor
            else:
                self.A.update(data.x(),data.y()) #update with click point

        #https://stackoverflow.com/questions/30898846/qgraphicsview-items-not-being-placed-where-they-should-be
        if self.measuring_widths:  #measure widths, snap to spines

            k = int(self.k / 2) #+ 1  #same origin for spine on either side
            x0, y0 = self.xp[k], self.yp[k]
            x1, y1 = data.x(), data.y()

            #perpindicular slopes
            vx, vy = self.slopes[k,0], self.slopes[k,1]

            A = np.matrix([[vx, -vy], [vy, vx]])
            b = np.array([x1 - x0, y1 - y0])
            t = np.linalg.solve(A,b)

            xi = x0 + t[0]*vx
            yi = y0 + t[0]*vy

            self.W.update(xi,yi)

            self.parent().statusbar.showMessage('Width measurements complete')

            self.measuring_widths = False

            self.parent().widthsButton.setEnabled(False)
        super().mousePressEvent(event)

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    #MouseWheel Zoom
    def wheelEvent(self, event):
        #https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
        #transform coordinates correctly
        #https://stackoverflow.com/questions/20942586/controlling-the-pan-to-anchor-a-point-when-zooming-into-an-image
        #https://stackoverflow.com/questions/41226194/pyqt4-pixel-information-on-rotated-image
        zoomInFactor = 1.05
        zoomOutFactor = 1 / zoomInFactor

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        oldPos = self.mapToScene(event.position().toPoint())

        #Zoom
        # https://quick-geek.github.io/answers/885796/index.html
        # y-component for mouse with two wheels
        if event.angleDelta().y() > 0:
            zoomFactor = zoomInFactor
        else:
            zoomFactor = zoomOutFactor
        self.scale(zoomFactor, zoomFactor)

        newPos = self.mapToScene(event.position().toPoint())  #Get the new position
        delta = newPos - oldPos
        self.translate(delta.x(), delta.y())  #Move scene to old position

class posData():

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def update(self, add_x, add_y):
        self.x = np.append(self.x, add_x)
        self.y = np.append(self.y, add_y)

        #below just for area calcs
        self.dx = np.diff(self.x)
        self.dy = np.diff(self.y)
        self.Tu = np.hypot(self.dx,self.dy) + np.finfo(float).eps

    def downdate(self):
        self.x = self.x[:-1]
        self.y = self.y[:-1]

        #below just for area calcs
        self.dx = np.diff(self.x)
        self.dy = np.diff(self.y)
        self.Tu = np.hypot(self.dx,self.dy) + np.finfo(float).eps

    def checkIntersect(self, xn, yn):
        vx = np.array([self.x[-1],xn])
        vy = np.array([self.y[-1],yn])
        dvx = np.diff(vx)
        dvy = np.diff(vy)
        Tv = np.hypot(dvx,dvy) + np.finfo(float).eps
        intersect = False
        xi = None
        yi = None
        count = None
        for k,(x,y,dx,dy,Tu) in enumerate(zip(self.x[:-1], self.y[:-1], self.dx, self.dy, self.Tu)):

            A = np.matrix([[dx/Tu, -dvx[0]/Tv[0]],[dy/Tu, -dvy[0]/Tv[0]]], dtype=float)
            b = np.array( [vx[0] - x, vy[0] - y] )
            try:
                t = np.linalg.solve(A, b)
            except np.linalg.LinAlgError as err:
                if 'Singular matrix' in str(err):
                    t = np.array([0,0])
            if (t[0] > 0) and (t[0] < Tu) and (t[1] > 0) and (t[1] < Tv):
                intersect = True
                xi = vx[0] + t[1]*dvx/Tv
                yi = vy[0] + t[1]*dvy/Tv
                count = k
        return intersect, xi, yi, count

    def calcArea(self):
        A =  0.5*np.abs( np.dot(self.x[:-1],self.y[1:]) + self.x[-1]*self.y[0]
                        - np.dot(self.y[:-1],self.x[1:]) - self.y[-1]*self.x[0] )
        self.A = A
        return A

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(__file__)

    return os.path.join(base_path, relative_path)

# Class for width measurement eclipses
# A grabable Object that allows the user to change width measurements at any moment
# Ellipse is bound to parent line
# Input: Line P1 (QPointF), Line P2 (QPointF)
class MovingEllipse(QGraphicsPixmapItem):
    def __init__(self, parent,lp1, lp2, scale):
        # LP2 is always border point (PyQt6.QtCore.QPointF(1030.9353133069922, 0.0))
        super(MovingEllipse,self).__init__()

        scaledSize = int(parent.scene.height()/80) + (scale*10)
        Image = QPixmap(resource_path("crosshair.png")).scaled(scaledSize,scaledSize)
        self.Pixmap = QPixmap(Image.size())
        self.Pixmap.fill(parent.picked_color)
        self.Pixmap.setMask(Image.createMaskFromColor(Qt.GlobalColor.transparent))

        self.setPixmap(self.Pixmap)
        self.setOffset(QtCore.QPointF(-scaledSize/2,-scaledSize/2)) # Set offset to center of image
        self.midPoint = (lp1 + lp2)/2    # QPointF
        self.cetnerLinePoint = lp1  # Used in

        self.p1 = lp1
        self.p2 = lp2

        self.parent = parent            # Used for updating widths measurement
        # Find slope of line (y2-y1)/(x2-x1)
        self.m = (self.p2.y()-self.p1.y())/(self.p2.x()-self.p1.x())
        self.assignPoints(self.m,lp1,lp2)
        # Find X intercept
        self.y0 = (lp1.y())-(self.m*lp1.x())  # y1-(m*x1) = b
        self.x0 = (self.y0*-1)/self.m   # -y0/slope

        # Set distance from linear measurement
        d = np.sqrt((lp1.x()-lp2.x())**2 + (lp1.y()-lp2.y())**2)
        t = (scaledSize*3)/d # Ratio of desired distance from center / total length of line

        self.setPos(QtCore.QPointF(((1-t)*lp1.x()+t*lp2.x()),((1-t)*lp1.y()+t*lp2.y())))
        self.setAcceptHoverEvents(True)
        self.drag = False

    def update_scale(self, scale):
        scaledSize = int(self.parent.scene.height()/60) + (scale*10)
        Image = QPixmap(resource_path("crosshair.png")).scaled(scaledSize,scaledSize)
        self.Pixmap = QPixmap(Image.size())
        self.Pixmap.fill(self.parent.picked_color)
        self.Pixmap.setMask(Image.createMaskFromColor(Qt.GlobalColor.transparent))

        self.setPixmap(self.Pixmap)
        self.setOffset(QtCore.QPointF(-scaledSize/2,-scaledSize/2)) # Set offset to center of image

    def assignPoints(self, slope, lp1, lp2):
        # Set Points depending on their path slope 
        if slope > -0.5 and slope < 0.5:    # set points depending on X
            if lp1.x() < lp2.x():
                self.p1 = lp1               # P1 should always hold the smaller comparetor
                self.p2 = lp2
            else:
                self.p1 = lp2
                self.p2 = lp1
        else:                               # set points depending on Y
            if lp1.y() < lp2.y():
                self.p1 = lp1
                self.p2 = lp2
            else:
                self.p1 = lp2
                self.p2 = lp1

    # Mouse Hover
    def hoverEnterEvent(self, event):
        #print("Hover")
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.OpenHandCursor)

    # Mouse Stops Hovering
    def hoverLeaveEvent(self, event):
        QApplication.restoreOverrideCursor()

    def mousePressEvent(self, event):
        self.drag = True
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.BlankCursor)

    def mouseMoveEvent(self, event):
        if self.drag:
            orig_curs_pos = event.lastScenePos()
            updated_curs_pos = event.scenePos()
            orig_pos = self.scenePos()

            # Update position of Ellipse to match mouse

            ell_y = updated_curs_pos.y() - orig_curs_pos.y() + orig_pos.y()
            ell_x = updated_curs_pos.x() - orig_curs_pos.x() + orig_pos.x()

            # Use X of mouse when line is horizontal, and Y when verticle
            if self.m > -0.5 and self.m < 0.5:
                # y = mx + b
                if ell_x < self.p1.x():
                    ell_x = self.p1.x()
                elif ell_x > self.p2.x():
                    ell_x = self.p2.x()
                ell_y = ell_x*self.m + self.y0
                
            else:
                # x = y/m - r
                # Stay within boundry
                if ell_y < self.p1.y():
                    ell_y = self.p1.y()
                elif ell_y > self.p2.y():
                    ell_y = self.p2.y()

                ell_x = ell_y/self.m + self.x0
                
            self.setPos(QtCore.QPointF(ell_x, ell_y))

    def mouseReleaseEvent(self, event):
        self.drag = False
        #QCursor.setPos(self.scenePos().toPoint())  # Requires special permissions :/
        QApplication.restoreOverrideCursor()

class angleData():  #actually need separate class from posdata? probably not

    def __init__(self, t):
        self.t = t

    def update(self, add_t):
        self.t = np.append(self.t, add_t)

    def downdate(self):
        self.t = self.t[:-1]


# Program crash hook for error logging
def except_hook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    dialog = QMessageBox()
    dialog.setIcon(QMessageBox.Icon.Critical)
    dialog.setWindowTitle("Error")
    dialog.setText("Error: Crash caught, save details to file.")
    dialog.setDetailedText(tb)
    dialog.setStandardButtons(QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
    ret = dialog.exec()   # Show dialog box
    if ret == QMessageBox.StandardButton.Save:
        path = QFileDialog().getExistingDirectory(dialog,'Select a directory')
        if(path):
            path += '/' + str(date.today()) + "_Morphometrix_Crashlog" + ".txt"
            print("saving: ", path)
            with open(path, 'w') as file:
                file.write("System: " + platform.system() + '\n')
                file.write("OS: " + os.name + '\n')
                file.write("Python Version: " + platform.python_version() + '\n')
                file.write("Python Implementation: " + platform.python_implementation() + '\n')
                file.write("Release: " + platform.release() + '\n')
                file.write("Version: " + platform.version() + '\n')
                file.write("Machine: " + platform.machine() + '\n')
                file.write("Processor: " + platform.processor() + '\n' + '\n')
                file.write(tb)

    QApplication.quit() # Quit application

def main():
    sys.excepthook = except_hook
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    app.exec()
    sys.exit()


if __name__ == "__main__":
    main()
