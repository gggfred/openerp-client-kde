##############################################################################
#
# Copyright (c) 2007-2008 Albert Cervera i Areny <albert@nan-tic.com>
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *

from Koo.Common import Icons
from Koo.Common import Calendar
from Koo.Common import Numeric
from Koo.Common import Common
from Koo.Rpc import Rpc

#
# We store the pointer to the Tiny ModelGroup on QModelIndex.internalPointer
# Fields order should be handled using QHeaderView
#
# Qt.UserRole returns the model id (database id) for the given field
# (QModelIndex),though id() function is also provided for convenience.


# @brief The KooModel class provides a QAbstractItemModel wrapper around
# RecordGroup class.
#
# To use this class, simply call setRecordGroup() to set the RecordGroup
# instance to wrap, and setFields() with the fields to load.
# Then it's ready to be used in any Qt model/view enabled widget such as
# QTreeView or QListView.
# Note that by default KooModel is read-only.
QStringList = list


class KooModel(QAbstractItemModel):

    # Modes
    modelAboutToBeReset = pyqtSignal()
    modelReset = pyqtSignal()
    dataChanged = pyqtSignal(QModelIndex, QModelIndex)
    TreeMode = 1
    ListMode = 2

    # Extra roles appended to UserRole

    # IdRole: Returns model id of the given field
    IdRole = Qt.UserRole
    # ValueRole: Returns the QVariant of the appropiate type
    # for the field. For example, date fields are returned as
    # QDate inside QVariant, instead of a QString as Qt.DisplayRole
    # does. It's been created for the Calendar view but others
    # might benefit too.
    ValueRole = Qt.UserRole + 1

    def __init__(self, parent=None):
        QAbstractItemModel.__init__(self, parent)
        self.group = None
        self.fields = {}
        self.buttons = {}
        self.icon = ''
        self.iconField = ''
        self.child = ''
        self.childField = ''
        self.mode = self.TreeMode
        self.colors = {}
        self.showBackgroundColor = True
        self._readOnly = True
        self._updatesEnabled = True
        self._showToolTips = True
        # visibleFields is an alphabetically sorted list of
        # all visible fields. This means it discards self.icon
        # and self.child fields. The list is updated using
        # updateVisibleFields().
        self.visibleFields = []

    def setRecordGroup(self, group):
        """
        Sets the RecordGroup associated with this Qt Model

        Fields should already be set and can't be added after this call
        :param group:
        :return: None
        :rtype: None
        """
        self.modelAboutToBeReset.emit()

        if self.group:
            self.group.recordsInserted[int, int].disconnect(self.recordsInserted)
            # @xtorello toreview
            self.group.recordChangedSignal['PyQt_PyObject'].disconnect(self.recordChanged)
            # self.group.recordChanged['QObject'].disconnect(self.recordChanged)
            self.group.recordsRemoved[int, int].disconnect(self.recordsRemoved)

        self.group = group
        if self.group:
            self.group.recordsInserted[int, int].connect(self.recordsInserted)
            # @xtorello toreview
            self.group.recordChangedSignal['PyQt_PyObject'].connect(self.recordChanged)
            # self.group.recordChanged[QObject].connect(self.recordChanged)
            self.group.recordsRemoved[int, int].connect(self.recordsRemoved)

        # We emit modelReset() so widgets will be notified that
        # they need to be updated
        self.modelReset.emit()
        self.updateVisibleFields()

    def recordGroup(self):
        """
        Returns the current RecordGroup associated with this Qt Model
        :return:
        """
        return self.group

    def setReadOnly(self, value):
        """
        Sets the model as read-only.

        :param value: True if its readonly
        :type value: bool
        :return: None
        :rtype: None
        """
        self._readOnly = value

    def isReadOnly(self):
        """
        Returns whether the model is read-only or read-write.

        :return:
        """
        return self._readOnly

    def reset(self):
        pass

    def recordsInserted(self, start, end):
        if self._updatesEnabled:
            self.reset()

    def recordChanged(self, record):
        if not record:
            return
        leftIndex = self.indexFromId(record.id)
        if not leftIndex.isValid():
            self.reset()
            return
        rightIndex = self.index(leftIndex.row(), self.columnCount() - 1)
        self.dataChanged.emit(leftIndex, rightIndex)

    def recordsRemoved(self, start, end):
        return None

    def setFields(self, fields):
        """
        Sets the dictionary of fields that should be loaded

        :param fields:
        :return: None
        :rtype: None
        """
        self.fields = fields
        self.updateVisibleFields()

    def setButtons(self, buttons):
        """
        Sets the dictionary of buttons to be shown
        :param buttons:
        :return: None
        :rtype: None
        """
        self.buttons = buttons

    def setFieldsOrder(self, fields):
        """
        Sets the order in which fields should be put in the model.

        If this function is never called fields are put in alphabetical order.

        :param fields:
        :return:None
        :rtype: None
        """
        self.visibleFields = fields
        self.updateVisibleFields()

    def setColors(self, colors):
        """
        Sets the dictionary of colors

        The dictionary is of the form 'color' : 'expression', where
        'expression' is a python boolean expression that will be passed
        to the model, and thus can use model context information.

        :param colors:
        :return:
        """
        self.colors = colors

    def setShowBackgroundColor(self, showBackgroundColor):
        """
        @brief Sets whether the background color should be returned in
        data() or not.

        Setting this to True (default) will make the call to data() with
        Qt.BackgroundRole to return the appropiate background color
        if fields are read only or required.

        :param showBackgroundColor:
        :return:
        """
        self.showBackgroundColor = showBackgroundColor

    def setIconForField(self, icon, icon_field):
        """
        Sets that the contents of field 'icon' are used as an icon
        for field 'iconField'

        The contents (usually an icon name) of the field 'icon' is used for
        the decoration role of 'iconField'
        :param icon:
        :param icon_field:
        :return: None
        :rtype: None
        """
        self.icon = icon
        self.iconField = icon_field
        self.updateVisibleFields()

    def setChildrenForField(self, child, child_field):
        """
        Sets that the children of field 'child' are used as an children
        for field 'childField'

        :param child:
        :param child_field:
        :return: None
        :rtype: None
        """
        self.child = child
        self.childField = child_field
        self.updateVisibleFields()

    def updateVisibleFields(self):
        """
        Updates the list of visible fields. The list is kept sorted and icon
        and child fields are excluded if they have been specified.

        :return: None
        :rtype: None
        """
        if not self.visibleFields:
            self.visibleFields = list(self.fields.keys())[:]
        if self.icon in self.visibleFields:
            del self.visibleFields[self.visibleFields.index(self.icon)]
        if self.child in self.visibleFields:
            del self.visibleFields[self.visibleFields.index(self.child)]

    def setMode(self, mode):
        """
        Set the model to the specified mode

        :param mode:mode parameter can be TreeMode or ListMode, this is not
        %100 necessary in most cases, but it also avoids some checks in many
        cases so at least it can provide some speed improvements.
        :return: None
        :rtype: None
        """
        self.mode = mode

    def setShowToolTips(self, show):
        """
        Sets whether tooltips should be shown or not.

        :param show:
        :return: None
        :rtype: None
        """
        self._showToolTips = show

    def id(self, index):
        """
        Returns the model id corresponding to index

        :param index:
        :return: Model id
        :rtype: int
        """

        if not self.group:
            return 0
        if not index.isValid():
            return 0

        model = self.record(index.row(), index.internalPointer())
        if model:
            return model.id
        else:
            return 0

    # Pure virtual functions from QAbstractItemModel

    def rowCount(self, parent = QModelIndex()):
        if not self.group:
            return 0

        # In list mode we will consider there are no children
        if self.mode == self.ListMode and parent.isValid() and parent.internalPointer() != self.group:
            return 0

        if parent.isValid():
            # Check if this field has associated the children of another one
            field = self.field(parent.column())
            parent_ip = parent.internalPointer()
            if field == self.childField:
                fieldType = self.fieldTypeByName(self.child, parent_ip)
                if fieldType in ['one2many', 'many2many']:
                    value = self.valueByName(parent.row(), self.child, parent_ip)
                    if value:
                        return value.count()
                    else:
                        return 0
                else:
                    return 0

            # If we get here it means that we return the _real_ children
            fieldType = self.fieldType( parent.column(), parent_ip)
            if fieldType in ['one2many', 'many2many']:
                value = self.value(parent.row(), parent.column(), parent_ip)
                if value:
                    return value.count()
                else:
                    return 0

            else:
                return 0
        else:
            return self.group.count()

    def columnCount(self, parent = QModelIndex()):
        if not self.group:
            return 0

        # In list mode we consider there are no children
        if self.mode == self.ListMode and parent.isValid() and parent.internalPointer() != self.group:
            return 0

        # We always return all visibleFields. If the element should have no
        # children then no rows will be returned. This way we avoid
        # duplication of calculations.
        return len(self.visibleFields)

    def flags(self, index):
        defaultFlags = QAbstractItemModel.flags(self, index)
        if 'sequence' in self.fields:
            defaultFlags = defaultFlags | Qt.ItemIsDropEnabled
            if index.isValid():
                defaultFlags = defaultFlags | Qt.ItemIsDragEnabled

        field = self.fields.get(self.field(index.column()))
        if not field:
            # Buttons
            fieldName = self.field(index.column())
            record = self.record(index.row(), index.internalPointer())
            state = 'draft'
            if record and record.fieldExists('state'):
                state = record.value('state')
            states = self.buttons[fieldName].get('states', '').split(',')
            if state in states:
                return defaultFlags
            return Qt.NoItemFlags

        if self._readOnly or ('readonly' in field and field['readonly']):
            return defaultFlags
        else:
            return defaultFlags | Qt.ItemIsEditable

    def setData(self, index, value, role):
        """

        :param index:
        :param value:
        :type value: QVariant
        :param role:
        :return:
        """
        if role != Qt.EditRole:
            return True
        if not index.isValid():
            return True
        model = self.record(index.row(), index.internalPointer())
        if not model:
            return True
        field = self.field(index.column())
        fieldType = self.fieldType(index.column(), index.internalPointer())

        if fieldType == 'boolean':
            model.setValue( field, bool(value))
        elif fieldType in ('float', 'float_time'):
            model.setValue(field, value.value())
        elif fieldType == 'integer':
            model.setValue(field, value.toInt()[0])
        elif fieldType == 'selection':
            value = str(value.toString())
            modelField = self.fields[self.field(index.column())]
            for x in modelField['selection']:
                if x[1] == value:
                    model.setValue( field, x[0])
        elif fieldType in ('char', 'text'):
            model.setValue(field, str(value))
        elif fieldType == 'date':
            model.setValue(field, Calendar.dateToStorage(value.toDate()))
        elif fieldType == 'datetime' and value:
            model.setValue(field, Calendar.dateTimeToStorage(value.value()))
        elif fieldType == 'time' and value:
            model.setValue(field, Calendar.timeToStorage(value.toTime()))
        elif fieldType == 'many2many':
            m = model.value(field)
            m.clear()
            ids = [x.toInt()[0] for x in value.toList()]
            m.load(ids)
        elif fieldType == 'many2one':
            value = value.toList()
            if value:
                value = [int(value[0].toInt()[0]), str(value[1].toString())]
            model.setValue(field, value)
        else:
            print("Unable to store value of type: ", fieldType)

        return True

    def data(self, index, role=Qt.DisplayRole ):
        if not self.group:
            return QVariant()
        if role in (Qt.DisplayRole, Qt.EditRole) or (self._showToolTips and role == Qt.ToolTipRole):
            value = self.value(index.row(), index.column(), index.internalPointer())
            if value is None:
                return QVariant()
            fieldType = self.fieldType(index.column(), index.internalPointer())
            if fieldType in ['one2many', 'many2many']:
                return QVariant('(%d)' % value.count())
            elif fieldType == 'selection':
                field = self.fields[self.field(index.column())]
                for x in field['selection']:
                    if x[0] == value:
                        return QVariant(str(x[1]))
                return QVariant()
            elif fieldType == 'date' and value:
                return QVariant(Calendar.dateToText(Calendar.storageToDate(value)))
            elif fieldType == 'datetime' and value:
                return QVariant(Calendar.dateTimeToText(Calendar.storageToDateTime(value)))
            elif fieldType == 'float':
                # If we use the default conversion big numbers are shown
                # in scientific notation. Also we have to respect the number
                # of decimal digits given by the server.
                field = self.fields[self.field(index.column())]
                if role == Qt.EditRole:
                    thousands = False
                else:
                    thousands = True
                return QVariant(Numeric.floatToText(value, field.get('digits', None), thousands))
            elif fieldType == 'integer':
                return QVariant(Numeric.integerToText(value))
            elif fieldType == 'float_time':
                return QVariant(Calendar.floatTimeToText(value))
            elif fieldType == 'binary':
                if value:
                    return QVariant(_('%d bytes') % len(value))
                else:
                    return QVariant()
            elif fieldType == 'boolean':
                return QVariant(bool(value))
            elif fieldType == 'button':
                if role == Qt.ToolTipRole:
                    fieldName = self.field(index.column())
                    return QVariant( self.buttons[fieldName].get('string', ''))
                return QVariant()
            else:
                if not value  or value is None:
                    return QVariant()
                else:
                    # If the text has several lines put them all in a single one
                    return QVariant(str(value).replace('\n', ' '))
        elif role == Qt.DecorationRole:
            fieldType = self.fieldType(index.column(), index.internalPointer())
            if fieldType == 'button':
                fieldName = self.field(index.column())
                return QVariant(Icons.kdeIcon(self.buttons[fieldName].get('icon')))
            if self.field(index.column()) == self.iconField:
                # Not all models necessarily have the icon so check that first
                model = self.record(index.row(), index.internalPointer())
                if model and self.icon in model.values:
                    return QVariant(Icons.kdeIcon(model.value(self.icon)))
                else:
                    return QVariant()
            else:
                return QVariant()
        elif role == Qt.BackgroundRole:
            if not self.showBackgroundColor:
                return QVariant()
            field = self.fields[self.field( index.column() )]
            model = self.record( index.row(), index.internalPointer() )
            # We need to ensure we're not being asked about a non existent row.
            # This happens in some special cases (an editable tree in a
            # one2many field, such as the case of fiscal year inside sequences).
            # Note that trying to avoid processing this function if index.row()
            # > self.rowCount()-1 works to avoid this but has problems with
            # some tree structures (such as the menu).
            # So we need to make the check here.
            if not model:
                return QVariant()
            # Priorize readonly to required as if it's readonly the
            # user doesn't mind if it's required as she won't be able
            # to change it anyway.
            if not model.isFieldValid(self.field(index.column())):
                color = '#FF6969'
            elif 'readonly' in field and field['readonly']:
                color = 'lightgrey'
            elif 'required' in field and field['required']:
                color = '#ddddff'
            else:
                color = 'white'
            return QVariant(QBrush(QColor(color)))
        elif role == Qt.ForegroundRole:
            if not self.colors:
                return QVariant()
            model = self.record(index.row(), index.internalPointer())
            # We need to ensure we're not being asked about a non existent row.
            # This happens in some special cases (an editable tree in a
            # one2many field, such as the case of fiscal year inside sequences).
            # Note that trying to avoid processing this function if
            # index.row() > self.rowCount()-1 works to avoid this but has
            # problems with some tree structures (such as the menu). So we
            # need to make the check here.
            if not model:
                return QVariant()
            palette = QPalette()
            color = palette.color(QPalette.WindowText)
            for (c, expression) in self.colors:
                if model.evaluateExpression( expression, checkLoad=False ):
                    color = c
                    break
            return QVariant(QBrush(QColor(color)))
        elif role == Qt.TextAlignmentRole:
            fieldType = self.fieldType(index.column(), index.internalPointer())
            if fieldType in ['integer', 'float', 'float_time', 'time', 'date', 'datetime']:
                return QVariant(Qt.AlignRight | Qt.AlignVCenter)
            else:
                return QVariant(Qt.AlignLeft | Qt.AlignVCenter)
        elif role == KooModel.IdRole:
            model = self.record(index.row(), index.internalPointer())
            return QVariant(model.id)
        elif role == KooModel.ValueRole:
            value = self.value( index.row(), index.column(), index.internalPointer())
            fieldType = self.fieldType( index.column(), index.internalPointer())
            if fieldType in ['one2many', 'many2many']:
                # By now, return the same as DisplayRole for these
                return QVariant( '(%d)' % value.count())
            elif fieldType == 'selection':
                # By now, return the same as DisplayRole for these
                field = self.fields[self.field(index.column())]
                for x in field['selection']:
                    if x[0] == value:
                        return QVariant(str(x[1]))
                return QVariant()
            elif fieldType == 'date' and value:
                return QVariant(Calendar.storageToDate(value))
            elif fieldType == 'datetime' and value:
                return QVariant(Calendar.storageToDateTime(value))
            elif fieldType == 'float':
                # If we use the default conversion big numbers are shown
                # in scientific notation. Also we have to respect the number
                # of decimal digits given by the server.
                field = self.fields[self.field(index.column())]
                return QVariant(Numeric.floatToText(value, field.get('digits',None)))
            elif fieldType == 'float_time':
                return QVariant(value)
            elif fieldType == 'binary':
                if value:
                    return QVariant(QByteArray.fromBase64(value))
                else:
                    return QVariant()
            elif fieldType == 'boolean':
                return QVariant(bool(value))
            else:
                if not value:
                    return QVariant()
                else:
                    return QVariant(str(value))
        else:
            return QVariant()

    def index(self, row, column, parent=QModelIndex()):
        if not self.group:
            return QModelIndex()
        if parent.isValid():
            # Consider childField
            field = self.field(parent.column())
            if field == self.childField:
                field = self.child

            value = self.valueByName( parent.row(), field, parent.internalPointer())
            return self.createIndex( row, column, value)
        else:
            return self.createIndex( row, column, self.group)

    def parent(self, index):
        if not self.group:
            return QModelIndex()
        if not index.isValid():
            return QModelIndex()
        if self.mode == self.ListMode:
            return QModelIndex()

        # Search where in the grandparent our parent is
        group = index.internalPointer()

        # We don't want to go upper the model we've been given.
        if group == self.group:
            return QModelIndex()

        # The 'parent' of the child RecordGroup is a Model. The
        # model has a pointer to the RecordGroup it belongs and
        # it's called 'group'
        model = group.parent
        parent = group.parent.group

        if not parent.recordExists(model):
            # Though it should not normally happen, when you reload
            # in the main menu we receive calls in which the model
            # is not in the list.
            return QModelIndex()

        row = parent.indexOfRecord(model)
        for x, y in list(model.values.items()):
            if y == group:
                field = x
                break

        # Consider childField
        if field == self.child:
            field = self.childField

        # We check if the field is in the visibleFields. This can happen
        # if the user forgot to set ListMode and there are children (or parents)
        # of different types, so related models don't have the same
        # fields. This crashed when browsing with the form view, but could
        # happen in other places too.
        if field in self.visibleFields:
            column = self.visibleFields.index(field)
            return self.createIndex( row, column, parent )
        else:
            return QModelIndex()

    def mimeTypes(self):
        return QStringList(['text/plain'])

    def mimeData(self, indexes):
        data = QMimeData()
        d = []
        for index in indexes:
            if index.column() == 0:
                d.append(self.id(index))
        data.setText(str(d[0]))
        return data

    def dropMimeData(self, data, action, row, column, parent):
        if action != Qt.MoveAction:
            return False
        if not parent.isValid():
            return False
        if row != -1 or column != -1:
            return False
        group = parent.internalPointer()
        # Change record order only if the group is sorted by 'sequence' field.
        # Otherwise don't even try to move it as group.sort() won't work due to
        # the need to call the server and thus it'd lose changes.
        # By now, when sortedField is None we consider as if it was 'sequence'
        # because most views will have it as default sort field.
        if group.sortedField and group.sortedField != 'sequence':
            return False
        record = self.recordFromIndex( parent )
        id = int( str( data.text() ) )
        movedRecord = self.recordFromIndex( self.indexFromId( id ) )
        group.records.remove( movedRecord )
        group.records.insert( group.records.index(record), movedRecord )

        if group.count():
            for idx in range(len(group.records)):
                if group.sortedOrder is None or group.sortedOrder == Qt.AscendingOrder:
                    seq = idx + 1
                else:
                    seq = len(group.records) - idx
                group.records[idx].setValue('sequence', seq)
        self.reset()
        return True

    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    # Plain virtual functions from QAbstractItemModel

    def sort(self, column, order):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.group.sort(self.field(column), order)
        except Rpc.RpcException as e:
            pass
        QApplication.restoreOverrideCursor()

    def headerData(self, section, orientation, role):
        if orientation == Qt.Vertical:
            return QVariant()
        if role == Qt.DisplayRole:
            field = self.fields.get(self.field(section))
            if not field:
                field = self.buttons.get(self.field(section))
            return QVariant(Common.normalizeLabel(str(field['string'])))
        elif role == Qt.FontRole and not self._readOnly:
            fieldName = self.field(section)
            if self.group.fieldExists(fieldName) and self.group.isFieldRequired(fieldName):
                font = QFont()
                font.setBold(True)
                return QVariant(font)
        return QVariant()

    def field(self, column):
        """
        Returns the field name for the given column

        :param column:
        :return:
        """
        if column >= len(self.visibleFields):
            return None
        else:
            return self.visibleFields[column]

    # Note that in both fieldType() and fieldTypeByName() functions we ignore
    # the 'group' parameter and use 'self.group' instead as this improves
    # performance as in some cases we won't force loading a record just to know
    # a field type.

    def fieldType(self, column, group):
        """
        Returns the field type for the given column and group

        :param column:
        :param group:
        :return:
        """
        field = self.field(column)
        if not field:
            return None
        if field in self.buttons:
            return 'button'
        return self.group.fields[ field ]['type']

    def fieldTypeByName(self, field, group):
        """
        Returns the field type for the given column and group
        :param field:
        :param group:
        :return:
        """
        if field in self.group.fields:
            return self.group.fields[field]['type']
        else:
            return None

    def record(self, row, group):
        """
        Returns a Record refered by row and group parameters

        :param row:
        :type row: int
        :param group:
        :type group: int
        :return:
        """
        if not group:
            return None
        # We ensure the group has been loaded by checking if there
        # are any fields. modelByIndex loads on demand, but it means
        # two reads to the server. So with these two lines (addFields)
        # we only have performance gains they can be removed with
        # the only drawback that the server will be queried twice.
        if not group.fields:
            group.addFields(self.fields)
        if row >= group.count():
            return None
        else:
            return group.modelByIndex(row)

    def value(self, row, column, group):
        """
        Returns the value from the model from the given row, column and group

        :param row:
        :param column:
        :param group: is usually obtained from the internalPointer() of a QModelIndex.
        :return:
        """
        # We ensure the group has been loaded by checking if there
        # are any fields
        if not group.fields:
            group.addFields( self.fields)
        model = self.record(row, group)
        field = self.field(column)
        if not field or not model or not field in self.fields:
            return None
        else:
            return model.value(field)

    def setValue(self, value, row, column, group):
        # We ensure the group has been loaded by checking if there
        # are any fields
        if not group.fields:
            group.addFields( self.fields )
        model = self.record(row, group)
        field = self.field(column)
        if field and model:
            model.setValue( field, value )


    def valueByName(self, row, field, group):
        # We ensure the group has been loaded by checking if there
        # are any fields
        if not group.fields:
            group.addFields( self.fields )

        model = self.record( row, group )
        if not model:
            return None
        else:
            return model.value( field )

    def id(self, index):
        """
        Returns the id of the model pointed by index.

        :param index: The index can point to any field of the model.
        :return:
        """
        model = self.record( index.row(), index.internalPointer() )
        if model:
            return model.id
        else:
            return -1

    def indexFromId(self, id):
        """
        Returns a QModelIndex pointing to the first field of a given
        record id

        :param id:
        :return:
        """
        if not self.group:
            return QModelIndex()

        row = self.group.indexOfId( id )
        if row >= 0:
            return self.index( row, 0 )
        return QModelIndex()

    def recordFromIndex(self, index):
        return self.record(index.row(), index.internalPointer())

    def indexFromRecord(self, record):
        """
        Returns a QModelIndex pointing to the first field of a given record
        :param record:
        :return:
        """
        if not self.group:
            return QModelIndex()
        row = self.group.indexOfRecord( record )
        if row >= 0:
            return self.index( row, 0 )
        return QModelIndex()


