#!/usr/bin/env python
import os
import sys
import csv
import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsView, QGraphicsScene, QWidget, QPushButton, QCheckBox, QStatusBar, QLabel, QLineEdit, QPlainTextEdit, QTextEdit, QGridLayout, QFileDialog, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsPolygonItem, QGraphicsItem, QMessageBox, QInputDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from scipy.special import comb

#To-do list (descending priority)
#   -photo saved wonky?
#   -mouseover xy position?
#   -preferences change in options?
#   -tune bezier curve tension parameter on length with scroll wheel (save for patch)
#   -combine into one window (save for patch)
#   -angle lines different color (save for patch)
#   -widths/lengths being incorrectly exported when multiple measurements? (?)
#   -whale outline (fusiform), concentric whale (possible update in future)
#   -arrows w/ heads for angle measurement

def main(args=None):

    #references:
    #https://stackoverflow.com/questions/26901540/arc-in-qgraphicsscene/26903599#26903599
    #https://stackoverflow.com/questions/27109629/how-can-i-resize-the-main-window-depending-on-screen-resolution-using-pyqt
    class Second(QMainWindow):
        def __init__(self, parent=None):
            super(Second, self).__init__(parent)

            self.iw = imwin()
            self.setCentralWidget(self.iw)
            self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized
                                | QtCore.Qt.WindowActive)
            self.activateWindow()

            self.export = QPushButton("Export Measurements", self)
            self.export.clicked.connect(self.export_meas)

            self.importImage = QPushButton("New Image", self)
            self.importImage.clicked.connect(self.file_open)

            self.lengthbutton = QPushButton(
                "Measure Total Length", self)  #Add options upon file_open instead?
            self.lengthbutton.clicked.connect(self.measure_length)

            self.widthsbutton = QPushButton("Measure Widths", self)
            self.widthsbutton.clicked.connect(self.iw.measure_widths)

            self.custombutton = QPushButton("Custom Length", self)
            self.custombutton.clicked.connect(self.measure_custom)
            self.lengthNames = []

            self.areabutton = QPushButton("Custom Area", self)
            self.areabutton.clicked.connect(self.measure_area)
            self.areaNames = []

            self.anglebutton = QPushButton("Measure Angle", self)
            self.anglebutton.clicked.connect(self.measure_angle)
            self.angleNames = []

            self.undobutton = QPushButton("Undo", self)
            self.undobutton.clicked.connect(self.undo)

            self.bezier = QCheckBox("Bezier fit?", self)
            self.bezier.setChecked(True)
            #self.bezier.stateChanged.connect(lambda: self.bezier_fit(self.bezier))

            self.statusBar = QStatusBar()
            self.setStatusBar(self.statusBar)
            self.statusBar.showMessage('Select new image to begin')

            self.tb = self.addToolBar("Toolbar")
            self.tb.addWidget(self.importImage)
            self.tb.addWidget(self.export)
            self.tb.addWidget(self.lengthbutton)
            self.tb.addWidget(self.widthsbutton)
            self.tb.addWidget(self.areabutton)
            self.tb.addWidget(self.anglebutton)
            self.tb.addWidget(self.custombutton)
            self.tb.addWidget(self.undobutton)
            self.tb.addWidget(self.bezier)

        def file_open(self):
            self.iw.scene.clear()
            self.image_name = QFileDialog.getOpenFileName(self, 'Open File')
            self.iw.pixmap = QtGui.QPixmap(self.image_name[0])
            self.iw.pixmap_fit = self.iw.pixmap.scaled(
                self.iw.pixmap.width(),
                self.iw.pixmap.height(),
                QtCore.Qt.KeepAspectRatio,
                transformMode=QtCore.Qt.SmoothTransformation)
            self.iw.scene.addPixmap(self.iw.pixmap_fit)  #add image
            self.iw.setScene(self.iw.scene)

            #Adjust window size automatically?
            self.setGeometry(
                QtCore.QRect(QtCore.QPoint(0, 0),
                            QtCore.QSize(1000, 2000)))  #change main window size
            self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
            self.iw.scene.update()
            self.statusBar.showMessage(
                'Select a measurement to make from the toolbar')

            #Initialize for new image
            self.iw.numwidths = int(
                self.parent()
                .numwidths.text())  #fetch # of length segments upon file open
            self.lengthNames = []
            self.iw.widthNames = [
                '{0:2.2f}% Width'.format(100 * f / self.iw.numwidths)
                for f in np.arange(1, self.iw.numwidths)
            ]
            #number of possible measurements per segment (length + #widths)
            self.iw.nm = len(self.iw.widthNames)  
            self.iw.measurements = np.empty((0, self.iw.nm + 1), int) * np.nan
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
            self.iw.L = posData(
                np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #lengths
            self.iw.A = posData(
                np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #area
            self.iw.W = posData(
                np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #widths
            self.iw.T = angleData(np.empty(shape=(0, 0)))  #widths
            self.iw.scene.realline = None
            self.iw.scene.testline = None
            self.iw.scene.ellipseItem = None
            self.iw.scene.polyItem = None
            self.iw.image_name = None

        def measure_length(self):
            self.iw.line_count = 0
            self.iw.measuring_length = True
            self.lengthNames.append("Total Length")
            self.iw._lastpos = None
            self.iw._thispos = None
            self.statusBar.showMessage(
                'Click initial point for length measurement')
             
        def measure_angle(self):
            self.iw.measuring_angle = True
            self.iw._lastpos = None
            self.iw._thispos = None
            self.statusBar.showMessage('Click initial point for angle measurement')

            self.lea = QLineEdit(self)
            self.lea.move(130, 22)
            self.show()

            text, ok = QInputDialog.getText(self, 'Input Dialog', 'Angle name')
            if ok:
                self.lea.setText(str(text))
                self.angleNames.append(self.lea.text())

        def measure_custom(self):
            self.iw.line_count = 0
            self.iw.measuring_custom = True
            self.iw.measuring_length = True
            self.iw._lastpos = None
            self.iw._thispos = None
            self.iw.L = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))
            self.statusBar.showMessage(
                'Click initial point for length measurement')

            self.lel = QLineEdit(self)
            self.lel.move(130, 22)
            self.show()

            text, ok = QInputDialog.getText(self, 'Input Dialog', 'Segment name')
            if ok:
                self.lel.setText(str(text))
                self.lengthNames.append(self.lel.text())

        def measure_area(self):
            self.iw.line_count = 0
            self.iw.measuring_area = True
            self.bezier.setChecked(False) #no bezier fit for area (yet)
            self.iw._lastpos = None
            self.iw._thispos = None
            self.iw.A = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))  #preallocate custom length
            self.statusBar.showMessage(
                'Click initial point for area measurement')

            self.lel = QLineEdit(self)
            self.lel.move(130, 22)
            self.show()

            text, ok = QInputDialog.getText(self, 'Input Dialog', 'Area name')
            if ok:
                self.lel.setText(str(text))
                self.areaNames.append(self.lel.text())

        def undo(self):

            if self.iw.measuring_length:
                self.iw._thispos = self.iw._lastpos
                self.iw.L.downdate()  #remove data
                self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
                self.iw.scene.realline = False

            if self.iw.measuring_area:
                self.iw._thispos = self.iw._lastpos
                self.iw.A.downdate()  #remove data
                self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic
                self.iw.scene.realline = False                

            if self.iw.measuring_widths:
                self.iw.W.downdate()  #remove data
                self.iw.scene.removeItem(self.iw.scene.ellipseItem)  #remove graphic
                self.iw.scene.ellipseItem = False
                self.iw.d[str(self.iw.k)].setPen(
                    QtGui.QPen(QtGui.QColor('black')))  #un-highlight next spine
                self.iw.k += -1  #reduce count

            if self.iw.measuring_angle:
                self.iw.T.downdate()  #remove data
                self.iw._thispos = self.iw_lastpos
                self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic

        def export_meas(self):
            fac = max(self.iw.pixmap.width(), self.iw.pixmap.height()) / max(
                self.iw.pixmap_fit.width(),
                self.iw.pixmap_fit.height())  #scale pixel -> m by scaled image
            name = QFileDialog.getSaveFileName(
                self, 'Save File', self.image_name[0].split('.', 1)[0])[0]
            self.pixeldim = float(self.parent().pixeldim.text())
            self.altitude = float(self.parent().altitude.text())
            self.focal = float(self.parent().focal.text())  
            #okay in mm https://www.imaging-resource.com/PRODS/sony-a5100/sony-a5100DAT.HTM

            #Convert pixels to meters
            measurements = self.iw.measurements * (
                fac * self.pixeldim * self.altitude / self.focal) 
            areas = self.iw.areaValues * (
                fac * self.pixeldim * self.altitude / self.focal)**2
            optical = np.array([
                self.parent().id.text(), self.image_name[0], self.focal,
                self.altitude, self.pixeldim
            ])
            names_optical = [
                'Image ID', 'Image Path', 'Focal Length', 'Altitude',
                'Pixel Dimension'
            ]
            names_widths = ['Object'] + ['Length (m)'] + self.iw.widthNames

            #Write .csv file
            with open(name + '.csv', 'w') as csvfile:
                writer = csv.writer(csvfile)
                for (f, g) in zip(names_optical, optical):
                    writer.writerow([f, g])
                writer.writerow(['Notes', self.parent().notes.toPlainText()])

                writer.writerow([''])
                writer.writerow(names_widths)

                for k, f in enumerate(self.lengthNames):  #write lengths and widths
                    vals = map(lambda t: format(t,'.3f'),measurements[k, :].ravel())
                    line = [[f] + list(vals)]
                    writer.writerows(line)

                writer.writerow([''])
                writer.writerow(['Object'] + ['Angle'])

                for k, f in enumerate(self.angleNames):  #write angles
                    line = [[f] + ["{0:.3f}".format(self.iw.angleValues[k])]]  #need to convert NaNs to empty
                    writer.writerows(line)

                writer.writerow([''])
                writer.writerow(['Object'] + ['Area (m^2)'])

                for k, f in enumerate(self.areaNames):  #write areas-
                    line = [[f] + ["{0:.3f}".format(areas[k])]]  #need to convert NaNs to empty
                    writer.writerows(line)                   

            #Export image
            self.setGeometry(
                QtCore.QRect(QtCore.QPoint(0, 0),
                             QtCore.QSize(1000, 1000)))  #change main window size
            self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
            pix = QtGui.QPixmap(1000,1000)
            self.iw.viewport().render(pix)
            pix.save(name + '-measurements.png')

    class imwin(QGraphicsView):  #Subclass QLabel for interaction w/ QPixmap
        def __init__(self, parent=None):
            super(imwin, self).__init__(parent)
            QApplication.setOverrideCursor(QtCore.Qt.CrossCursor)  #change cursor
            self.scene = QGraphicsScene()
            self.view = QGraphicsView(self.scene)

            self.pixmap = None
            self._lastpos = None
            self._thispos = None
            self.delta = QtCore.QPointF(0, 0)
            self.nm = None
            self.measuring_length = False
            self.measuring_widths = False
            self.measuring_area = False
            self.measuring_custom = False
            self.measuring_angle = False
            self._zoom = 1
            self.newPos = None
            self.oldPos = None
            self.factor = 1.0
            self.numwidths = None
            self.widthNames = []
            #self.lengths = []
            #self.widths = []
            self.d = {}  #dictionary for line items
            #self.k = 0 #initialize counter so lines turn yellow
            self.L = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
            self.W = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
            self.scene.realline = None
            self.scene.testline = None
            self.setMouseTracking(True)
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.setRenderHints(QtGui.QPainter.Antialiasing
                                | QtGui.QPainter.SmoothPixmapTransform)
            self.setRenderHint(QtGui.QPainter.Antialiasing, True)
            self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
            self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
            self.setInteractive(False)
            #self.setFrameShape(QtGui.QFrame.NoFrame)

        def keyPressEvent(self, event):  #shift modifier for panning
            if event.key() == QtCore.Qt.Key_Shift:
                pos = QtGui.QCursor.pos()
                self.oldPos = self.mapToScene(self.mapFromGlobal(pos))

        def mouseMoveEvent(self, event):
            data = self.mapToScene(event.pos())
            rules = [self.measuring_length, self.measuring_angle, self.measuring_area]

            #Shift to pan
            modifiers = QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier and self.oldPos:
                self.newPos = data #self.mapToScene(event.pos())
                delta = self.newPos - self.oldPos
                self.translate(delta.x(), delta.y())

            #dragging line
            elif self._thispos and any(rules):
                if self.measuring_length:
                    self.parent().statusBar.showMessage(
                        'Click to place next point... double click to finish')
                if self.measuring_area:
                    self.parent().statusBar.showMessage(
                        'Click to place next point... close polygon to finish')
                if self.measuring_angle:
                    self.parent().statusBar.showMessage(
                        'Click point to define vector')

                end = QtCore.QPointF(data)#self.mapToScene(event.pos()))
                start = self._thispos

                if self.measuring_angle and self._lastpos:
                    start = self._lastpos

                if self.scene.testline:  #remove old line
                    self.scene.removeItem(self.scene.testline)
                    self.scene.testline = False

                if self.measuring_area and self.line_count > 2:
                    intersect, xi, yi, k = self.A.checkIntersect(data.x(),data.y())
                    if self.scene.ellipseItem: #remove existing intersect
                        self.scene.removeItem(self.scene.ellipseItem)
                        self.scene.ellipseItem = False
                    if self.scene.polyItem:  
                        self.scene.removeItem(self.scene.polyItem)  
                        self.scene.polyItem = False                         
                    if intersect:                 
                        #indicate intersect point    
                        p = QtCore.QPointF(xi, yi)
                        self.scene.ellipseItem = QGraphicsEllipseItem(0, 0, 10, 10)                        
                        self.scene.ellipseItem.setPos(p.x() - 10 / 2, p.y() - 10 / 2)
                        self.scene.ellipseItem.setBrush(
                        QtGui.QBrush(QtCore.Qt.blue, style=QtCore.Qt.SolidPattern))
                        self.scene.ellipseItem.setFlag(
                        QGraphicsItem.ItemIgnoresTransformations,
                        False)  #size stays small, but doesnt translate if set to false
                        self.scene.addItem(self.scene.ellipseItem)
                        #shade polygon region
                        points = [ QtCore.QPointF(x,y) for x,y in zip( self.A.x[k:], self.A.y[k:] ) ]
                        points.append(QtCore.QPointF(xi,yi))
                        self.scene.polyItem = QGraphicsPolygonItem(QtGui.QPolygonF(points))
                        self.scene.polyItem.setBrush( QtGui.QBrush(QtGui.QColor(255,255,255,127)) )
                        self.scene.addItem(self.scene.polyItem)

                self.scene.testline = QGraphicsLineItem(QtCore.QLineF(start, end))
                self.scene.addItem(self.scene.testline)

        def mouseDoubleClickEvent(self, event):
            def qpt2pt(x, y):
                Q = self.mapFromScene(self.mapToScene(x, y))
                return Q.x(), Q.y()

            #only delete lines if bezier fit
            if self.measuring_length and self.parent().bezier.isChecked():
                self.parent().statusBar.showMessage('Length measurement complete.')
                #Remove most recent items drawn (exact lines)
                nl = self.line_count
                for k, i in enumerate(self.scene.items()):
                    if k < nl:
                        self.scene.removeItem(i)

            if self._lastpos and self.measuring_length:

                #catmull roms spline instead?
                #https://codeplea.com/introduction-to-splines
                n = max(1000, self.numwidths * 50)  #num of interpolating points

                if self.parent().bezier.isChecked():
                    #https://gist.github.com/Alquimista/1274149

                    def bernstein_poly(i, n, t):
                        return comb(n, i) * (t**(n - i)) * (1 - t)**i

                    points = np.vstack((self.L.x, self.L.y)).T

                    def bezier_curve(points, nTimes=n):

                        nPoints = len(points)
                        xPoints = np.array([p[0] for p in points])
                        yPoints = np.array([p[1] for p in points])
                        t = np.linspace(0.0, 1.0, nTimes)
                        polynomial_array = np.array([
                            bernstein_poly(i, nPoints - 1, t)
                            for i in range(0, nPoints)
                        ])

                        xvals = np.dot(xPoints, polynomial_array)[::-1]
                        yvals = np.dot(yPoints, polynomial_array)[::-1]
                        slopes = np.gradient(yvals) / np.gradient(
                            xvals)  #change with analytic gradient
                        return xvals, yvals, slopes

                    self.xs, self.ys, slopes = bezier_curve(points, nTimes=n)

                    pts = np.array(list(map(qpt2pt, self.xs, self.ys)))
                    x, y = pts[:, 0], pts[:, 1]

                    self.l = np.cumsum(np.hypot(
                        np.gradient(x), np.gradient(y)))  #integrate for length
                    add = np.concatenate(
                        (self.l[-1], np.empty(self.nm) * np.nan),
                        axis=None)  #add length and row of nans for possible widths
                    add = np.expand_dims(add, axis=0)
                    self.measurements = np.append(self.measurements, add, axis=0)

                    #get pts for width drawing
                    bins = np.linspace(0, self.l[-1], self.numwidths + 1)
                    inds = np.digitize(self.l, bins)
                    __, self.inddec = np.unique(inds, return_index=True)

                    self.xp, self.yp = x[self.inddec], y[self.inddec]
                    self.m = slopes[self.inddec]

                    #Identify width spine points
                    self.xsw = x[inds]
                    self.ysw = y[inds]

                    for i in range(1, n - 1):
                        start = self.mapFromScene(
                            self.mapToScene(self.xs[i - 1],
                                            self.ys[i - 1]))  #+ self.pos()
                        mid = self.mapFromScene(
                            self.mapToScene(self.xs[i], self.ys[i]))  #+ self.pos()
                        end = self.mapFromScene(
                            self.mapToScene(self.xs[i + 1],
                                            self.ys[i + 1]))  # + self.pos()
                        path = QtGui.QPainterPath(start)
                        path.cubicTo(start, mid, end)
                        self.scene.addPath(path)

                if not self.parent().bezier.isChecked():

                    pts = np.array(list(map(qpt2pt, self.L.x, self.L.y)))
                    x, y = pts[:, 0], pts[:, 1]

                    self.l = np.cumsum(np.hypot(np.diff(x),
                                                np.diff(y)))  #integrate for length
                    add = np.concatenate(
                        (self.l[-1], np.empty(self.nm) * np.nan),
                        axis=None)  #add length and row of nans for possible widths
                    add = np.expand_dims(add, axis=0)
                    self.measurements = np.append(self.measurements, add, axis=0)

            self.measuring_angle = False
            self.measuring_length = False
            self._thispos = False

        def measure_widths(self):
            self.measuring_widths = True
            self.k = 0
            self.W = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))  #preallocate custom widths
            self.nspines = 2 * (self.numwidths - 1)
            self.parent().statusBar.showMessage(
                'Click point along spines to make width measurements perpindicular to the length segment'
            )
            #Draw widths
            for k, m in enumerate(self.m[1:-1]):  #only middle widths
                x1, y1 = self.xp[k + 1], self.yp[k + 1]

                x2 = self.pixmap_fit.width()  # - x1
                y2 = -(1 / m) * (x2 - x1) + y1

                y0 = self.pixmap_fit.height()  # - y1
                x0 = -m * (y0 - y1) + x1

                #use larger distance
                if np.hypot((x1 - x0), (y1 - y0)) > np.hypot((x1 - x2), (y1 - y2)):
                    x2 = x1 + (x1 - x0)
                    y2 = y1 + (y1 - y0)
                else:
                    x0 = x1 + (x1 - x2)
                    y0 = y1 + (y1 - y2)

                # Limit spines to size of image...I am sure there is a cleaner way to do this
                if y2 > self.pixmap_fit.height():
                    y2 = self.pixmap_fit.height()
                    x2 = -m * (y2 - y1) + x1
                elif y2 < 0:
                    y2 = 0
                    x2 = -m * (y2 - y1) + x1

                if x0 > self.pixmap_fit.width():
                    x0 = self.pixmap_fit.width()
                    y0 = -(1 / m) * (x0 - x1) + y1
                elif x0 < 0:
                    x0 = 0
                    y0 = -(1 / m) * (x0 - x1) + y1

                # Limit spines to size of image...I am sure there is a cleaner way to do this
                if y0 > self.pixmap_fit.height():
                    y0 = self.pixmap_fit.height()
                    x0 = -m * (y0 - y1) + x1
                elif y0 < 0:
                    y0 = 0
                    x0 = -m * (y0 - y1) + x1

                if x2 > self.pixmap_fit.width():
                    x2 = self.pixmap_fit.width()
                    y2 = -(1 / m) * (x2 - x1) + y1
                elif x2 < 0:
                    x2 = 0
                    y2 = -(1 / m) * (x2 - x1) + y1

                for l, (x, y) in enumerate(zip([x0, x2], [y0, y2])):
                    start = QtCore.QPointF(x1, y1)
                    end = QtCore.QPointF(x, y)
                    self.scene.interpLine = QGraphicsLineItem(
                        QtCore.QLineF(start, end))
                    self.d["{}".format(2 * k + l)] = self.scene.interpLine
                    self.scene.addItem(self.scene.interpLine)

                    if k == 0 and l == 0:
                        self.scene.interpLine.setPen(
                            QtGui.QPen(QtGui.QColor('yellow')))

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

                    start = self._lastpos
                    self.measuring_angle = False
                    a = np.array([data.x() - start.x(), data.y() - start.y()])
                    b = np.array([
                        self._thispos.x() - start.x(),
                        self._thispos.y() - start.y()
                    ])
                    t = np.arccos(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
                    t *= 180 / np.pi  #convert to degrees
                    self.T.update(t)
                    self.angleValues = np.append(self.angleValues,t)
                    self.parent().statusBar.showMessage(
                        'Angle measurement complete')

                self.scene.realline = QGraphicsLineItem(QtCore.QLineF(start, end))
                self.scene.addItem(self.scene.realline)
                #self.scene.realline.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)

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
                    self.parent().statusBar.showMessage(
                        'Polygon area measurement completed')
                else:
                    self.A.update(data.x(),data.y()) #update with click point
                
            #https://stackoverflow.com/questions/30898846/qgraphicsview-items-not-being-placed-where-they-should-be
            if self.measuring_widths:  #measure widths, snap to spines

                #y2 = m*(x2-x0)+y0
                #y2 = mp*(x2-x1)+y1
                #solves this system of equations in Ax=b form
                k = int(self.k / 2) + 1  #same origin for spine on either side
                x0, y0 = self.xp[k], self.yp[k]
                x1, y1 = data.x(), data.y()
                m = self.m[k]  #tangent to whale length curve
                mp = -1 / self.m[k]  #perpindicular to whale length curve

                A = np.matrix([[mp, -1], [m, -1]])
                b = np.array([-y0 + mp * x0, -y1 + m * x1])
                x = np.linalg.solve(A, b)
                p = QtCore.QPointF(x[0], x[1])
                self.W.update(data.x(), data.y())

                s = 10  #dot size
                self.scene.ellipseItem = QGraphicsEllipseItem(0, 0, s, s)
                self.scene.ellipseItem.setPos(p.x() - s / 2, p.y() - s / 2)
                self.scene.ellipseItem.setBrush(
                    QtGui.QBrush(QtCore.Qt.red, style=QtCore.Qt.SolidPattern))
                self.scene.ellipseItem.setFlag(
                    QGraphicsItem.ItemIgnoresTransformations,
                    False)  #size stays small, but doesnt translate if false
                self.scene.addItem(self.scene.ellipseItem)
                self.k += 1
                
                if self.k < self.nspines:
                    self.d[str(self.k)].setPen(QtGui.QPen(
                        QtGui.QColor('yellow')))  #Highlight next spine
                if self.k == self.nspines:
                    self.parent().statusBar.showMessage(
                        'Width measurements complete')
                    self.measuring_widths = False
                    width = np.sqrt(
                        (self.W.x[1::2] - self.W.x[0::2])**2 +
                        (self.W.y[1::2] - self.W.y[0::2])**2)  #calculate widths
                    #update most recent row w/ length measurement
                    self.measurements[-1,1:] = width  
        
        #MouseWheel Zoom
        def wheelEvent(self, event):
            #https://stackoverflow.com/questions/35508711/how-to-enable-pan-and-zoom-in-a-qgraphicsview
            #transform coordinates correctly
            #https://stackoverflow.com/questions/20942586/controlling-the-pan-to-anchor-a-point-when-zooming-into-an-image
            #https://stackoverflow.com/questions/41226194/pyqt4-pixel-information-on-rotated-image
            zoomInFactor = 1.05
            zoomOutFactor = 1 / zoomInFactor

            self.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.setResizeAnchor(QGraphicsView.NoAnchor)
            oldPos = self.mapToScene(event.pos())

            #Zoom
            #y component for mouse with two wheels
            #https://quick-geek.github.io/answers/885796/index.html
            if event.angleDelta().y() > 0:
                zoomFactor = zoomInFactor
            else:
                zoomFactor = zoomOutFactor
            self.scale(zoomFactor, zoomFactor)

            newPos = self.mapToScene(event.pos())  #Get the new position
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
                A = np.matrix( [[dx/Tu, -dvx/Tv],
                                [dy/Tu, -dvy/Tv]], dtype = 'float' )
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
                
    class angleData():  #actually need separate class from posdata? probably not
        def __init__(self, t):
            self.t = t

        def update(self, add_t):
            self.t = np.append(self.t, add_t)

        def downdate(self):
            self.t = self.t[:-1]


    class Window(QWidget):
        def __init__(self, parent=None
                    ):  #init methods runs every time (core application stuff)
            super(Window, self).__init__()
            self.setGeometry(50, 50, 600, 500)  #x,y,width,height
            #elf.setStyleSheet("background-color: rgb(0,0,0)") #change color
            #self.setStyleSheet("font-color: rgb(0,0,0)") #change color
            self.setWindowTitle("MorphoMetriX")
            self.dialog = Second(self)

            self.label_id = QLabel("Image ID")
            self.id = QLineEdit()
            self.id.setText('0000')

            #Define custom attributes for pixel -> SI conversion
            self.label_foc = QLabel("Focal Length (mm):")
            self.focal = QLineEdit()
            self.focal.setText('50')

            self.label_alt = QLabel("Altitude (m):")
            self.altitude = QLineEdit(self)
            self.altitude.setText('50')

            self.label_pd = QLabel("Pixel Dimension (mm/pixel)")
            self.pixeldim = QLineEdit()
            self.pixeldim.setText('0.00391667')

            self.label_widths = QLabel("# Width Segments:")
            self.numwidths = QLineEdit()
            self.numwidths.setText('10')

            self.label_not = QLabel("Notes:")
            self.notes = QPlainTextEdit(self)
            #self.notes.resize(280,40)
            
            self.manual = QWebEngineView()
            #fpath = os.path.abspath('/Users/WalterTorres/Dropbox/KC_WT/MorphoMetrix/morphometrix/README.html')
            #webpage = QtCore.QUrl.fromLocalFile(fpath)
            webpage = QtCore.QUrl('https://wingtorres.github.io/morphometrix/')
            self.manual.setUrl(webpage)

            # self.okay = QPushButton("okay?",self)
            self.fileimport = QPushButton("Start measuring", self)
            self.fileimport.clicked.connect(self.openwin)
            self.exit = QPushButton("Exit", self)
            self.exit.clicked.connect(self.close_application)

            grid = QGridLayout()
            grid.addWidget(self.label_id, 1, 0)
            grid.addWidget(self.id, 1, 1)

            grid.addWidget(self.label_foc, 2, 0)
            grid.addWidget(self.focal, 2, 1)
            grid.addWidget(self.label_alt, 3, 0)
            grid.addWidget(self.altitude, 3, 1)
            grid.addWidget(self.label_pd, 4, 0)
            grid.addWidget(self.pixeldim, 4, 1)
            grid.addWidget(self.label_widths, 5, 0)
            grid.addWidget(self.numwidths, 5, 1)
            grid.addWidget(self.label_not, 6, 0)
            grid.addWidget(self.notes, 6, 1)
            # grid.addWidget(self.okay,5,1)
            grid.addWidget(self.fileimport, 7, 1)
            grid.addWidget(self.exit, 7, 3)
            grid.addWidget(self.manual, 8,0,1,4)

            self.setLayout(grid)
            # self.connect(self.okay, QtCore.SIGNAL("clicked()"), self.getvars)
            self.show()

        def getvars(self):
            try:
                alt = float(self.altitude.text())
                foc = float(self.focal.text())
                print('Focal Length = ', foc)
                print('Altitude = ', alt)
            except ValueError as error:
                print('Values must be floats!!!', error)

        def openwin(self):
            self.dialog.show()

        def close_application(self):
            choice = QMessageBox.question(self, 'exit', "Exit program?",
                                        QMessageBox.Yes | QMessageBox.No)
            if choice == QMessageBox.Yes:
                self.deleteLater()
                self.close()
            else:
                pass


    def run():
        app = QApplication(sys.argv)
        GUI = Window()
        # GUI.show()
        #app.exec_()
        sys.exit(app.exec_())
    
    run()

if __name__ == "__main__":
    main()
