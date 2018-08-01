##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
# Copyright (c) 2007-2009 Albert Cervera i Areny <albert@nan-tic.com>
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

from .SearchDialog import *
from .ExportDialog import *
from .ImportDialog import *
from .AttachmentDialog import *
from .GoToIdDialog import *
from .BatchUpdateDialog import *
from .BatchInsertDialog import *

from Koo.Common import Help

from Koo.Screen.Screen import *
from Koo.Model.Group import RecordGroup
from PyQt5.QtCore import *
from Koo.Common.Ui import *
from gettext import gettext as _

try:
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView
    isHelpWidgetAvailable = True
except:
    isHelpWidgetAvailable = False

(FormWidgetUi, FormWidgetBase) = loadUiType(Common.uiPath('formcontainer.ui'))


class FormWidget(QWidget, FormWidgetUi):

    closed = pyqtSignal()
    shortcutsChanged = pyqtSignal()

    def __init__(self, model, res_id=False, domain=None, view_type=None,
                 view_ids=None, context=None, parent=None, name=False):
        """
        Class constructor

        :param model: Name of the model the form should handle
        :param res_id: List of ids of type 'model' to load
        :param domain: Domain the models should be in
        :param view_type: type of view: form, tree, graph, calendar, ...
        :param view_ids: Id's of the views 'ir.ui.view' to show
        :param context: Context for the current data set
        :param parent: Parent widget of the form
        :param name: User visible title of the form
        """
        QWidget.__init__(self, parent)
        FormWidgetUi.__init__(self)
        self.setupUi(self)

        if domain is None:
            domain = []
        if view_ids is None:
            view_ids = []
        if context is None:
            context = {}

        # This variable holds the id used to update status (and show number of
        # attachments)
        # If it doesn't change we won't update the number of attachments,
        # avoiding some server calls.
        self.previousId = False
        self.previousAttachments = False

        # Workaround: In some cases (detected in some CRM actions) view_type
        # and view_ids may contain duplicate entries. Here we remove duplicates
        # (ensuring lists order is kept).
        if view_type:
            new_view_ids = []
            new_view_type = []
            for i in range(len(view_type)):
                if not view_type[i] in new_view_type:
                    if i < len(view_ids):
                        new_view_ids.append(view_ids[i])
                    new_view_type.append(view_type[i])
            view_ids = new_view_ids
            view_type = new_view_type

        if not view_type:
            view_type = ['form', 'tree']
        else:
            if view_type[0] in ['graph'] and not res_id:
                res_id = Rpc.session.execute(
                    '/object', 'execute', model, 'search', domain)
        fields = {}
        self.model = model
        self.previousAction = None
        self.fields = fields
        self.domain = domain
        self.context = context
        self.viewTypes = view_type
        self.viewIds = view_ids

        self._switchViewMenu = QMenu(self)
        self._viewActionGroup = QActionGroup(self)
        self._viewActionGroup.setExclusive(True)
        for view in self.viewTypes:
            action = ViewFactory.viewAction(view, self)
            if not action:
                continue
            action.triggered.connect(self.switchView)
            self._switchViewMenu.addAction(action)
            self._viewActionGroup.addAction(action)

        self.group = RecordGroup(self.model, context=self.context)
        if Settings.value('koo.sort_mode') == 'visible_items':
            self.group.setSortMode(RecordGroup.SortVisibleItems)
        self.group.setDomain(domain)
        self.group.modified.connect(self.notifyRecordModified)

        self.screen.setRecordGroup(self.group)
        self.screen.setEmbedded(False)
        self.screen.activated.connect(self.switchToForm)
        # @xtorello toreview not-clear signal<->slot
        self.screen.currentChangedSignal.connect(self.updateStatus)
        self.screen.closed.connect(self.closeWidget)
        self.screen.recordMessage[int, int, int].connect(self.updateRecordStatus)
        self.screen.statusMessage['QString'].connect(self.updateStatus)

        self._allowOpenInNewWindow = True

        # Remove ids with False value
        self.screen.setupViews(view_type, view_ids)

        if name:
            self.name = name
        else:
            self.name = self.screen.currentView().title

        self.handlers = {
            'New': self.new,
            'Save': self.save,
            'Export': self.export,
            'Import': self.import_,
            'Delete': self.remove,
            'Find': self.search,
            'Previous': self.previous,
            'Next':  self.__next__,
            'GoToResourceId':  self.goto,
            'AccessLog':  self.showLogs,
            'Reload': self.reload,
            'Switch': self.switchView,
            'Attach': self.showAttachments,
            'Duplicate': self.duplicate,
            'BatchInsert': self.batchInsert,
            'BatchUpdate': self.batchUpdate,
            'BatchButton': self.batchButton,
            'BatchUpdateField': self.batchUpdateField,
            'StoreViewSettings': self.storeViewSettings,
        }

        if res_id:
            if isinstance(res_id, int):
                res_id = [res_id]
            self.screen.load(res_id)
        else:
            if len(view_type) and view_type[0] == 'form':
                self.screen.new()

        self.updateSwitchView()

        self.reloadTimer = QTimer(self)
        self.reloadTimer.timeout.connect(self.autoReload)
        self.pendingReload = False

        # We always use the Subscriber as the class itself will handle
        # whether the module exists on the server or not
        self.subscriber = Rpc.Subscriber(Rpc.session, self)
        if Settings.value('koo.auto_reload'):
            self.subscriber.subscribe(
                'updated_model:%s' % model, self.autoReload)

    def save(self):
        pass

    def cancel(self):
        pass

    def notifyRecordModified(self):
        self.updateStatus(_('<font color="blue">Document modified</font>'))


    def setAutoReload(self, value):
        """
        Establishes that every value seconds a reload should be scheduled.
        If value is < 0 only Subscription based reloads are executed. Note
        that if value is != 0 Subscription based reloads are always used if
        available.
        :param value:
        :return: None
        :rtype: None
        """
        if value:
            # We use both, timer and subscriber as in some cases information
            # may change only virtually: Say change the color of a row
            # depending on current time.
            # If the value is negative we don't start the timer but keep
            # subscription, so this allows setting -1 in autorefresh when you
            # don't want timed updates but only when data is changed in the
            # server.
            if value > 0:
                self.reloadTimer.start(int(value) * 1000)
            if not Settings.value('koo.auto_reload'):
                # Do not subscribe again if that was already done in the
                # constructor
                self.subscriber.subscribe(
                    'updated_model:%s' % self.model, self.autoReload)
        else:
            self.reloadTimer.stop()

    def setAllowOpenInNewWindow(self, value):
        self._allowOpenInNewWindow = value

    def goto(self):
        if not self.modifiedSave():
            return
        dialog = GoToIdDialog(self)
        if dialog.exec_() == QDialog.Rejected:
            return
        if not dialog.result in self.group.ids():
            QMessageBox.information(self, _('Go To Id'), _(
                "Resouce with ID '%s' not found.") % dialog.result)
            return
        self.screen.load([dialog.result])

    def setStatusBarVisible(self, value):
        self.uiStatusLabel.setVisible(value)
        self.uiStatus.setVisible(value)
        self.uiRecordStatus.setVisible(value)

    def showAttachments(self):
        id = self.screen.currentId()
        if id:
            if Settings.value('koo.attachments_dialog'):
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    window = AttachmentDialog(self.model, id, self)
                    window.destroyed.connect(self.attachmentsClosed)
                except Rpc.RpcException:
                    QApplication.restoreOverrideCursor()
                    return
                QApplication.restoreOverrideCursor()
                window.show()
            else:
                context = self.context.copy()
                context.update(Rpc.session.context)
                action = Rpc.session.execute(
                    '/object', 'execute', 'ir.attachment', 'action_get',
                    context)
                action['domain'] = [
                    ('res_model', '=', self.model), ('res_id', '=', id)]
                context['default_res_model'] = self.model
                context['default_res_id'] = id
                Api.instance.executeAction(action, {}, context)
        else:
            self.updateStatus(_('No resource selected !'))

    def attachmentsClosed(self):
        self.updateStatus()

    def switchToForm(self):
        if 'form' in self.viewTypes:
            self.switchView('form')
        else:
            self.switchView()

    def switchView(self, viewType=None):
        selectedIds = self.screen.selectedIds()
        if not self.modifiedSave():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if (self._allowOpenInNewWindow and QApplication.keyboardModifiers() & Qt.ControlModifier) == Qt.ControlModifier:
                if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                    target = 'background'
                else:
                    target = 'current'
                for ident in selectedIds:
                    Api.instance.createWindow(
                        None, self.model, [ident],
                        view_type='form', mode='form,tree', target=target)
            else:
                sender = self.sender()
                name = str(sender.objectName())
                if isinstance(sender, QAction) and name != 'actionSwitch':
                    self.sender().setChecked(True)
                    self.screen.switchView(name)
                else:
                    self.screen.switchView(viewType)
            if self.pendingReload:
                self.reload()
            self.updateSwitchView()
        except Rpc.RpcException:
            pass
        QApplication.restoreOverrideCursor()

    def showLogs(self):
        id = self.screen.currentId()
        if not id:
            self.updateStatus(_('You have to select one resource!'))
            return False
        res = Rpc.session.execute(
            '/object', 'execute', self.model, 'perm_read', [id])
        message = ''
        for line in res:
            todo = [
                ('id', _('ID')),
                ('create_uid', _('Creation User')),
                ('create_date', _('Creation Date')),
                ('write_uid', _('Latest Modification by')),
                ('write_date', _('Latest Modification Date')),
            ]
            for (key, val) in todo:
                if line[key] and key in ('create_uid', 'write_uid') and isinstance(line[key], tuple):
                    line[key] = line[key][1]
                message += val + ': ' + str(line[key] or '-') + '\n'
        QMessageBox.information(self, _('Record log'), message)

    def remove(self):
        value = QMessageBox.question(
            self, _('Question'),
            _('Are you sure you want to remove these records?'),
            QMessageBox.Yes | QMessageBox.No)
        if value == 0:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                if not self.screen.remove(unlink=True):
                    self.updateStatus(_('Resource not removed !'))
                else:
                    self.updateStatus(_('Resource removed.'))
            except Rpc.RpcException:
                pass
            QApplication.restoreOverrideCursor()

    def import_(self):
        dialog = ImportDialog(self)
        dialog.setModel(self.model)
        dialog.setup(self.viewTypes, self.viewIds)
        dialog.exec_()
        if not self.screen.isModified():
            self.reload()

    def export(self):
        dialog = ExportDialog(self)
        dialog.setModel(self.model)
        dialog.setIds(self.screen.selectedIds())
        dialog.setup(self.viewTypes, self.viewIds)
        dialog.exec_()

    def new(self):
        if not self.modifiedSave():
            return
        self.screen.new()

    def duplicate(self):
        # Store selected ids before executing modifiedSave() because, there,
        # the selection is lost.
        selectedIds = self.screen.selectedIds()

        if not self.modifiedSave():
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        # Duplicate all selected records but, remember the ID of the copy of the
        # currently selected record
        newId = None
        newIds = []
        currentId = self.screen.currentId()
        for ident in selectedIds:
            copyId = Rpc.session.execute(
                '/object', 'execute', self.model, 'copy', ident, {},
                Rpc.session.context)
            newIds.append(copyId)
            if ident == currentId:
                newId = copyId

        # Ensure the copy of the currently selected ID is the first of the list
        # so it will be the current one, once loaded by screen.
        if newId in newIds:
            newIds.remove(newId)
            newIds.insert(0, newId)

        self.screen.load(newIds, self.screen.addOnTop())
        self.updateStatus(
            _('<font color="orange">Working now on the duplicated document</font>'))
        QApplication.restoreOverrideCursor()

    def save(self):
        """
        Save action

        :return:
        :rtype: None or boolean
        """
        if not self.screen.currentRecord():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            modification = self.screen.currentRecord().id
            ident = self.screen.save()
            if ident:
                self.updateStatus(
                    _('<font color="green">Document saved</font>'))
                if not modification and Settings.value('koo.auto_new'):
                    self.screen.new()
                QApplication.restoreOverrideCursor()
            else:
                self.updateStatus(_('<font color="red">Invalid form</font>'))

                QApplication.restoreOverrideCursor()
                record = self.screen.currentRecord()
                fields = []
                for field in record.invalidFields:
                    attrs = record.fields()[field].attrs
                    if 'string' in attrs:
                        name = attrs['string']
                    else:
                        name = field
                    fields.append('<li>{}</li>'.format(name))
                fields.sort()
                fields = '<ul>{}</ul>'.format(''.join(fields))
                mesage = _('<p>The following fields have an invalid value and have been highlighted in red:</p>{}<p>Please fix them before saving.</p>')
                QMessageBox.question(
                    self,
                    _('Error'),
                    mesage.format(fields),
                    QMessageBox.Ok)
        except Rpc.RpcException:
            QApplication.restoreOverrideCursor()
            ident = False
        return bool(ident)

    def previous(self):
        if not self.modifiedSave():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.screen.displayPrevious()
            self.updateStatus()
        except Rpc.RpcException:
            pass
        QApplication.restoreOverrideCursor()

    def __next__(self):
        if not self.modifiedSave():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.screen.displayNext()
            self.updateStatus()
        except Rpc.RpcException as e:
            pass
        QApplication.restoreOverrideCursor()

    def autoReload(self):
        # Do not reload automatically if it's an editable list
        # By explicitly disallowing this it makes the global
        # koo module auto_reload option to be usable.
        if self.screen.currentView().showsMultipleRecords() and \
                not self.screen.currentView().isReadOnly():
            return
        # Do not reload automatically if there are any modified records
        # However, we take note that there's a pending reload which
        # will be done in the next switchView()
        if self.screen.isModified():
            self.pendingReload = True
            return
        self.reload()
        # If current view only shows one record self.screen.reload()
        # only reloads the current record. As we want to be sure that
        # any new records will appear in the list view (or any view that
        # shows multiple records), we set pendingReload to be run
        # when switching view.
        if not self.screen.currentView().showsMultipleRecords():
            self.pendingReload = True

    def reload(self):
        if not self.modifiedSave():
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # Ensure attachments are updated by initializing previousId
            self.previousId = False
            self.screen.reload()
            self.updateStatus()
            self.pendingReload = False
        except Rpc.RpcException:
            pass
        QApplication.restoreOverrideCursor()

    def cancel(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.screen.cancel()
            self.updateStatus()
        except Rpc.RpcException:
            pass
        QApplication.restoreOverrideCursor()

    def search(self):
        if not self.modifiedSave():
            return
        dom = self.domain
        dialog = SearchDialog(self.model, domain=self.domain,
                              context=self.context, parent=self)
        if dialog.exec_() == QDialog.Rejected:
            return
        self.screen.clear()
        self.screen.load(dialog.result)

    def updateStatus(self, message=''):
        """
        Updates the status message of the form (bottom right)

        :param message: Message
        :return: None
        :rtype: None
        """
        if self.model and \
                self.screen.currentRecord() and \
                self.screen.currentRecord().id:
            # We don't need to query the server for the number of attachments
            # if current record has not changed since list update.
            ident = self.screen.currentRecord().id
            if ident != self.previousId:
                ids = Rpc.session.execute(
                    '/object', 'execute', 'ir.attachment', 'search',
                    [('res_model', '=', self.model), ('res_id', '=', ident)]
                )
                self.previousAttachments = ids
                self.previousId = ident
            else:
                ids = self.previousAttachments
        else:
            ids = []
            self.previousId = False
            self.previousAttachments = ids
        message = (_("({} attachments) ").format(len(ids))) + str(message)
        self.uiStatus.setText(message)

    def updateSwitchView(self):
        for action in self._viewActionGroup.actions():
            if action.objectName() == self.screen.currentView().viewType():
                action.setChecked(True)
                break

    def updateRecordStatus(self, position, count, value):
        if not count:
            msg = _('No records')
        else:
            pos = '_'
            if position >= 0:
                pos = str(position + 1)
            if value is None:
                # Value will be None only when it's called by the constructor
                edit = _('No document selected')
            else:
                # Other times it'll either be 0 (new document) or the appropiate
                # object i
                edit = _('New document')
                if value > 0:
                    edit = _('Editing document (id: %s)') % str(value)
            msg = _('Record: %(name)s / %(count)s - %(name2)s') % {
                'name': pos, 'count': str(count), 'name2': edit}

        self.uiRecordStatus.setText(msg)

    def modifiedSave(self):
        if self.screen.isModified():
            record = self.screen.currentRecord()
            fields = []
            for field in record.modifiedFields():
                attrs = record.fields()[field].attrs
                if 'string' in attrs:
                    name = attrs['string']
                else:
                    name = field
                fields.append('<li>%s</li>' % name)
            fields.sort()
            fields = '<ul>%s</ul>' % ''.join(fields)
            value = QMessageBox.question(
                self, _('Question'),
                _('<p>You have modified the following fields in current record:</p>%s<p>Do you want to save the changes?</p>') % fields,
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if value == 0:
                return self.save()
            elif value == 1:
                self.cancel()
                return True
            else:
                return False
        else:
            # If a new record was created but not modified, isModified()
            # will return False but we want to cancel new records anyway.
            # We call screen.cancel() directly as we don't want to trigger
            # an updateStatus() which will result in a server request.
            self.screen.cancel()
        return True

    def batchInsert(self):
        dialog = BatchInsertDialog(self)
        dialog.setModel(self.model)
        dialog.setContext(self.context)
        dialog.setViewTypes(self.viewTypes)
        dialog.setViewIds(self.viewIds)
        dialog.setup()
        if dialog.exec_() == QDialog.Rejected:
            return
        self.reload()

    def batchUpdate(self):
        if not self.screen.selectedIds():
            QMessageBox.information(
                self, _('No records selected'), _('No records selected'))
            return
        dialog = BatchUpdateDialog(self)
        dialog.setIds(self.screen.selectedIds())
        dialog.setModel(self.model)
        dialog.setContext(self.context)
        dialog.setup(self.viewTypes, self.viewIds)
        if dialog.exec_() == QDialog.Rejected:
            return
        self.reload()

    def batchUpdateField(self):
        dialog = BatchInsertDialog(self)
        dialog.setModel(self.model)
        dialog.setContext(self.context)
        dialog.setUpdateOnServer(False)
        dialog.setViewTypes(self.viewTypes)
        dialog.setViewIds(self.viewIds)
        dialog.setup()
        if dialog.exec_() == QDialog.Rejected:
            return

        if len(dialog.newValues) != len(self.screen.selectedRecords()):
            QMessageBox.warning(
                self,
                _('Batch Field Update'),
                _('The number of selected records (%(records)d) does not match the number of records to be inserted in fields (%(fields)d).') % {
                    'records': len(dialog.newValues),
                    'fields': len(self.screen.selectedRecords())
            })
            return

        i = 0
        for record in self.screen.selectedRecords():
            record.setValue(dialog.newField, dialog.newValues[i])
            i += 1
        self.save()
        self.reload()

    def storeViewSettings(self):
        self.screen.storeViewSettings()

    def closeWidget(self):
        self.screen.storeViewSettings()
        self.reloadTimer.stop()
        self.subscriber.unsubscribe()
        self.closed.emit()

    def canClose(self, urgent=False):
        if self.modifiedSave():
            # Here suppose that if we return True the form/tab will
            # actually be closed, so stop reload timer so it doesn't
            # remain active if the object is freed.
            self.reloadTimer.stop()
            self.subscriber.unsubscribe()
            # Store settings of all opened views before closing the tab.
            self.screen.storeViewSettings()
            return True
        else:
            return False

    def actions(self):
        return self.screen.actions

    def switchViewMenu(self):
        return self._switchViewMenu

    def help(self, button):
        if not isHelpWidgetAvailable:
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        helpWidget = Help.HelpWidget(button)
        helpWidget.setLabel(self.name)
        helpWidget.setType(helpWidget.ViewType)
        helpWidget.setFilter(
            (self.model, self.screen.currentView().viewType()))
        helpWidget.show()
        QApplication.restoreOverrideCursor()

    def __del__(self):
        self.group.__del__()
        del self.group

    def batchButton(self):
        viewTypes = self.viewTypes
        viewIds = self.viewIds

        group = RecordGroup(self.model, context=self.context)
        group.setDomainForEmptyGroup()
        group.load(self.screen.selectedIds())

        screen = Screen(self)
        screen.setRecordGroup(self.group)
        screen.setEmbedded(True)
        if 'form' in viewTypes:
            queue = ViewQueue()
            queue.setup(viewTypes, viewIds)
            type = ''
            while type != 'form':
                ident, type = next(queue)
            screen.setupViews(['form'], [ident])
        else:
            screen.setupViews(['form'], [False])

        from Koo.Fields.Button import ButtonFieldWidget
        from Koo.Common import Common

        buttons = {}
        for key, widget in screen.currentView().widgets.items():
            if isinstance(widget, ButtonFieldWidget):
                buttons[str(widget.button.text())] = widget.name

        selectionDialog = Common.SelectionDialog(
            _('Choose action to apply to selected records'), buttons, self)
        if selectionDialog.exec_() == QDialog.Rejected:
            return

        buttonString = selectionDialog.result[0]
        buttonName = selectionDialog.result[1]

        if QMessageBox.question(
                self, _("Batch Update"),
                _("Do you really want to push button '%s' of all selected records?") % buttonString,
                QMessageBox.Yes|QMessageBox.No
        ) == 1:
            return

        for ident in self.screen.selectedIds():
            screen.display(ident)
            screen.currentView().widgets[buttonName].executeButton(screen, ident)

        self.reload()

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
