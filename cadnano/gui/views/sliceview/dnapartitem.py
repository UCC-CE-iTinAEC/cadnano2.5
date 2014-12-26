
from cadnano.gui.controllers.itemcontrollers.dnapartitemcontroller import DnaPartItemController
from .virtualhelixitem import VirtualHelixItem

from . import slicestyles as styles
import cadnano.util as util
from cadnano import getReopen

from PyQt5.QtCore import QPointF, Qt, QRectF, QEvent, pyqtSignal, pyqtSlot, QObject
from PyQt5.QtGui import QBrush, QPainter, QPainterPath, QPen, QColor
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsPathItem
from PyQt5.QtWidgets import QGraphicsSimpleTextItem, QGraphicsTextItem
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsRectItem
from PyQt5.QtWidgets import QUndoCommand, QStyle

from math import sqrt, atan2, degrees, pi

_RADIUS = 60
HIGHLIGHT_WIDTH = 40
_DEFAULT_RECT = QRectF(0, 0, 2 * _RADIUS, 2 * _RADIUS)
DELTA = (HIGHLIGHT_WIDTH - styles.SLICE_HELIX_STROKE_WIDTH)/2.
_HOVER_RECT = _DEFAULT_RECT.adjusted(-DELTA, -DELTA, DELTA, DELTA)

_DNALINE_WIDTH = 1
_DNA_PEN = QPen(styles.BLUE_STROKE, _DNALINE_WIDTH)
_DNA_BRUSH = QBrush(QColor(153, 204, 255, 128), 1)
_SELECT_STROKE_WIDTH = 10
_SELECT_PEN = QPen(QColor(204, 0, 0, 64), _SELECT_STROKE_WIDTH)
_SELECT_PEN.setCapStyle(Qt.FlatCap)
_SELECT_BRUSH = QBrush(QColor(204, 0, 0, 128))

_HOVER_PEN = QPen(QColor(255, 255, 255), 128)
_HOVER_BRUSH = QBrush(QColor(255, 255, 255, 0))


class DnaSelectionItem(QGraphicsPathItem):
    def __init__(self, startAngle, spanAngle, parent=None):
        # setup DNA line
        super(QGraphicsPathItem, self).__init__(parent)
        self.setPen(_SELECT_PEN)
        self.updateAngle(startAngle, spanAngle)
    # end def

    def updateAngle(self, startAngle, spanAngle):
        self._startAngle = startAngle
        self._spanAngle = spanAngle
        path = QPainterPath()
        path.arcMoveTo(_DEFAULT_RECT, startAngle)
        path.arcTo(_DEFAULT_RECT, startAngle, spanAngle)
        self.setPath(path)
    # end def
# end class


