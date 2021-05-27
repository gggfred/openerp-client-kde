##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#					Fabien Pinckaers <fp@tiny.Be>
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

import gettext
from PyQt5.QtWidgets import *
import re
from Koo.Common import Common
from Koo.Common import Numeric
from Koo.Common import Api
from Koo.Common.Settings import *

from Koo import Rpc
from Koo.Model.Group import RecordGroup

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from Koo.Common.Ui import *

try:
    from PyQt5.QtWebKit import *
    from PyQt5.QtNetwork import *
    isWebKitAvailable = True
except:
    isWebKitAvailable = False


if isWebKitAvailable:
    (FullTextSearchDialogUi, FullTextSearchDialogBase) = loadUiType(
        Common.uiPath('full_text_search.ui'))

    # @brief The FullTextSearchDialog class shows a dialog for searching text at all indexed models.
    #
    # The dialog has a text box for the user input and a combo box to search at one specific
    # model or all models that have at least one field indexed.
    class FullTextSearchDialog(QDialog, FullTextSearchDialogUi):
        def __init__(self, parent=None):
            QDialog.__init__(self, parent)
            FullTextSearchDialogUi.__init__(self)
            self.setupUi(self)

            self.setModal(True)

            self.result = None

            self.setQueriesEnabled(False, _('Loading...'))

            self.title = _('Full Text Search')
            self.title_results = _('Full Text Search (%%d result(s))')

            self.setWindowTitle(self.title)
            self.uiWeb.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
            self.uiWeb.linkClicked[QUrl].connect(self.open)

            self.shortcuts = {}
            self.related = []
            self.limit = 10
            self.offset = 0
            self.queryThreads = []
            self.pushNext.setEnabled(False)
            self.pushPrevious.setEnabled(False)

            self.uiHelp.linkActivated['QString'].connect(self.showHelp)
            self.pushClose.clicked.connect(self.accept)
            self.pushFind.clicked.connect(self.find)
            self.pushPrevious.clicked.connect(self.previous)
            self.pushNext.clicked.connect(self.__next__)
            self.accept.connect(self.accepted)
            if Settings.value('koo.fts_instant', True):
                self.uiText.textEdited['QString'].connect(self.find)
            self.show()

            QApplication.setOverrideCursor(Qt.WaitCursor)
            QTimer.singleShot(0, self.initGui)

        def accepted(self):
            for thread in self.queryThreads:
                thread.terminate()
                thread.wait()

        def showHelp(self, link):
            QApplication.postEvent(self.sender(), QEvent(QEvent.WhatsThis))

        def initGui(self):
            try:
                answer = Rpc.session.call(
                    '/fulltextsearch', 'indexedModels', Rpc.session.context)
                self.uiModel.addItem(_('(Everywhere)'), QVariant(False))
                for x in answer:
                    self.uiModel.addItem(x['name'], QVariant(x['id']))
                if len(answer) == 0:
                    self.setQueriesEnabled(False, _(
                        '<b>Full text search is not configured.</b><br/>Go to <i>Administration - Configuration - Full Text Search - Indexes</i>. Then add the fields you want to be indexed and finally use <i>Update Full Text Search</i>.'))
                    QApplication.restoreOverrideCursor()
                    return
            except:
                self.setQueriesEnabled(False, _(
                    '<b>Full text search module not installed.</b><br/>Go to <i>Administration - Modules administration - Uninstalled Modules</i> and add the <i>full_text_search</i> module.'))
                QApplication.restoreOverrideCursor()
                return
            self.setQueriesEnabled(True)
            self.uiText.setFocus()
            if QApplication.keyboardModifiers() & Qt.AltModifier:
                clipboard = QApplication.clipboard()
                if clipboard.supportsFindBuffer():
                    text = clipboard.text(QClipboard.FindBuffer)
                elif clipboard.supportsSelection():
                    text = clipboard.text(QClipboard.Selection)
                else:
                    text = clipboard.text(QClipboard.Clipboard)
                self.uiText.setText(text)
                self.find()
            QApplication.restoreOverrideCursor()

        def setQueriesEnabled(self, value, text=''):
            self.uiModel.setEnabled(value)
            self.pushFind.setEnabled(value)
            self.uiText.setEnabled(value)
            self.uiWeb.page().mainFrame().setHtml(
                "<span style='font-size: large'>%s</span>" % text)

        def textToQuery(self):
            q = str(self.uiText.text()).strip()
            return re.sub(' +', '|', q)

        def query(self):
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if self.uiModel.currentIndex() == 0:
                model = False
            else:
                model = str(self.uiModel.itemData(
                    self.uiModel.currentIndex()).toString())

            # We always query for limit+1 items so we can know if there will be more records in the next page
            thread = Rpc.session.executeAsync(self.showResults, '/fulltextsearch', 'search',
                                              self.textToQuery(), self.limit + 1, self.offset, model, Rpc.session.context)
            self.queryThreads.append(thread)

            QApplication.restoreOverrideCursor()

        def showResults(self, answer, exception):
            if exception or not answer:
                answer = []
            if len(answer) < self.limit:
                self.pushNext.setEnabled(False)
            else:
                # If there are more pages, we just show 'limit' items.
                answer = answer[:-1]
                self.pushNext.setEnabled(True)
            if self.offset == 0:
                self.pushPrevious.setEnabled(False)
            else:
                self.pushPrevious.setEnabled(True)
            self.resultsToHtml(answer)

        def resultsToHtml(self, answer):
            for shortcut in list(self.shortcuts.keys()):
                shortcut.setParent(None)
            self.shortcuts = {}
            number = 1
            page = ''
            for item in answer:
                # Prepare relations
                related = Rpc.session.execute('/object', 'execute', 'ir.values', 'get', 'action',
                                              'client_action_relate', [(item['model_name'], False)], False, Rpc.session.context)
                actions = [x[2] for x in related]
                block = []
                related = ''
                for action in actions:
                    def f(action): return lambda: self.executeRelation(action)
                    action['model_name'] = item['model_name']
                    self.related.append(action)
                    block.append("<a href='relate/%d/%d'>%s</a>" %
                                 (len(self.related) - 1, item['id'], action['name']))
                    if len(block) == 3:
                        related += '<div style="padding-left: 40px">%s</div>' % ' - '.join(
                            block)
                        block = []
                if block:
                    related += '<div style="padding-left: 40px">%s</div>' % ' - '.join(
                        block)

                if related:
                    related = '<div style="padding-top: 5px">%s</div>' % related

                # Prepare URL
                url = 'open/%s/%s' % (item['model_name'], item['id'])

                # Prepare Shortcut
                # TODO: Implement shortcuts
                if number <= 10:
                    self.shortcut = QShortcut(self)
                    self.shortcut.setKey('Ctrl+%s' % number)
                    self.shortcut.setContext(Qt.WidgetWithChildrenShortcut)
                    self.shortcut.activated.connect(self.openShortcut)
                    self.shortcuts[self.shortcut] = url
                    shortcut = ' - <span style="color: green; font-size: medium">[Ctrl+%d]</span>' % (
                        number % 10)
                else:
                    shortcut = ''
                number += 1

                # Prepare Item
                page += """
					<div style="padding: 5px; font-size: large">
					<a href="%(url)s">%(model_label)s: %(name)s</a> &nbsp;%(shortcut)s - <span style="font-size: medium">[ %(ranking).2f ]</span></a>
					<div style="font-size: medium">%(headline)s</div>
					<div style="font-size: medium">%(related)s</div>
					</div>""" % {
                        'url': url,
                        'model_label': item['model_label'],
                        'name': item['name'],
                        'shortcut': shortcut,
                        'ranking': item['ranking'],
                        'headline': item['headline'],
                        'related': related,
                }

            page = '<html>%s</html>' % page
            self.uiWeb.page().mainFrame().setHtml(page)
            #self.serverOrder = ['id', 'model_id', 'model_name', 'model_label', 'name', 'headline', 'ranking']

        def previous(self):
            self.offset = max(0, self.offset - self.limit)
            self.query()

        def __next__(self):
            self.offset = self.offset + self.limit
            self.query()

        def find(self):
            self.offset = 0
            self.query()

        def openShortcut(self):
            self.open(self.shortcuts[self.sender()])

        def open(self, url):
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if isinstance(url, QUrl):
                url = str(url.toString())
            url = url.split('/')
            if url[0] == 'open':
                model = url[1]
                id = int(url[2])

                if model == 'ir.ui.menu':
                    Api.instance.executeKeyword('tree_but_open', {
                        'model': model,
                        'id': id,
                        'report_type': 'pdf',
                        'ids': [id]
                    }, Rpc.session.context)
                else:
                    if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                        target = 'background'
                    else:
                        target = 'current'
                    Api.instance.createWindow(
                        None, model, id, view_type='form', mode='form,tree', target=target)
            elif url[0] == 'relate':
                action = int(url[1])
                id = int(url[2])
                self.executeRelation(self.related[action], id)
            QApplication.restoreOverrideCursor()

            if QApplication.keyboardModifiers() & Qt.ControlModifier:
                # If user is pressing Control do not close current dialog
                return
            self.accept()

        def executeRelation(self, action, id):
            group = RecordGroup(action['model_name'])
            group.load([id])
            record = group.modelByIndex(0)
            action['domain'] = record.evaluateExpression(
                action['domain'], checkLoad=False)
            action['context'] = str(record.evaluateExpression(
                action['context'], checkLoad=False))
            Api.instance.executeAction(action)

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
