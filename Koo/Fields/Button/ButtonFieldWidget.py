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
from Koo.Fields.AbstractFieldWidget import *
from Koo.Fields.AbstractFieldDelegate import *
from Koo.Common import Api
from Koo.Common import Notifier
from Koo.Common import Icons
from Koo.Common import Common
from Koo.Common import Api
from Koo.Rpc import Rpc
import sys


class ButtonFieldWidget(AbstractFieldWidget):
    def __init__(self, parent, view, attributes):
        AbstractFieldWidget.__init__(self, parent, view, attributes)

        self.button = QPushButton(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)

        self.button.setText(Common.normalizeLabel(
            attributes.get('string', 'unknown')))
        if 'icon' in attributes:
            self.button.setIcon(Icons.kdeIcon(attributes['icon']))

        self.button.clicked.connect(self.click)

    def addShortcut(self, keys):
        if not keys:
            return
        shortcut = QShortcut(QKeySequence(keys), self)
        shortcut.activated.connect(self.button.click)

    def executeButton(self, screen, id):
        type = self.attrs.get('type', 'workflow')
        if type == 'workflow':
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                # TODO: Uncomment when our patch will be applied in the server
                #result = Rpc.session.execute('/object', 'exec_workflow', screen.name, self.name, id, self.record.context())
                result = Rpc.session.execute(
                    '/object', 'exec_workflow', screen.name, self.name, id)
                if isinstance(result, dict):
                    if result['type'] == 'ir.actions.act_window_close':
                        screen.close()
                    else:
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.setOverrideCursor(Qt.ArrowCursor)
                        Api.instance.executeAction(result, {'ids': [id]})
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.restoreOverrideCursor()

                elif isinstance(result, list):
                    for r in result:
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.setOverrideCursor(Qt.ArrowCursor)
                        Api.instance.executeAction(r, {'ids': [id]})
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.restoreOverrideCursor()
            except Rpc.RpcException as e:
                pass
            QApplication.restoreOverrideCursor()
        elif type == 'object':
            if not id:
                return
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                result = Rpc.session.execute(
                    '/object', 'execute', screen.name, self.name, [id], self.record.context())
            except Rpc.RpcException as err:
                QApplication.restoreOverrideCursor()
                title = err.__class__.__name__
                msg = err.code
                details = err.backtrace
                Notifier.notifyError(title, msg, details)
                return
            QApplication.restoreOverrideCursor()
            if isinstance(result, dict):
                screen.close()
                datas = {
                    'ids': [id],
                    'model': screen.name,
                }
                Api.instance.executeAction(result, datas, screen.context)

        elif type == 'action':
            action_id = int(self.attrs['name'])
            Api.instance.execute(action_id, {'model': screen.name, 'id': id, 'ids': [
                                 id]}, context=screen.context)
        else:
            Notifier.notifyError(_('Error in Button'), _(
                'Button type not allowed'), _('Button type not allowed'))

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            screen.reload()
        except Rpc.RpcException as e:
            pass
        QApplication.restoreOverrideCursor()

    def click(self):
        if not self.record:
            return

        # TODO: Remove screen dependency and thus ViewForm.screen
        screen = self.view.screen
        self.view.store()
        if self.attrs.get('special', '') == 'quit':
            sys.exit(0)
        if self.attrs.get('special', '') == 'cancel':
            screen.close()
            if 'name' in list(self.attrs.keys()):
                result = Rpc.session.execute(
                    '/object', 'execute', screen.name,
                    self.attrs['name'], [], self.record.context()
                )
                datas = {}
                Api.instance.executeAction(result, datas, screen.context)
            return

        if self.record.validate():
            id = screen.save()
            if not self.attrs.get('confirm', False) or \
                    QMessageBox.question(self, _('Question'), self.attrs['confirm'], _("Yes"), _("No")) == 0:
                self.executeButton(screen, id)
        else:
            Notifier.notifyWarning('', _('Invalid Form, correct red fields!'))
            screen.display()

    def setReadOnly(self, value):
        AbstractFieldWidget.setReadOnly(self, value)
        if self.attrs.get('readonly', '0') == '1':
            self.button.setEnabled(False)
            self.button.setToolTip(
                _('You do not have permission to execute this action.'))
        else:
            self.button.setEnabled(not value)
            self.button.setToolTip('')

    def showValue(self):
        if not self.attrs.get('states', False):
            self.show()
            return

        state = 'draft'
        if self.record and self.record.fieldExists('state'):
            state = self.record.value('state')
        states = self.attrs.get('states', '').split(',')
        if state in states:
            self.show()
        else:
            self.hide()


