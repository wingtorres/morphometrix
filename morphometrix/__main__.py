#!/usr/bin/env python
import sys
import csv
import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QMainWindow, QApplication, QGraphicsView, QGraphicsScene, QWidget, QPushButton, QCheckBox, QStatusBar, QLabel, QLineEdit, QPlainTextEdit, QGridLayout, QFileDialog, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsItem, QMessageBox, QInputDialog
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

            self.custom = QPushButton("Custom Length", self)
            self.custom.clicked.connect(self.measure_custom)
            self.lengthnames = []

            self.anglebutton = QPushButton("Measure Angle", self)
            self.anglebutton.clicked.connect(self.measure_angle)
            self.anglenames = []

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
            self.tb.addWidget(self.anglebutton)
            self.tb.addWidget(self.custom)
            self.tb.addWidget(self.undobutton)
            self.tb.addWidget(self.bezier)

        def file_open(self):
            self.image_name = QFileDialog.getOpenFileName(self, 'Open File')
            self.iw.pixmap = QtGui.QPixmap(self.image_name[0])
            self.iw.pixmap_fit = self.iw.pixmap.scaled(
                self.iw.pixmap.width(),
                self.iw.pixmap.height(),
                QtCore.Qt.KeepAspectRatio,
                transformMode=QtCore.Qt.SmoothTransformation)
            self.iw.scene.clear()
            self.iw.scene.addPixmap(self.iw.pixmap_fit)  #add image
            self.iw.setScene(self.iw.scene)

            #Adjust window size automatically?
            self.setGeometry(
                QtCore.QRect(QtCore.QPoint(0, 0),
                            QtCore.QSize(1000, 1000)))  #change main window size
            self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
            self.iw.scene.update()
            self.statusBar.showMessage(
                'Select a measurement to make from the toolbar')

            #Initialize for new image
            self.iw.numwidths = int(
                self.parent()
                .numwidths.text())  #fetch # of length segments upon file open
            self.lengthnames = []
            self.iw.widthnames = [
                '{0:2.2f}% Width'.format(100 * f / self.iw.numwidths)
                for f in np.arange(1, self.iw.numwidths)
            ]
            self.iw.nm = len(
                self.iw.widthnames
            )  #number of possible measurements per segment (length+ #widths)
            self.iw.measurements = np.empty((0, self.iw.nm + 1), int) * np.nan
            self.iw._lastpos = None
            self.iw._thispos = None
            self.iw.measuring_length = False
            self.iw.measuring_widths = False
            self.iw.measuring_angle = False
            self.iw._zoom = 0
            self.iw.factor = 1.0
            self.iw.d = {}  #dictionary for line items
            self.iw.k = 0  #initialize counter so lines turn yellow
            self.iw.m = None
            self.iw.A = posData(
                np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #lengths
            self.iw.W = posData(
                np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))  #widths
            self.iw.T = angleData(np.empty(shape=(0, 0)))  #widths
            self.iw.scene.realline = None
            self.iw.scene.testline = None
            self.iw.scene.ellipseItem = None
            self.iw.image_name = None

        def measure_length(self):
            self.iw.line_count = 0
            self.iw.measuring_length = True
            self.lengthnames.append("Total Length")
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
                self.anglenames.append(self.lea.text())

        def measure_custom(self):
            self.iw.line_count = 0
            self.iw.measuring_custom = True
            self.iw.measuring_length = True
            self.iw._lastpos = None
            self.iw._thispos = None
            self.iw.A = posData(
                np.empty(shape=(0, 0)),
                np.empty(shape=(0, 0)))  #preallocate custom length
            self.statusBar.showMessage(
                'Click initial point for length measurement')

            self.lel = QLineEdit(self)
            self.lel.move(130, 22)
            self.show()

            text, ok = QInputDialog.getText(self, 'Input Dialog', 'Segment name')
            if ok:
                self.lel.setText(str(text))
                self.lengthnames.append(self.lel.text())

        def undo(self):

            if self.iw.measuring_length:
                self.iw._thispos = self.iw._lastpos
                self.iw.A.downdate()  #remove data
                self.iw.scene.removeItem(self.iw.scene.realline)  #remove graphic

            if self.iw.measuring_widths:
                self.iw.W.downdate()  #remove data
                self.iw.scene.removeItem(
                    self.iw.scene.ellipseItem)  #remove graphic
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
            self.pixeldim = float(
                self.parent()
                .pixeldim.text())  #change this to correct fraction (cm/pixel)
            self.altitude = float(self.parent().altitude.text())
            self.focal = float(
                self.parent().focal.text()
            )  #okay in mm https://www.imaging-resource.com/PRODS/sony-a5100/sony-a5100DAT.HTM

            measurements = self.iw.measurements * (
                fac * self.pixeldim * self.altitude / self.focal
            )  #convert pixels to meters
            optical = np.array([
                self.parent().id.text(), self.image_name[0], self.focal,
                self.altitude, self.pixeldim
            ])
            names_optical = [
                'Image ID', 'Image Path', 'Focal Length', 'Altitude',
                'Pixel Dimension'
            ]
            names_widths = ['Object Name'] + ['Length'] + self.iw.widthnames
            names_lengths = self.lengthnames  #['Total Length'] + self.customnames

            #Write .csv file
            with open(name + '.csv', 'w') as csvfile:
                writer = csv.writer(csvfile)
                for (f, g) in zip(names_optical, optical):
                    writer.writerow([f, g])
                writer.writerow(['Notes', self.parent().notes.toPlainText()])

                writer.writerow([''])
                writer.writerow(names_widths)

                for k, f in enumerate(names_lengths):  #write lengths and widths
                    vals = map(lambda t: format(t,'.3f'),measurements[k, :].ravel())
                    line = [[f] + list(vals)]
                    writer.writerows(line)

                writer.writerow([''])
                writer.writerow(['Object Name'] + ['Angle'])
                for k, f in enumerate(self.anglenames):  #write angles
                    line = [[f] + ["{0:.3f}".format(self.iw.T.t[k])]]  #need toconvert NaNs to empty
                    writer.writerows(line)

            #Export image
            self.setGeometry(
                QtCore.QRect(QtCore.QPoint(0, 0),
                            QtCore.QSize(1000, 1000)))  #change main window size
            self.iw.fitInView(self.iw.scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
            pix = QtGui.QPixmap(
                1000,
                1000)  #self.iw.view.viewport().size())#self.iw.pixmap_fit.copy
            self.iw.viewport().render(pix)
            pix.save(name + '-measurements.png')


    class imwin(QGraphicsView):  #Subclass QLabel for interaction w/ QPixmap
        def __init__(self, parent=None):
            super(imwin, self).__init__(parent)
            QApplication.setOverrideCursor(QtCore.Qt.CrossCursor)  #change cursor
            self.scene = QGraphicsScene()
            self.view = QGraphicsView(self.scene)

            #self.bezier_fit = True
            self.pixmap = None
            self._lastpos = None
            self._thispos = None
            self.delta = QtCore.QPointF(0, 0)
            self.nm = None
            self.measuring_custom = False
            self.measuring_length = False
            self.measuring_widths = False
            self.measuring_angle = False
            self._zoom = 1
            self.newPos = None
            self.oldPos = None
            self.factor = 1.0
            self.numwidths = None
            self.widthnames = []
            #self.lengths = []
            #self.widths = []
            self.d = {}  #dictionary for line items
            #self.k = 0 #initialize counter so lines turn yellow
            self.A = posData(np.empty(shape=(0, 0)), np.empty(shape=(0, 0)))
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

            #Shift to pan
            modifiers = QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier and self.oldPos:
                self.newPos = self.mapToScene(event.pos())
                delta = self.newPos - self.oldPos
                self.translate(delta.x(), delta.y())

            #dragging line
            elif self._thispos and (self.measuring_length
                                    or self.measuring_angle):  #only on mouse press
                if self.measuring_length:
                    self.parent().statusBar.showMessage(
                        'Click to place next point... double click to finish')
                if self.measuring_angle:
                    self.parent().statusBar.showMessage(
                        'Click point to define vector')

                end = QtCore.QPointF(self.mapToScene(event.pos()))
                start = self._thispos

                if self.measuring_angle and self._lastpos:
                    start = self._lastpos

                if self.scene.testline:  #remove old line
                    self.scene.removeItem(self.scene.testline)

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

            if self._lastpos and not (self.measuring_widths or self.measuring_angle):

                #catmull roms spline instead?
                #https://codeplea.com/introduction-to-splines
                n = max(1000, self.numwidths * 50)  #num of interpolating points

                if self.parent().bezier.isChecked():
                    #https://gist.github.com/Alquimista/1274149

                    def bernstein_poly(i, n, t):
                        return comb(n, i) * (t**(n - i)) * (1 - t)**i

                    points = np.vstack((self.A.x, self.A.y)).T

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

                    pts = np.array(list(map(qpt2pt, self.A.x, self.A.y)))
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

            data = self.mapToScene(event.pos())
            #https://stackoverflow.com/questions/21197658/how-to-get-pixel-on-qgraphicspixmapitem-on-a-qgraphicsview-from-a-mouse-click

            #draw piecewise lines
            if self.scene.testline and (self.measuring_length
                                        or self.measuring_angle) and self._thispos:
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
                    self.parent().statusBar.showMessage(
                        'Angle measurement complete')

                self.scene.realline = QGraphicsLineItem(QtCore.QLineF(start, end))
                #self.scene.realline.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
                self.scene.addItem(self.scene.realline)

            #Collect piecewise line start/end points
            if self.measuring_angle:
                self._lastpos = self._thispos  # save old position value
                self._thispos = QtCore.QPointF(data)  # update current position

            if self.measuring_length:
                self._lastpos = self._thispos  # save old position value
                self._thispos = QtCore.QPointF(data)  # update current position
                self.A.update(data.x(), data.y())  # update total length
                self.line_count += 1

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
                    self.measurements[
                        -1,
                        1:] = width  #update most recent row w/ length measurement

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

        def downdate(self):
            self.x = self.x[:-1]
            self.y = self.y[:-1]


    class angleData(
    ):  #do i actually need separate class from posdata? probably not
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
            self.setGeometry(50, 50, 600, 250)  #x,y,width,height
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