class DnaHoverRegion(QGraphicsEllipseItem):
    def __init__(self, rect, parent=None):
        # setup DNA line
        super(QGraphicsEllipseItem, self).__init__(rect, parent)
        self.setPen(QPen(Qt.NoPen))
        self.setBrush(_HOVER_BRUSH)
        self.setAcceptHoverEvents(True)
        # self.setFlag(QGraphicsItem.ItemStacksBehindParent)

        # hover marker
        self._hoverLine = QGraphicsLineItem(-_SELECT_STROKE_WIDTH/2, 0, _SELECT_STROKE_WIDTH/2, 0, self)
        self._hoverLine.setPen(QPen(QColor(204, 0, 0), .5))
        self._hoverLine.hide()

        self._startPos = None
        self._startAngle = None  # save selection start
        self._clockwise = None
        self.dummy = DnaSelectionItem(0, 0, parent)
        self.dummy.hide()

    def hoverEnterEvent(self, event):
        self.updateHoverLine(event)
        self._hoverLine.show()
    # end def

    def hoverMoveEvent(self, event):
        self.updateHoverLine(event)
    # end def

    def hoverLeaveEvent(self, event):
        self._hoverLine.hide()
    # end def

    def mousePressEvent(self, event):
        self.updateHoverLine(event)
        pos = self._hoverLine.pos()
        aX, aY, angle = self.snapPosToCircle(pos, _RADIUS)
        if angle != None:
            self._startPos = QPointF(aX, aY)
            self._startAngle = self.updateHoverLine(event)
            self.dummy.updateAngle(self._startAngle, 0)
            self.dummy.show()
        # mark the start
        # f = QGraphicsEllipseItem(pX, pY, 2, 2, self)
        # f.setPen(QPen(Qt.NoPen))
        # f.setBrush(QBrush(QColor(204, 0, 0)))
    # end def

    def mouseMoveEvent(self, event):
        eventAngle = self.updateHoverLine(event)
        # Record initial direction before calling getSpanAngle
        if self._clockwise is None:
            self._clockwise = False if eventAngle > self._startAngle else True
        spanAngle = self.getSpanAngle(eventAngle)
        self.dummy.updateAngle(self._startAngle, spanAngle)
    # end def

    def mouseReleaseEvent(self, event):
        self.dummy.hide()
        endAngle = self.updateHoverLine(event)
        spanAngle = self.getSpanAngle(endAngle)

        if self._startPos != None and self._clockwise != None:
            self.parentItem().addSelection(self._startAngle, spanAngle)
            self._startPos = self._clockwise = None

        # mark the end
        # x = self._hoverLine.x()
        # y = self._hoverLine.y()
        # f = QGraphicsEllipseItem(x, y, 6, 6, self)
        # f.setPen(QPen(Qt.NoPen))
        # f.setBrush(QBrush(QColor(204, 0, 0, 128)))

    # end def

    def updateHoverLine(self, event):
        """
        Moves red line to point (aX,aY) on DnaLine closest to event.pos.
        Returns the angle of aX, aY, using the Qt arc coordinate system
        (0 = east, 90 = north, 180 = west, 270 = south).
        """
        aX, aY, angle = self.snapPosToCircle(event.pos(), _RADIUS)
        if angle != None:
            self._hoverLine.setPos(aX, aY)
            self._hoverLine.setRotation(-angle)
        return angle
    # end def

    def snapPosToCircle(self, pos, radius):
        """Given x, y and radius, return x,y of nearest point on circle, and its angle"""
        pX = pos.x()
        pY = pos.y()
        cX = cY = radius
        vX = pX - cX
        vY = pY - cY
        magV = sqrt(vX*vX + vY*vY)
        if magV == 0:
            return (None, None, None)
        aX = cX + vX / magV * radius
        aY = cY + vY / magV * radius
        angle = (atan2(aY-cY, aX-cX))
        deg = -degrees(angle) if angle < 0 else 180+(180-degrees(angle))
        return (aX, aY, deg)
    # end def

    def getSpanAngle(self, angle):
        """
        Return the spanAngle angle by checking the initial direction of the selection.
        Selections that cross 0° must be handed as an edge case.
        """
        if self._clockwise: # spanAngle is negative
            if angle < self._startAngle:
                spanAngle = angle - self._startAngle
            else:
                spanAngle = -(self._startAngle + (360-angle))
        else: # counterclockwise, spanAngle is positive
            if angle > self._startAngle:
                spanAngle = angle - self._startAngle
            else:
                spanAngle = (360-self._startAngle) + angle
        return spanAngle
    # end def
# end class


class DnaLine(QGraphicsEllipseItem):
    def __init__(self, hover_rect, default_rect, parent=None):
        # setup DNA line
        super(QGraphicsEllipseItem, self).__init__(hover_rect, parent)
        if "color" in parent._model_props:
            self.setPen(QPen(QColor(parent._model_props["color"]), _DNALINE_WIDTH))
        else:
            self.setPen(_DNA_PEN)
        self.setRect(default_rect)
        self.setFlag(QGraphicsItem.ItemStacksBehindParent)
        # self.setSpanAngle(90*16)
        # self.setBrush(_DNA_BRUSH)
        # self.setAcceptHoverEvents(True)
    # end def
    
    def updateColor(self, color):
        """docstring for updateColor"""
        self.setPen(QPen(color, _DNALINE_WIDTH))
        # self.update()
# end class


