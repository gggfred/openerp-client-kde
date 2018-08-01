##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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

from Koo.Common import Common
from PyQt5.QtWidgets import *
from Koo.Fields.AbstractFieldWidget import *
from Koo.Fields.AbstractFieldDelegate import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class SelectionFieldWidget(AbstractFieldWidget):
    def __init__(self, parent, view, attrs={}):
        AbstractFieldWidget.__init__(self, parent, view, attrs)

        self.widget = QComboBox(self)
        self.widget.setFrame(True)
        self.widget.setEditable(True)
        self.widget.setInsertPolicy(QComboBox.NoInsert)
        self.widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # As there's no sense in this widget to handle focus
        # we set QComboBox as the proxy widget. Without this
        # editable lists don't work properly.
        self.setFocusProxy(self.widget)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget)

        self._changed = False

        self.installPopupMenu(self.widget)

        self.widget.activated[int].connect(self.activated)
        self.widget.editTextChanged['QString'].connect(self.changed)
        self.fill(attrs.get('selection') or [])

    def fill(self, selection):
        for (identifier, name) in selection:
            self.widget.addItem(name, identifier)

    def setReadOnly(self, value):
        AbstractFieldWidget.setReadOnly(self, value)
        self.widget.setEnabled(not value)

    def changed(self, text):
        self._changed = True

    def value(self):
        if not self._changed:
            return self.record.value(self.name)

        # If we checked with MatchContains directly, we might find incorrect values when
        # the user clicked the item instead of writting it.

        # @xtorello toreview
        value = self.widget.itemData(
            self.widget.findText(
                self.widget.currentText(),
                Qt.MatchExactly | Qt.MatchCaseSensitive,
            ),
        )

        if not value:
            value = self.widget.itemData(
                self.widget.findText(self.widget.currentText(), Qt.MatchExactly),
            )

        if not value:
            value = self.widget.itemData(
                self.widget.findText(self.widget.currentText(), Qt.MatchContains),
            )

        if value:
            return value
        else:
            return False

    def storeValue(self):
        self.record.setValue(self.name, self.value())

    def clear(self):
        self.widget.setCurrentIndex(self.widget.findText(''))

    def showValue(self):
        value = self.record.value(self.name)
        if not value:
            self.widget.setCurrentIndex(self.widget.findText(''))
        else:
            self.widget.setCurrentIndex(self.widget.findData(QVariant(value)))
        self._changed = False

    def activated(self, idx):
        self.store()

    def colorWidget(self):
        return self.widget


class SelectionFieldDelegate(AbstractFieldDelegate):
    def createEditor(self, parent, option, index):
        widget = QComboBox(parent)
        widget.setEditable(False)
        widget.setInsertPolicy(QComboBox.InsertAtTop)
        for (ident, name) in self.attributes.get('selection', []):
            widget.addItem(name, QVariant(ident))
        return widget

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        editor.setCurrentIndex(editor.findText(value))

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.currentText()), Qt.EditRole)

    # def sizeHint(self, option, index):
    #	return QSize(30, 30)
