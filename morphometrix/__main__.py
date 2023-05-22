#usr/bin/env python
import os
import sys
import csv
from itertools import cycle, islice
import numpy as np
from scipy.linalg import pascal
from scipy.sparse import diags
from scipy.optimize import root_scalar

from PyQt6 import QtGui, QtCore
from PyQt6.QtWidgets import QColorDialog ,QGraphicsTextItem ,QComboBox, QMainWindow, QApplication, QGraphicsView, QGraphicsScene, QWidget, QToolBar, QPushButton, QLabel, QLineEdit, QPlainTextEdit, QGridLayout, QFileDialog, QGraphicsLineItem, QGraphicsPixmapItem,QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsItem, QMessageBox, QInputDialog, QDockWidget, QSizePolicy, QRadioButton
from PyQt6.QtGui import QShortcut, QFont, QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt

#To-do list (descending priority)
#   -combine UI into one window (done)
#   -scale bar
#   -show values as measurements being made
#   -mouseover xy position
#   -preferences change in options
#   -tune bezier curve tension parameter (rational bezier) with scroll wheel
#   -photo saved not working correctly?
#   -angle lines different color?
#   -arrows w/ heads for angle measurement
#   -arc between angle lines
#   -object outline: fusiform

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


class Manual(QWidget):
    def __init__(self, parent=None):
        super(Manual, self).__init__()
        self.manual = QWebEngineView()
        webpage = QtCore.QUrl('https://wingtorres.github.io/morphometrix/')
        self.manual.setUrl(webpage)
        self.grid = QGridLayout()
        self.grid.addWidget(self.manual,1,0)
        self.setLayout(self.grid)