class ButtonFieldDelegate(AbstractFieldDelegate):
    def createEditor(self, parent, option, index):
        return None

    def editorEvent(self, event, model, option, index):
        if event.type() != QEvent.MouseButtonPress:
            return AbstractFieldDelegate.editorEvent(self, event, model, option, index)

        record = index.model().recordFromIndex(index)
        if not record:
            return True

        if not self.isEnabled(record):
            return True

        # TODO: Remove screen dependency and thus ViewTree.screen
        view = self.parent().parent()
        screen = self.parent().parent().screen

        screen.setCurrentRecord(record)

        view.store()
        if self.attributes.get('special', '') == 'cancel':
            screen.close()
            if 'name' in list(self.attributes.keys()):
                result = Rpc.session.execute(
                    '/object', 'execute', screen.name,
                    self.attributes['name'], [], record.context()
                )
                datas = {}
                Api.instance.executeAction(result, datas, screen.context)
            return

        if record.validate():
            id = screen.save()
            if not self.attributes.get('confirm', False) or \
                    QMessageBox.question(self, _('Question'), self.attributes['confirm'], _("Yes"), _("No")) == 0:
                self.executeButton(screen, id, record)
        else:
            Notifier.notifyWarning('', _('Invalid Form, correct red fields!'))
            screen.display()
        return True

    def isEnabled(self, record):
        state = 'draft'
        if record and record.fieldExists('state'):
            state = record.value('state')
        states = self.attributes.get('states', '').split(',')
        if state in states:
            return True
        return False

    def executeButton(self, screen, id, record):
        type = self.attributes.get('type', 'workflow')
        if type == 'workflow':
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                # TODO: Uncomment when our patch will be applied in the server
                #result = Rpc.session.execute('/object', 'exec_workflow', screen.name, self.name, id, record.context())
                result = Rpc.session.execute(
                    '/object', 'exec_workflow', screen.name, self.name, id)
                if isinstance(result, dict):
                    if result['type'] == 'ir.actions.act_window_close':
                        screen.close()
                    else:
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.setOverrideCursor(Qt.ArrowCursor)
                        Api.instance.executeAction(result, {'ids': [id]})
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.restoreOverrideCursor()

                elif isinstance(result, list):
                    for r in result:
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.setOverrideCursor(Qt.ArrowCursor)
                        Api.instance.executeAction(r, {'ids': [id]})
                        if result['type'] == 'ir.actions.act_window':
                            QApplication.restoreOverrideCursor()
            except Rpc.RpcException as e:
                pass
            QApplication.restoreOverrideCursor()
        elif type == 'object':
            if not id:
                return
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                result = Rpc.session.execute(
                    '/object', 'execute', screen.name, self.name, [id], record.context())
            except Rpc.RpcException as e:
                QApplication.restoreOverrideCursor()
                return
            QApplication.restoreOverrideCursor()
            if isinstance(result, dict):
                screen.close()
                datas = {
                    'ids': [id],
                    'model': screen.name,
                }
                Api.instance.executeAction(result, datas, screen.context)

        elif type == 'action':
            action_id = int(self.attributes['name'])
            Api.instance.execute(action_id, {'model': screen.name, 'id': id, 'ids': [
                                 id]}, context=screen.context)
        else:
            Notifier.notifyError(_('Error in Button'), _(
                'Button type not allowed'), _('Button type not allowed'))

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            screen.reload()
        except Rpc.RpcException as e:
            pass
        QApplication.restoreOverrideCursor()