class DnaPartItem(QGraphicsItem):
    _RADIUS = styles.SLICE_HELIX_RADIUS

    def __init__(self, model_part_instance, parent=None):
        """
        Parent should be either a SliceRootItem, or an AssemblyItem.
        Order matters for deselector, probe, and setlattice
        """
        super(DnaPartItem, self).__init__(parent)
        self._model_instance = model_part_instance
        self._model_part = m_p = model_part_instance.object()
        self._model_props = m_props = m_p.getPropertyDict()
        self._controller = DnaPartItemController(self, m_p)
        self._rect = QRectF(0, 0, 0, 0)
        self._initDeselector()
        self.probe = self.IntersectionProbe(self)
        self.setFlag(QGraphicsItem.ItemHasNoContents)  # never call paint
        self.setZValue(styles.ZPARTITEM)
        # self._initModifierCircle()
        gap = 2 # gap between inner and outer strands
        _OUTER_RECT = QRectF(-gap/2, -gap/2, 2 * _RADIUS+gap, 2 * _RADIUS+gap)
        _INNER_RECT = QRectF(gap/2, gap/2, 2 * _RADIUS-gap, 2 * _RADIUS-gap)
        self._outer_Line = DnaLine(_HOVER_RECT, _OUTER_RECT, self)
        self._inner_Line = DnaLine(_HOVER_RECT, _INNER_RECT, self)

        self.hoverRegion = DnaHoverRegion(_HOVER_RECT, self)

        self._initSelections()





    # end def

    def _initDeselector(self):
        """
        The deselector grabs mouse events that missed a slice and clears the
        selection when it gets one.
        """
        self.deselector = ds = DnaPartItem.Deselector(self)
        ds.setParentItem(self)
        ds.setFlag(QGraphicsItem.ItemStacksBehindParent)
        ds.setZValue(styles.ZDESELECTOR)
    # end def

    def _initModifierCircle(self):
        self._can_show_mod_circ = False
        self._mod_circ = m_c = QGraphicsEllipseItem(_HOVER_RECT, self)
        m_c.setPen(_MOD_PEN)
        m_c.hide()
    # end def

    def _initSelections(self):
        self._selections = self._model_part.getSelectionDict()
        for key in sorted(self._selections):
            (start, end) = self._selections[key]
            # convert bases to angles
    # end def

    def addSelection(self, startAngle, spanAngle):
        dSI = DnaSelectionItem(startAngle, spanAngle, self)
    # end def

    ### SIGNALS ###

    ### SLOTS ###
    def partActiveVirtualHelixChangedSlot(self, part, virtualHelix):
        pass

    def partDimensionsChangedSlot(self, sender):
        pass
    # end def

    def partHideSlot(self, sender):
        self.hide()
    # end def

    def partParentChangedSlot(self, sender):
        # print "DnaPartItem.partParentChangedSlot"
        pass

    def partRemovedSlot(self, sender):
        self.parentItem().removeDnaPartItem(self)
        scene = self.scene()
        scene.removeItem(self)
        self._model_part = None
        self.probe = None
        self._mod_circ = None
        self.deselector = None
        self._controller.disconnectSignals()
        self._controller = None
    # end def

    def partVirtualHelicesReorderedSlot(self, sender, orderedCoordList):
        pass
    # end def

    def partPreDecoratorSelectedSlot(self, sender, row, col, baseIdx):
        """docstring for partPreDecoratorSelectedSlot"""
        vhi = self.getVirtualHelixItemByCoord(row, col)
        view = self.window().slice_graphics_view
        view.scene_root_item.resetTransform()
        view.centerOn(vhi)
        view.zoomIn()
        mC = self._mod_circ
        x,y = self._model_part.latticeCoordToPositionXY(row, col, self.scaleFactor())
        mC.setPos(x,y)
        if self._can_show_mod_circ:
            mC.show()
    # end def

    def partVirtualHelixAddedSlot(self, sender, virtual_helix):
        vh = virtual_helix
        coords = vh.coord()

        empty_helix_item = self._empty_helix_hash[coords]
        # TODO test to see if self._virtual_helix_hash is necessary
        vhi = VirtualHelixItem(vh, empty_helix_item)
        self._virtual_helix_hash[coords] = vhi
    # end def

    def partVirtualHelixRenumberedSlot(self, sender, coord):
        pass
    # end def

    def partVirtualHelixResizedSlot(self, sender, coord):
        pass
    # end def

    def updatePreXoverItemsSlot(self, sender, virtualHelix):
        pass
    # end def

    def partPropertyChangedSlot(self, model_part, property_key, new_value):
        if self._model_part == model_part:
            if property_key == "color":
                color = QColor(new_value)
                self._outer_Line.updateColor(color)
                self._inner_Line.updateColor(color)
            elif property_key == "circular":
                pass
            elif property_key == "dna_sequence":
                pass

    # end def


    ### ACCESSORS ###
    def boundingRect(self):
        return self._rect
    # end def

    def part(self):
        return self._model_part
    # end def

    def scaleFactor(self):
        return self._scaleFactor
    # end def

    def setPart(self, newPart):
        self._model_part = newPart
    # end def

    def window(self):
        return self.parentItem().window()
    # end def

    ### PRIVATE SUPPORT METHODS ###
    def _upperLeftCornerForCoords(self, row, col):
        pass  # subclass
    # end def

    def _updateGeometry(self):
        self._rect = QRectF(0, 0, *self.part().dimensions())
    # end def

    def _spawnEmptyHelixItemAt(self, row, column):
        helix = EmptyHelixItem(row, column, self)
        # helix.setFlag(QGraphicsItem.ItemStacksBehindParent, True)
        self._empty_helix_hash[(row, column)] = helix
    # end def

    def _killHelixItemAt(row, column):
        s = self._empty_helix_hash[(row, column)]
        s.scene().removeItem(s)
        del self._empty_helix_hash[(row, column)]
    # end def

    def _setLattice(self, old_coords, new_coords):
        """A private method used to change the number of rows,
        cols in response to a change in the dimensions of the
        part represented by the receiver"""
        old_set = set(old_coords)
        old_list = list(old_set)
        new_set = set(new_coords)
        new_list = list(new_set)
        for coord in old_list:
            if coord not in new_set:
                self._killHelixItemAt(*coord)
        # end for
        for coord in new_list:
            if coord not in old_set:
                self._spawnEmptyHelixItemAt(*coord)
        # end for
        # self._updateGeometry(newCols, newRows)
        # self.prepareGeometryChange()
        # the Deselector copies our rect so it changes too
        self.deselector.prepareGeometryChange()
        if not getReopen():
            self.zoomToFit()
    # end def

    ### PUBLIC SUPPORT METHODS ###
    def getVirtualHelixItemByCoord(self, row, column):
        if (row, column) in self._empty_helix_hash:
            return self._virtual_helix_hash[(row, column)]
        else:
            return None
    # end def

    def paint(self, painter, option, widget=None):
        pass
    # end def

    def selectionWillChange(self, newSel):
        if self.part() == None:
            return
        if self.part().selectAllBehavior():
            return
        for sh in self._empty_helix_hash.values():
            sh.setSelected(sh.virtualHelix() in newSel)
    # end def

    def setModifyState(self, bool):
        """Hides the mod_rect when modify state disabled."""
        self._can_show_mod_circ = bool
        if bool == False:
            self._mod_circ.hide()

    def updateStatusBar(self, statusString):
        """Shows statusString in the MainWindow's status bar."""
        self.window().statusBar().showMessage(statusString, timeout)
        pass  # disabled for now.

    def vhAtCoordsChanged(self, row, col):
        self._empty_helix_hash[(row, col)].update()
    # end def

    def zoomToFit(self):
        thescene = self.scene()
        theview = thescene.views()[0]
        theview.zoomToFit()
    # end def

    ### EVENT HANDLERS ###
    def mousePressEvent(self, event):
        # self.createOrAddBasesToVirtualHelix()
        QGraphicsItem.mousePressEvent(self, event)
    # end def

    class Deselector(QGraphicsItem):
        """The deselector lives behind all the slices and observes mouse press
        events that miss slices, emptying the selection when they do"""
        def __init__(self, parent_HGI):
            super(DnaPartItem.Deselector, self).__init__()
            self.parent_HGI = parent_HGI
        def mousePressEvent(self, event):
            self.parent_HGI.part().setSelection(())
            super(DnaPartItem.Deselector, self).mousePressEvent(event)
        def boundingRect(self):
            return self.parent_HGI.boundingRect()
        def paint(self, painter, option, widget=None):
            pass
    # end class

    class IntersectionProbe(QGraphicsItem):
        def boundingRect(self):
            return QRectF(0, 0, .1, .1)
        def paint(self, painter, option, widget=None):
            pass
    # end class
# end class