class Window(QWidget):

    def __init__(self, iw):
        #init methods runs every time, use for core app stuff)
        super(Window, self).__init__()
        self.iw = iw    # Reference for color picker
        #self.setWindowTitle("MorphoMetriX")
        #self.setGeometry(50, 50, 100, 200)  #x,y,width,height
        #self.setStyleSheet("background-color: rgb(0,0,0)") #change color
        #self.setStyleSheet("font-color: rgb(0,0,0)") #change color

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

        self.label_not = QLabel("Notes:")
        self.notes = QPlainTextEdit()

        self.label_color = QLabel("Crosshair Color: ")
        self.button_color = QPushButton()
        self.button_color.setStyleSheet("background-color: red")
        self.button_color.clicked.connect(self.color_changed)

        # self.manual = QWebEngineView()
        #fpath = os.path.abspath('/Users/WalterTorres/Dropbox/KC_WT/MorphoMetrix/morphometrix/README.html')
        #webpage = QtCore.QUrl.fromLocalFile(fpath)
        # webpage = QtCore.QUrl('https://wingtorres.github.io/morphometrix/')
        # self.manual.setUrl(webpage)

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
        self.grid.addWidget(self.label_not, 7, 0)
        self.grid.addWidget(self.notes, 7, 1)
        self.grid.addWidget(self.label_color,8,0)
        self.grid.addWidget(self.button_color,8,1)
        # self.grid.addWidget(self.manual, 8,0,1,4)
        self.grid.addWidget(self.exit, 9, 3)
        self.setLayout(self.grid)

    def color_changed(self):
        color = QColorDialog().getColor()   # Returns QColor
        self.button_color.setStyleSheet("background-color: "+color.name())
        self.iw.picked_color = color


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

		#qr = self.frameGeometry()
        #cp = self.screen().availableGeometry().center()
        #qr.moveCenter(cp)
        #self.move(qr.topLeft())

        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowState.WindowMinimized
                            | QtCore.Qt.WindowState.WindowActive)
        self.activateWindow()


        self.iw = imwin()           # Image window
        self.subWin = Window(self.iw)
        self.Manual = Manual()
        self.setCentralWidget(self.iw)

        #Stacked dock widgets
        docked1 = QDockWidget("", self)
        docked2 = QDockWidget("", self)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, docked1)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, docked2)
        docked1.setWidget(self.subWin)
        docked2.setWidget(self.Manual)
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
        #self.widthsButton.clicked.connect(self.iw.measure_widths)
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
	#self.bezier.toggled.connect(self.onClicked)

        self.piecewise = QRadioButton("Piecewise", self)

        self.statusbar = self.statusBar()
        self.statusbar.showMessage('Select new image to begin')

        self.tb = QToolBar('Toolbar')
        #self.addToolBar(QtCore.Qt.RightToolBarArea,self.tb)
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
        #self.tb.setOrientation(QtCore.Qt.Vertical)

    def file_open(self):

        self.iw.scene.clear()
        self.image_name = QFileDialog.getOpenFileName(self, 'Open File')
        self.iw.pixmap = QtGui.QPixmap(self.image_name[0])
        self.iw.pixmap_fit = self.iw.pixmap.scaled(
            self.iw.pixmap.width(),
            self.iw.pixmap.height(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            transformMode=QtCore.Qt.TransformationMode.SmoothTransformation)
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
        #self.iw.measurements = [[]]
        self.iw.ellipses = []
        self.iw.widths = []
        self.iw.lengths = [[]]
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

    def undo(self):

        if self.iw.measuring_length:
            self.iw._thispos = self.iw._lastpos
            self.iw.L.downdate()  #remove data
            self.iw.line_count += -1
            self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
            self.iw.scene.realline = False

        if self.iw.measuring_area:
            self.iw._thispos = self.iw._lastpos
            self.iw.A.downdate()  #remove data
            self.iw.line_count += -1
            self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
            self.iw.scene.realline = False

        # Removed functionality for new dragable system (Elliott)
        #if self.iw.measuring_widths:
        #    self.iw.W.downdate()  #remove data
        #    self.iw.scene.removeItem(self.iw.scene.ellipseItem)  #remove graphic
        #    self.iw.scene.ellipseItem = False           # Why does this get set to false!?
        #    self.iw.d[str(self.iw.k)].setPen(
        #        QtGui.QPen(QtGui.QColor('black')))  #un-highlight next spine
        #    self.iw.k += -1  #reduce count

        if self.iw.measuring_angle:
            self.iw.T.downdate()  #remove data
            self.iw._thispos = self.iw_lastpos
            self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
            self.iw.scene.realline = False

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
            #measurements = [ f * fac * self.pixeldim * self.altitude / self.focal for f in self.iw.measurements]7
            #lengths = [ f * fac * self.pixeldim * self.altitude / self.focal for f in self.iw.lengths]
            #print(self.iw.widths)
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
            with open(name + '.csv', 'w') as csvfile:
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
        #self.widths = []
        self.ellipses = []
        self.d = {}  #dictionary for line items
        #self.k = 0 #initialize counter so lines turn yellow
        self.L = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
        self.W = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
        self.scene.realline = None
        self.scene.testline = None
        self.setMouseTracking(True)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        #self.setRenderHints(QtGui.QPainter.Antialiasing
        #                    | QtGui.QPainter.SmoothPixmapTransform)
        #self.setRenderHint(QtGui.QPainter.Antialiasing, True)
        #self.setRenderHint(QtGui.QPainter.HighQualityAntialiasing, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        #self.setInteractive(True)

    # Calculates width between corresponding ellipses
    # Calculates distance in pixels and appends widths[] list
    # Input: None
    # Output: None
    def calculate_widths(self,bias):
        for x in range(0,len(self.ellipses)):   # iterate over every group of ellipses
            calculated_widths = []
            for y in range(0,len(self.ellipses[x]),2):  # Iterate over every ellipse in group (might be causing incorrect amount at export issue)
                print("Bias: ", bias)
                if bias == 'None':
                    width = np.sqrt(
                            (self.ellipses[x][y].scenePos().x() - self.ellipses[x][y+1].scenePos().x())**2 +
                            (self.ellipses[x][y].scenePos().y() - self.ellipses[x][y+1].scenePos().y())**2)  #calculate width of entire line
                elif bias == 'Side A':
                    # (A point - centerlinePoint) * 2
                    print("P1x: ",self.ellipses[x][y].scenePos().x())
                    print("P2x: ",self.ellipses[x][y].cetnerLinePoint.x())
                    width = np.sqrt(
                            ((self.ellipses[x][y].scenePos().x() - self.ellipses[x][y].cetnerLinePoint.x())*2)**2 +
                            ((self.ellipses[x][y].scenePos().y() - self.ellipses[x][y].cetnerLinePoint.y())*2)**2)  #calculate width of entire line
                else:   # Bias B
                    # (B point - centerlinePoint) * 2
                    print("P1x: ",self.ellipses[x][y+1].scenePos().x())
                    print("P2x: ",self.ellipses[x][y+1].cetnerLinePoint.x())
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
        #else:
        #    QApplication.setOverrideCursor(QtCore.Qt.CursorShape.ArrowCursor)  #change cursor

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

            if (self.parent().bezier.isChecked()) and (len(np.vstack((self.L.x, self.L.y)).T) > 2):

                def bezier_rational(points, nt):
                    """Rational Bezier Curve fit"""
                    # # https://gist.github.com/Alquimista/1274149
                    # # https://pages.mtu.edu/~shene/COURSES/cs3621/NOTES/spline/Bezier/bezier-der.html
                    # n = len(points)
                    # xp = np.array([p[0] for p in points])
                    # yp = np.array([p[1] for p in points])
                    # t = np.linspace(0.0, 1.0, nt)

                    # #Bezier curve
                    # B = np.array([ bernstein(i,n-1,t) for i in range(0,n) ])
                    # xb = np.dot(xp, B)[::-1]
                    # yb = np.dot(yp, B)[::-1]

                    # #Analytic gradient for bezier curve
                    # Qx = n*np.diff(xp)
                    # Qy = n*np.diff(yp)
                    # Bq = np.array([ bernstein(i,n-2,t) for i in range(0,n-1) ])
                    # dxb = np.dot(Qx, Bq)[::-1]
                    # dyb = np.dot(Qy, Bq)[::-1]

                    # m = np.vstack((dxb,dyb))
                    # m *= (1/np.linalg.norm(m, axis=0))
                    # return xb, yb, m

                nt = 100 #max(1000, self.numwidths * 50)  #num of interpolating points
                t = np.linspace(0.0, 1.0, nt)
                self.P = np.vstack((self.L.x, self.L.y)).T #control points
                self.kb = len(self.P) - 1 #order of bezier curve # of control points (n) - 1

                # self.xs, self.ys, self.m = bezier_rational(points, nt)
                B = bezier(t, self.P, k = self.kb) #evaluate bezier curve along t
                self.Q = self.kb*np.diff(self.P, axis = 0)
                self.l = gauss_legendre(b = 1, f = bezier, P = self.Q, k = self.kb - 1, arc = True) #compute total arc length.
                self.lengths[-1] = self.l

                self.xs, self.ys = B[:,0], B[:,1]
                pts = np.array(list(map(self.qpt2pt, self.xs, self.ys)))
                #x, y = pts[:, 0], pts[:, 1]
                #self.l = np.cumsum(np.hypot(np.gradient(x), np.gradient(y))) #integrate for length

                #draw cubic line to interpolated points
                for i in range(1, nt - 1):
                    P0 = QtCore.QPointF( self.xs[i-1], self.ys[i-1] )#.toPoint()
                    P1 = QtCore.QPointF( self.xs[i  ], self.ys[i  ] )#.toPoint()
                    P2 = QtCore.QPointF( self.xs[i+1], self.ys[i+1] )#.toPoint()
                    start = self.mapFromScene(self.mapToScene(P0.toPoint()))
                    mid = self.mapFromScene(self.mapToScene(P1.toPoint()))
                    end = self.mapFromScene(self.mapToScene(P2.toPoint()))
                    path = QtGui.QPainterPath(P0)
                    path.cubicTo(P0, P1, P2)
                    self.scene.addPath(path)

            if (not self.parent().bezier.isChecked()) or (len(np.vstack((self.L.x, self.L.y)).T) <= 2):
                """Simple linear points if piecewise mode (or only two points used?)"""
                pts = np.array(list(map(self.qpt2pt, self.L.x, self.L.y)))
                x, y = pts[:, 0], pts[:, 1]
                slope = (y[-1] - y[0]) / (x[-1] - x[0])
                theta = np.arctan(slope)
                distance = np.hypot( x[-1] - x[0], y[-1] - y[0] )
                r = np.linspace(0, distance, 1000)

                self.xs, self.ys = x[0] + r*np.cos(theta), y[0] + r*np.sin(theta)
                self.m = np.vstack(( slope*(r*0 + 1), -slope*(r*0 + 1) ))
                #self.m = np.vstack(( (y[-1] - y[0])*(r*0 + 1), (x[-1] - x[0])*(r*0 + 1) ))
                self.m = np.vstack((  (x[-1] - x[0])*(r*0 + 1), (y[-1] - y[0])*(r*0 + 1) ))
                self.l = np.cumsum(np.hypot(np.diff(self.xs), np.diff(self.ys)))  #integrate for length
                self.lengths[-1] = self.l[-1]

            self.lengths.extend([np.nan])
            #self.widths.append([])

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
        self.parent().widthsButton.setChecked(True)
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

        # #get pts for width drawing
        # bins = np.linspace(0, self.l[-1], self.numwidths + 1)
        # inds = np.digitize(self.l, bins)
        # __, self.inddec = np.unique(inds, return_index = True)

        # pts = np.array(list(map(qpt2pt, self.xs, self.ys)))
        # x, y = pts[:, 0], pts[:, 1]
        # self.xp, self.yp = x[self.inddec], y[self.inddec]
        # self.slopes = self.m[:,self.inddec]
        # #Identify width spine points

        #Bisection method on Gauss-Legendre Quadrature to find equal spaced intervals
        s_i = np.linspace(0,1,self.numwidths+2)[1:-1] #only need to draw widths for inner pts
        t_i = np.array([root_scalar(gauss_legendre, x0 = s_i, bracket = [-1,1], method = "bisect",
                            args = (bezier, self.Q, self.kb-1, True, s, self.l) ).root for s in s_i])
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
        font.setWeight(600)
        font.setPixelSize(int(self.pixmap_fit.width()/30))  # Set text size relative to screen dimensions

        for k,(pt,m) in enumerate(zip(B_i,bnorm)):
        #for k,(x,y) in enumerate(zip(self.xp[1:-1], self.yp[1:-1])):
            x1, y1 = pt[0],pt[1]
            vx, vy = m[0], m[1]
            L = self.pixmap_fit.width()
            H = self.pixmap_fit.height()
            # t2 = 0
            # t0 = np.hypot(L,H) #preallocate t0 as diagonal distance

            # #check intersection w/ bounding rectangle
            # for offset in ([0,0],[L,H]):
            #     for ev in ([1,0],[0,1]):
            #         A = np.matrix([ [vx, ev[0]] , [vy, ev[1]] ])
            #         b = np.array([offset[0] - x1, offset[1] - y1])
            #         T = np.linalg.solve(A,b)[0]
            #         t0 = min(T, t0, key=abs) #find nearest intersection to bounds

            xi,yi = [], []
            for bound in ([0,0],[L,H]):
                for ev in ([1,0],[0,1]):
                    A = np.matrix([ [vx, ev[0]] , [vy, ev[1]] ])
                    b = np.array([bound[0] - x1, bound[1] - y1])
                    T = np.linalg.solve(A,b)[0] #only need parametric value for our vector, not bound vector
                    #t0 = min(T, t0, key=abs) #find nearest intersection to bounds

                    xint = x1 + T*vx
                    yint = y1 + T*vy
                    print( f"for line {k}, sol to Ax = B is {T}")
                    if ( (xint<=L + 1) and (xint>=0-1) and (yint<=H+1) and (yint>=0-1) ): #only add intersect if conditions met.
                        #1 pixel fudge factor required?
                        print("success")
                        xi.append(xint)
                        yi.append(yint)
            #assert False
            # #Find 2nd furthest intersection within bounds
            # bounds = np.array( [(L - x1)/vx, (H - y1)/vy, -x1/vx, -y1/vy] )
            # t2 = max(-t0, np.sign(-t0)* np.partition(bounds,-2)[-2], key=abs)

            # x0 = x1 + t0*vx
            # y0 = y1 + t0*vy
            # x2 = x1 + t2*vx
            # y2 = y1 + t2*vy

            # for l, (x, y) in enumerate(zip([x0, x2], [y0, y2])):

            # Draw width lines (And draw starting points)

            for l, (x, y) in enumerate(zip(xi,yi)):
                index = 2 * k + l

                start = QtCore.QPointF(x1, y1)
                end = QtCore.QPointF(x, y)

                # if this is the first itertion
                if k == 0 and l == 0:
                    A = QGraphicsTextItem(str("A"))
                    A.setFont(font)
                    A.setPos((start+end)/2) # Set to mid-Point
                    self.scene.addItem(A)
                if k == 0 and l == 1:
                    B = QGraphicsTextItem(str("B"))
                    B.setFont(font)
                    B.setPos((start+end)/2)
                    self.scene.addItem(B)

                Ell = MovingEllipse(self, start, end)
                ellipse_group.append(Ell)
                self.scene.interpLine = QGraphicsLineItem(
                    QtCore.QLineF(start, end))
                self.d["{}".format(index)] = self.scene.interpLine
                self.scene.addItem(self.scene.interpLine)
                self.scene.addItem(ellipse_group[-1])   # Grab last appended ellipse



        self.ellipses.append(ellipse_group) # Store width group

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
            # vx = self.slopes[:,k][1]
            # vy = -self.slopes[:,k][0]
            vx, vy = self.slopes[k,0], self.slopes[k,1]

            A = np.matrix([[vx, -vy], [vy, vx]])
            b = np.array([x1 - x0, y1 - y0])
            t = np.linalg.solve(A,b)

            xi = x0 + t[0]*vx
            yi = y0 + t[0]*vy

            self.W.update(xi,yi)
            #p = QtCore.QPointF(xi, yi)

            #s = 10  #dot size
            #self.scene.ellipseItem = QGraphicsEllipseItem(0, 0, s, s)   # Define ellipse
            #self.scene.ellipseItem.setPos(p.x() - s / 2, p.y() - s / 2) # Draw ellipse to scene
            #qb = QtGui.QBrush()
            #qb.setColor(QtGui.QColor('red'))
            #self.scene.ellipseItem.setBrush(qb)
            #self.scene.ellipseItem.setFlag(
            #    QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations,
            #    True)  #size stays small, but doesnt translate if false
            #self.scene.addItem(self.scene.ellipseItem)
            #self.k += 1

            #Highlight width lines
            #if self.k < self.nspines:
            #    self.d[str(self.k)].setPen(QtGui.QPen(QtGui.QColor('yellow'))) #Highlight next spine

            # When all width measurements are inputted
            #if self.k == self.nspines:
            #    self.parent().statusbar.showMessage('Width measurements complete')
            #    self.measuring_widths = False
            #    self.parent().widthsButton.setEnabled(False)
            #    self.parent().widthsButton.setChecked(False)
            #    self.parent().bezier.setEnabled(True)
            #    width = np.sqrt(
            #        (self.W.x[1::2] - self.W.x[0::2])**2 +
            #        (self.W.y[1::2] - self.W.y[0::2])**2)  #calculate width of entire line
            #    self.widths[-1] = width    # Output is in Pixels
        self.parent().statusbar.showMessage('Width measurements complete')
        self.measuring_widths = False
        self.parent().widthsButton.setEnabled(False)
        self.parent().widthsButton.setChecked(False)
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
    def __init__(self, parent,lp1, lp2):
        # LP2 IS ALWAYS BORDER POINT (PyQt6.QtCore.QPointF(1030.9353133069922, 0.0))
        super(MovingEllipse,self).__init__()

        scaledSize = int(parent.scene.height()/30)
        Image = QPixmap(resource_path("crosshair.png")).scaled(scaledSize,scaledSize)
        self.Pixmap = QPixmap(Image.size())
        self.Pixmap.fill(parent.picked_color)
        self.Pixmap.setMask(Image.createMaskFromColor(Qt.GlobalColor.transparent))

        self.setPixmap(self.Pixmap)
        self.setOffset(QtCore.QPointF(-scaledSize/2,-scaledSize/2)) # Set offset to center of image
        #self.setRect(-10,-10,20,20)
        self.midPoint = (lp1 + lp2)/2    # QPointF
        self.cetnerLinePoint = lp1  # Used in

        self.p1 = None
        self.p2 = None
        self.parent = parent            # to update widths measurement
        self.pointAssignment(lp1,lp2)
        # Find slope of line (y2-y1)/(x2-x1)
        self.m = (self.p2.y()-self.p1.y())/(self.p2.x()-self.p1.x())
        # Find X intercept
        self.y0 = (lp1.y())-(self.m*lp1.x())  # y1-(m*x1) = b
        self.x0 = (self.y0*-1)/self.m   # -y0/slope
        #print("midpoint: ", self.midPoint)
        #print("Y0: ", self.y0)
        #print("m: ", self.m)

        # Set distance from linear measurement
        d = np.sqrt((lp1.x()-lp2.x())**2 + (lp1.y()-lp2.y())**2)
        t = (scaledSize*3)/d # Ratio of desired distance from center / total length of line


        self.setPos(QtCore.QPointF(((1-t)*lp1.x()+t*lp2.x()),((1-t)*lp1.y()+t*lp2.y())))
        self.setAcceptHoverEvents(True)
        self.drag = False

    # set points correctly for slope calculations
    def pointAssignment(self,lp1,lp2):
        if lp1.y() > lp2.y():
            self.p1 = lp2
            self.p2 = lp1
        else:
            self.p1 = lp1
            self.p2 = lp2

    # Mouse Hover
    def hoverEnterEvent(self, event):
        print("Hover")
        QApplication.setOverrideCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        #super(MovingEllipse, self).hoverEnterEvent(event)
        #return super(MovingEllipse, self).hoverEnterEvent(event)

    # Mouse Stops Hovering
    def hoverLeaveEvent(self, event):
        print("No Hover")
        QApplication.restoreOverrideCursor()
        #super(MovingEllipse, self).hoverLeaveEvent(event)
        #return super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        print("Press")
        self.drag = True
        #return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        #print("Mouse move")
        if self.drag:
            #super().mouseMoveEvent(event)
            orig_curs_pos = event.lastScenePos()
            updated_curs_pos = event.scenePos()
            orig_pos = self.scenePos()

            # Update Y position of Ellipse to match mouse
            updated_curs_y = updated_curs_pos.y() - orig_curs_pos.y() + orig_pos.y()

            # Match X position of Ellipse to slope of line (m = (y1-y0)/(x1-x0))
            # y/m - r = x
            # Issue when line starting position goes below 0
            updated_curs_x = updated_curs_y/self.m + self.x0

            self.setPos(QtCore.QPointF(updated_curs_x, updated_curs_y))

    def mouseReleaseEvent(self, event):
        #super().mouseReleaseEvent(event)
        self.drag = False
        print("release")
        #print(self.pos())

class angleData():  #actually need separate class from posdata? probably not

    def __init__(self, t):
        self.t = t

    def update(self, add_t):
        self.t = np.append(self.t, add_t)

    def downdate(self):
        self.t = self.t[:-1]

def main():
    app = QApplication(sys.argv)
    #GUI = Window()
    main = MainWindow()
    main.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