class KooGroupedModel( QAbstractProxyModel ):
    def __getattr__(self, name):
        if name == 'group':
            return self.sourceModel().group
        return QAbstractProxyModel.__getattr__(name)

    def __setattr__(self, name, value):
        if name == 'group':
            self.sourceModel().group = value
            return
        return QAbstractProxyModel.__setattr__(self, name, value)

    def setSourceModel(self, model):
        QAbstractProxyModel.setSourceModel(self, model)
        self.group = model.group

    def mapFromSource(self, index):
        model = self.sourceModel()
        newRow = 0
        previous = False
        for y in range(0, index.row()):
            value = model.value(y, 0, self.group)
            if value != previous:
                newRow += 1
                previous = value
        return self.createIndex(newRow, index.column())

    def mapToSource(self, index):
        model = self.sourceModel()
        previous = None
        newRow = 0
        for y in range(0, self.group.count()):
            value = model.value(y, 0, self.group)
            if value != previous:
                newRow += 1
                if newRow == index.row():
                    break
        return self.createIndex(y, index.column())

    def recordGroup(self):
        return self.sourceModel().recordGroup()

    def setRecordGroup(self, recordGroup):
        return self.sourceModel().setRecordGroup(recordGroup)

    def isReadOnly(self):
        return self.sourceModel().isReadOnly()

    def rowCount(self, parent=QModelIndex()):
        model = self.sourceModel()
        newRow = 0
        previous = None
        for y in range(0, self.group.count()):
            value = model.value(y, 0, self.group)
            if value != previous:
                newRow += 1
        return newRow

    def columnCount(self, parent=QModelIndex()):
        return self.sourceModel().columnCount(parent)

    def index(self, row, column, parent=QModelIndex()):
        return self.createIndex(row, column, parent)

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
