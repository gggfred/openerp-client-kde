#!/usr/bin/python
#############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#					Fabien Pinckaers <fp@tiny.Be>
# Copyright (c) 2007 Angel Alvarez <angel@nan-tic.com>
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


import tempfile
import subprocess

from .PreferencesDialog import *
from .FullTextSearchDialog import *
from .TipOfTheDayDialog import *


from .LoginDialog import *
from .AdministratorPasswordDialog import *

from Koo.Common.Settings import Settings
from Koo.Common import Api
from Koo.Common import ViewSettings
from Koo.Common import RemoteHelp

from Koo.View.ViewFactory import *

from Koo.Plugins import *
from gettext import gettext as _
from PyQt5.uic import loadUi


class MainTabWidget(QTabWidget):
    middleClicked = pyqtSignal(int)

    def __init__(self, parent=None):
        QTabWidget.__init__(self, parent)
        self.pressedAt = -1
        if Common.isQtVersion45():
            self.setMovable(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MidButton:
            self.pressedAt = self.tabBar().tabAt(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MidButton:
            tab = self.tabBar().tabAt(event.pos())
            if tab != self.pressedAt:
                self.pressedAt = -1
                return
            self.middleClicked.emit(tab)

    def wheelEvent(self, event):
        if not self.tabBar().underMouse():
            return
        degrees = event.angleDelta().y() / 8
        steps = degrees / 15
        self.setCurrentIndex((self.currentIndex() + steps) % self.count())


(KooMainWindowUi, KooMainWindowBase) = loadUiType(Common.uiPath('mainwindow.ui'))


class KooMainWindow(QMainWindow, KooMainWindowUi):

    instance = None

    def __init__(self):
        QMainWindow.__init__(self)
        KooMainWindowUi.__init__(self)

        self.menuBar = False

        self.setupUi(self)

        # Initialize singleton
        KooMainWindow.instance = self

        self.fixedWindowTitle = self.windowTitle()

        self.uiServerInformation.setText(_('Press Ctrl+O to login'))

        self.tabWidget = MainTabWidget(self. centralWidget())
        self.tabWidget.currentChanged[int].connect(self.currentChanged)
        self.tabWidget.middleClicked[int].connect(self.closeTab)
        self.tabWidget.tabCloseRequested[int].connect(self.closeTab)

        self.pushClose = QToolButton(self.tabWidget)
        self.pushClose.setIcon(QIcon(':/images/close_tab.png'))
        self.pushClose.setAutoRaise(True)
        self.pushClose.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.pushClose.setToolTip(_('Close tab'))
        self.pushClose.clicked.connect(self.closeCurrentTab)

        self.tabWidget.setCornerWidget(self.pushClose, Qt.TopRightCorner)

        self.layout = self.centralWidget().layout()
        self.layout.setSpacing(2)
        self.layout.addWidget(self.tabWidget)
        self.layout.addWidget(self.frame)

        self.actionFullTextSearch.setShortcuts(['Ctrl+T', 'Ctrl+Alt+T'])

        self.actionClose.triggered.connect(self.closeCurrentTab)
        self.actionConnect.triggered.connect(self.showLoginDialog)
        self.actionDisconnect.triggered.connect(self.logout)
        self.actionSendRequest.triggered.connect(self.newRequest)
        self.actionReadMyRequest.triggered.connect(self.pendingRequests)
        self.actionWaitingRequests.triggered.connect(self.waitingRequests)
        self.actionNewDatabase.triggered.connect(self.createDatabase)
        self.actionExit.triggered.connect(self.close)
        self.actionFullTextSearch.triggered.connect(self.fullTextSearch)
        self.actionNextTab.triggered.connect(self.nextTab)
        self.actionPreviousTab.triggered.connect(self.previousTab)
        self.actionBackupDatabase.triggered.connect(self.backupDatabase)
        self.actionRestoreDatabase.triggered.connect(self.restoreDatabase)
        self.actionDropDatabase.triggered.connect(self.dropDatabase)
        self.actionAdminPassword.triggered.connect(self.changeAdministratorPassword)
        self.actionPreferences.triggered.connect(self.userPreferences)
        self.actionOpenMenuTab.triggered.connect(self.openMenuTab)
        self.actionOpenHomeTab.triggered.connect(self.openHomeTab)
        self.actionClearCache.triggered.connect(self.clearCache)

        self.actionHtmlManual.triggered.connect(self.openHtmlManual)
        self.actionPdfManual.triggered.connect(self.openPdfManual)
        self.actionDocOpenErpCom.triggered.connect(self.openDocOpenErpCom)
        self.actionTips.triggered.connect(self.showTipOfTheDay)
        self.actionShortcuts.triggered.connect(self.showShortcuts)
        self.actionLicense.triggered.connect(self.showLicense)
        self.actionAbout.triggered.connect(self.showAboutDialog)

        self.actionFormDesigner.triggered.connect(self.formDesigner)

        # Connect request buttons
        self.pushReadRequests.clicked.connect(self.pendingRequests)
        self.pushSendRequest.clicked.connect(self.newRequest)

        self.pushHelp.clicked.connect(self.help)

        if Settings.value('koo.enable_batch_update_field'):
            self.actionBatchUpdateField.setVisible(True)

        # These actions are not handled by the Main Window but by the currently opened tab.
        # What we do here, is connect all these actions to a single handler that will
        # call the current child/tab/form. This is handled this way instead of signals because we
        # may have several windows opened at the same time and all children would receive
        # the signal...
        self.actions = [
            'New', 'Save', 'Delete', 'Find', 'Previous', 'Next', 'Reload', 'Switch',
            'Attach', 'Export', 'Import', 'GoToResourceId', 'Duplicate', 'AccessLog',
            'BatchInsert', 'BatchUpdate', 'BatchUpdateField', 'BatchButton', 'StoreViewSettings'
        ]
        for x in self.actions:
            action = eval('self.action' + x)
            action.triggered.connect(self.callChildView)

        self.pushSwitchView = self.uiToolBar.widgetForAction(self.actionSwitch)
        self.pushSwitchView.setPopupMode(QToolButton.MenuButtonPopup)

        self.updateEnabledActions()

        self.shortcutActions = []
        self.shortcutsGroup = None

        # Stores the id of the menu action. This is to avoid opening two menus
        # when 'action_id' returns the same as 'menu_id'
        self.menuId = False

        # Update the number of pending requests in the status bar using a timer but also
        # subscribing to model changes if 'koo' module is installed in the server.
        self.requestsTimer = QTimer()
        self.requestsTimer.timeout.connect(self.updateRequestsStatus)
        self.pendingRequests = -1
        # Subscriber will be used to update requests status too. Only if 'koo' model is installed
        # on the server.
        self.subscriber = None

        # System Tray
        self.actionOpenPartnersTab = QAction(self)
        self.actionOpenPartnersTab.setIcon(QIcon(':/images/partner.png'))
        self.actionOpenPartnersTab.setText(_('Open partners tab'))
        self.actionOpenPartnersTab.triggered.connect(self.openPartnersTab)

        self.actionOpenProductsTab = QAction(self)
        self.actionOpenProductsTab.setIcon(QIcon(':/images/product.png'))
        self.actionOpenProductsTab.setText(_('Open products tab'))
        self.actionOpenProductsTab.triggered.connect(self.openProductsTab)

        self.systemTrayMenu = QMenu()
        self.systemTrayMenu.addAction(self.actionFullTextSearch)
        self.systemTrayMenu.addAction(self.actionOpenPartnersTab)
        self.systemTrayMenu.addAction(self.actionOpenProductsTab)
        self.systemTrayMenu.addAction(self.actionOpenMenuTab)
        self.systemTrayMenu.addSeparator()
        self.systemTrayMenu.addAction(self.actionSendRequest)
        self.systemTrayMenu.addAction(self.actionReadMyRequest)
        self.systemTrayMenu.addAction(self.actionWaitingRequests)
        self.systemTrayMenu.addSeparator()
        self.systemTrayMenu.addAction(self.actionExit)

        self.systemTrayIcon = QSystemTrayIcon(self)
        self.systemTrayIcon.setIcon(QIcon(":/images/koo-icon.png"))
        self.systemTrayIcon.setContextMenu(self.systemTrayMenu)
        self.systemTrayIcon.activated[QSystemTrayIcon.ActivationReason].connect(self.systemTrayIconActivated)

        if RemoteHelp.isRemoteHelpAvailable():
            # Add Remote Help menu option under Windows platforms only.
            self.actionRemoteHelp = QAction(self)
            self.actionRemoteHelp.setIcon(QIcon(':/images/partner.png'))
            self.actionRemoteHelp.setText(_('Remote Help'))
            self.actionRemoteHelp.triggered.connect(self.remoteHelp)
            self.menuHelp.addAction(self.actionRemoteHelp)

        self.companyMenu = QMenu(self)
        self.pushCompany.setMenu(self.companyMenu)
        self.companyMenu.aboutToShow.connect(self.updateCompanyList)

        # Initialize plugins: This allows some plugins (such as SerialBarcodeScanner)
        # to be available in the LoginDialog.
        Plugins.list()

    def remoteHelp(self):
        RemoteHelp.remoteHelp(self)

    def systemTrayIconActivated(self, reason):
        if reason != QSystemTrayIcon.DoubleClick:
            return
        self.setVisible(not self.isVisible())
        if self.isMinimized():
            self.showNormal()

    def openPartnersTab(self):
        if not self.isVisible():
            self.showNormal()
        Api.instance.createWindow(None, 'res.partner', mode='tree,form')

    def openProductsTab(self):
        if not self.isVisible():
            self.showNormal()

        model = Rpc.session.execute('/object', 'execute', 'ir.model', 'search', [(
            'model', '=', 'product.product')], 0, 1, False, Rpc.session.context)
        if not model:
            QMessageBox.information(self, _('Products'), _(
                'Products module is not installed.'))
            return

        Api.instance.createWindow(None, 'product.product', mode='tree,form')

    def startRequestsTimer(self):
        # Every X minutes check for new requests and put the number of open
        # requests in the appropiate space in the status bar
        frequency = Settings.value(
            'koo.requests_refresh_interval', 5 * 60, int) * 1000
        if frequency > 0:
            self.requestsTimer.start(frequency)
        else:
            self.requestsTimer.stop()

        # Check for new Koo releases after logging in.
        self.checkNewRelease()

        # We always use the Subscriber as the class itself will handle
        # whether the module exists on the server or not
        self.subscriber = Rpc.Subscriber(Rpc.session, self)
        # Subscribe to changes to res.request (if 'koo' module is installed in the server).
        self.subscriber.subscribe(
            'updated_model:res.request', self.updateRequestsStatus)

    def stopRequestsTimer(self):
        self.requestsTimer.stop()
        if self.subscriber:
            self.subscriber.unsubscribe()
            self.subscriber = None

    def formDesigner(self):
        dialog = FormDesigner(self)
        dialog.show()

    # @brief Closes the given tab smartly.
    #
    # First asks the widget in the tab if it can be closed and if so, it removes it.
    # Note that the widget might ask the user some questions, for example when there's
    # modified data in a form.
    # It returns True if all tabs could be closed, False otherwise. If there are no
    # tabs always returns True.
    def closeTab(self, tab):
        widget = self.tabWidget.widget(tab)
        if widget:
            # Ask the current tab if it can be closed
            if not widget.canClose():
                return False
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.tabWidget.removeTab(tab)
        if widget:
            widget.setParent(None)
            del widget
        self.updateEnabledActions()
        QApplication.restoreOverrideCursor()
        return True

    # @brief Closes the current tab smartly.
    def closeCurrentTab(self):
        return self.closeTab(self.tabWidget.currentIndex())

    def fullTextSearch(self):
        # Ensure the window is shown as it might be called from the system tray icon
        # If we don't do this the dialog is shown, but when it's closed the whole
        # application is closed too.
        if not self.isVisible():
            self.showNormal()

        win = FullTextSearchDialog(self)
        win.exec_()

    def nextTab(self):
        pn = self.tabWidget.currentIndex()
        if pn == self.tabWidget.count() - 1:
            pn = 0
        else:
            pn = pn + 1
        self.tabWidget.setCurrentIndex(pn)

    def previousTab(self):
        pn = self.tabWidget.currentIndex()
        if pn == 0:
            pn = self.tabWidget.count() - 1
        else:
            pn = pn - 1
        self.tabWidget.setCurrentIndex(pn)

    def userPreferences(self):
        win = PreferencesDialog(self)
        win.exec_()

    def newRequest(self):
        if not self.isVisible():
            self.showNormal()
        Api.instance.createWindow(None, 'res.request', False,
                                  [('act_from', '=', Rpc.session.uid)], 'form', mode='form,tree')

    # Opens a new tab with requests pending for the user to resolve
    def pendingRequests(self):
        if not self.isVisible():
            self.showNormal()
        Api.instance.createWindow(False, 'res.request', False,
                                  [('act_to', '=', Rpc.session.uid)], 'form', mode='tree,form')

    # Opens a new tab with all unsolved requests posted by the user
    def waitingRequests(self):
        if not self.isVisible():
            self.showNormal()
        Api.instance.createWindow(False, 'res.request', False,
                                  [('act_from', '=', Rpc.session.uid), ('state', '=', 'waiting')], 'form', mode='tree,form')

    def updateCompanyList(self):
        self.companyMenu.clear()

        ids = Rpc.session.execute(
            '/object', 'execute', 'res.company', 'search', [], 0, False, 'name ASC')
        records = Rpc.session.execute(
            '/object', 'execute', 'res.company', 'read', ids, ['id', 'name'])

        for record in records:
            action = QAction(self)
            action.setText(record['name'])
            action.setData(record['id'])
            action.triggered.connect(self.changeCompany)
            self.companyMenu.addAction(action)

    def changeCompany(self):
        action = self.sender()
        company_id = action.data()
        users = Rpc.RpcProxy('res.users')
        users.write([Rpc.session.uid], {
            'company_id': company_id,
        }, Rpc.session.context)
        Rpc.session.reloadContext()
        self.updateCompany()
        self.closeAllTabs()
        self.openMenuTab()

    def updateCompany(self, company=None):
        if not company:
            users = Rpc.RpcProxy('res.users')
            records = users.read([Rpc.session.uid], [
                                 'company_id'], Rpc.session.context)
            company = records[0]['company_id']
            if company:
                company = company[1]
            else:
                company = ''
        self.pushCompany.setText(company)

    # Updates the status bar with the number of pending requests.
    #
    #  Note that this function uses Rpc.session.call() so exceptions are ignored, because this
    #  function is called every five minutes. We don't want any temporary disconnection of the
    #  server to annoy the user unnecessarily.
    def updateRequestsStatus(self):
        # We use 'try' because we might not have logged in or the server might
        # be down temporarily. This way the user isn't notified unnecessarily.
        uid = Rpc.session.uid
        try:
            ids, ids2 = Rpc.session.call(
                '/object', 'execute', 'res.request', 'request_get')
        except Rpc.RpcException as e:
            return ([], [])

        if len(ids):
            message = _('%s request(s)') % len(ids)
        else:
            message = _('No request')
        if len(ids2):
            message += _(' - %s pending request(s)') % len(ids2)
        self.uiRequests.setText(message)
        message = "%s - [%s]" % (message, Rpc.session.databaseName)
        self.systemTrayIcon.setToolTip(message)
        if self.pendingRequests != -1 and self.pendingRequests < len(ids):
            QApplication.alert(self)
            if self.systemTrayIcon.isVisible() and not self.isVisible():
                self.systemTrayIcon.showMessage(
                    _("New Request"), _("You've received a new request"))
        self.pendingRequests = len(ids)
        return (ids, ids2)

    def help(self):
        widget = self.tabWidget.currentWidget()
        if widget:
            widget.help(self.pushHelp)

    def checkNewRelease(self):
        from Koo.Common import Version

        Rpc.session.callAsync(self.newReleaseInformation, '/object', 'execute', 'nan.koo.release',
                              'needs_update', Version.Version, os.name, True, Rpc.session.context)

    def newReleaseInformation(self, value, exception):
        if exception:
            return

        if not value:
            return

        directory = tempfile.mkdtemp()
        installer = os.path.join(directory, value['filename'])
        f = open(installer, 'wb')
        f.write(base64.decodestring(value['installer']))
        f.close()
        command_line = value['command_line'].split(' ')
        command_line = [x.replace('$path', directory) for x in command_line]
        subprocess.Popen(command_line, cwd=directory)

    def showLoginDialog(self):
        dialog = LoginDialog(self)
        while dialog.exec_() == QDialog.Accepted:
            self.login(dialog.url, dialog.databaseName)
            if Rpc.session.open:
                return

    # Logs into the specified database and server.
    #
    # If correctly logged in, the parameters are stored as the default
    # config for the next time. Note that the function first will check
    # if it can close all opened tabs. If the user permits so by storing
    # or discarding all modified tabs, then it logs in. If no tabs are
    # opened or non of them have been modified, then no questions are asked.
    # @param url string describing the server
    # @param databaseName name of the database to log into
    def login(self, url, databaseName):
        # Before connecting to the specified database
        # try to logout from the previous one. That will allow the
        # user to cancel the operation if any of the tabs is modified
        # and it will stop requests timer and subscription.
        if not self.logout():
            return
        try:
            loginResponse = Rpc.session.login(url, databaseName)
            url = QUrl(url)
            if loginResponse == Rpc.session.LoggedIn:
                Settings.loadFromServer()
                if Settings.value('koo.stylesheet_code'):
                    QApplication.instance().setStyleSheet(Settings.value('koo.stylesheet_code'))
                if Settings.value('koo.use_cache'):
                    Rpc.session.cache = Rpc.Cache.ActionViewCache()
                else:
                    Rpc.session.cache = None

                iconVisible = Settings.value('koo.show_system_tray_icon', True)
                self.systemTrayIcon.setVisible(iconVisible)

                # Start timer once settings have been loaded because
                # the request interval can be configured
                self.startRequestsTimer()

                self.openMenuTab()
                self.openHomeTab()

                if Settings.value('open.model'):
                    model = Settings.value('open.model')
                    id = Settings.value('open.id') or False
                    mode = 'tree,form'
                    if id:
                        try:
                            id = int(id)
                            mode = 'form,tree'
                        except:
                            id = False
                            pass
                    Api.instance.createWindow(
                        None, model, id, view_type='form', mode=mode)

                if Common.isQtVersion45():
                    self.tabWidget.setTabsClosable(
                        Settings.value('koo.tabs_closable'))

                self.updateRequestsStatus()
                self.updateUserShortcuts()

            elif loginResponse == Rpc.session.Exception:
                QMessageBox.warning(self, _('Connection error !'), _(
                    'Unable to connect to the server !'))
            elif loginResponse == Rpc.session.InvalidCredentials:
                QMessageBox.warning(self, _('Connection error !'), _(
                    'Bad username or password !'))

        except Rpc.RpcException as e:
            if len(e.args) == 2:
                (e1, e2) = e.args
                Common.error(_('Connection Error !'), e.args[0], e.args[1])
            else:
                Common.error(_('Connection Error !'), _(
                    'Error logging into database.'), e)
            Rpc.session.logout()

    # Closes all tabs smartly, that is using closeCurrentTab()
    def closeAllTabs(self):
        while self.tabWidget.count() > 0:
            if not self.closeCurrentTab():
                return False
        return True

    def logout(self):
        if not self.closeAllTabs():
            return False
        self.uiRequests.clear()
        self.stopRequestsTimer()
        self.uiUserName.setText(_('Not logged !'))
        self.uiServerInformation.setText(_('Press Ctrl+O to login'))
        self.setWindowTitle(self.fixedWindowTitle)
        Rpc.session.logout()
        self.updateEnabledActions()
        self.updateUserShortcuts()
        return True

    def openPdfManual(self):
        try:
            pdf = Rpc.session.call(
                '/object', 'execute', 'ir.documentation.paragraph', 'export_to_pdf', Rpc.session.context)
        except:
            return False
        if not pdf:
            return False

        pdf = base64.decodestring(pdf)
        fd, fileName = tempfile.mkstemp('.pdf')
        os.write(fd, pdf)
        os.close(fd)
        Common.openFile(fileName)
        return True

    def openHtmlManual(self):
        Api.instance.createWebWindow(
            'openerp://ir.documentation.file/get/index.html', _('Manual'))

    def openDocOpenErpCom(self):
        Api.instance.createWebWindow(
            'http://doc.openerp.com', 'doc.openerp.com')

    def showTipOfTheDay(self):
        dialog = TipOfTheDayDialog(self)
        dialog.exec_()

    def showLicense(self):
        dialog = QDialog(self)
        loadUi(Common.uiPath('license.ui'), dialog)
        dialog.exec_()

    def showAboutDialog(self):
        dialog = QDialog(self)
        loadUi(Common.uiPath('about.ui'), dialog)
        from Koo.Common import Version
        dialog.uiOpenErp.setHtml(
            str(dialog.uiOpenErp.toHtml()) % Version.Version)
        dialog.exec_()

    def showShortcuts(self):
        dialog = QDialog(self)
        loadUi(Common.uiPath('shortcuts.ui'), dialog)
        dialog.exec_()

    def shortcutsChanged(self, model):
        if model == 'ir.ui.menu':
            self.updateUserShortcuts()

    def updateUserShortcuts(self):
        if not self.menuBar:
            return

        # Remove previous actions
        for action in self.shortcutActions:
            self.menuWindow.removeAction(action)
        self.shortcutActions = []

        if not Rpc.session.logged():
            return
        fields = Rpc.session.execute(
            '/object', 'execute', 'ir.ui.view_sc', 'fields_get', ['res_id', 'name'])
        self.shortcutsGroup = RecordGroup('ir.ui.view_sc', fields)
        self.shortcutsGroup.setDomain(
            [('user_id', '=', Rpc.session.uid), ('resource', '=', 'ir.ui.menu')])
        self.shortcutActions.append(self.menuWindow.addSeparator())
        for record in self.shortcutsGroup:
            action = QAction(self)
            action.setObjectName(str(record.id))
            action.setText(record.value('name'))
            action.setIcon(QIcon(':/images/relate.png'))
            action.triggered.connect(self.executeShortcut)
            self.menuWindow.addAction(action)
            self.shortcutActions.append(action)

    def executeShortcut(self):
        action = self.sender()
        id = int(action.objectName())
        # We need to get the value as if we were the server because we
        # don't want the string that would be shown for the many2one field
        # but the id.
        m = self.shortcutsGroup[id]
        id = self.shortcutsGroup.fieldObjects['res_id'].get(m)
        Api.instance.executeKeyword(
            'tree_but_open', {'model': 'ir.ui.menu', 'id': id, 'ids': [id]})

    # @brief Opens the Menu Tab.
    #
    # If a tab menu already exists it's risen, otherwise a new one is created
    # and rised.
    def openMenuTab(self):

        # Ensure the window is shown as it might be called from the system tray icon
        if not self.isVisible():
            self.showNormal()

        # Search if a menu tab already exists and rise it
        for p in range(self.tabWidget.count()):
            if self.tabWidget.widget(p).model == 'ir.ui.menu':
                self.tabWidget.setCurrentIndex(p)
                return

        # If no menu tab exists query the server and open it
        data = Rpc.session.execute('/object', 'execute', 'res.users', 'read', [
                                   Rpc.session.uid], ['menu_id', 'name', 'company_id'], Rpc.session.context)
        record = data[0]
        user = record['name'] or ''
        company = record['company_id'] and record['company_id'][1] or ''
        self.updateCompany(company)
        self.uiUserName.setText(user)
        self.uiServerInformation.setText("%s [%s]" % (
            Rpc.session.url, Rpc.session.databaseName))
        self.setWindowTitle("[%s] - %s" %
                            (Rpc.session.databaseName, self.fixedWindowTitle))

        if not record['menu_id']:
            QMessageBox.warning(self, _('Access denied'), _(
                'You can not log into the system !\nAsk the administrator to verify\nyou have an action defined for your user.'))
            Rpc.session.logout()
            self.menuId = False
            return

        # Store the menuId so we ensure we don't open the menu twice when
        # calling openHomeTab()
        self.menuId = record['menu_id'][0]

        Api.instance.execute(self.menuId, {'window': self})

    # @brief Opens Home Tab.
    #
    # Home tab is an action specified in the server which usually is a
    # dashboard, but could be anything.
    def openHomeTab(self):
        id = Rpc.session.execute('/object', 'execute', 'res.users', 'read',
                                 [Rpc.session.uid], ['action_id', 'name'], Rpc.session.context)

        if not id[0]['action_id']:
            return
        id = id[0]['action_id'][0]
        if not id:
            return

        # Do not open the action if the id is the same as the menu id.
        if id == self.menuId:
            return
        Api.instance.execute(id, {'window': self})

    def clearCache(self):
        ViewSettings.ViewSettings.clear()
        if Rpc.session.cache:
            Rpc.session.cache.clear()

    def closeEvent(self, event):
        if QMessageBox.question(
                self, _("Quit"), _("Do you really want to quit ?"),
                QMessageBox.Yes|QMessageBox.No
        ) == 1:
            event.ignore()
            return
        wid = self.tabWidget.currentWidget()
        if wid:
            # Ask the current tab if it can be closed
            if not wid.canClose():
                event.ignore()
                return
        Rpc.session.logout()
        self.systemTrayIcon.setVisible(False)

    @pyqtSlot()
    def closeTabForced(self):
        idx = self.tabWidget.indexOf(self.sender())
        self.tabWidget.removeTab(idx)
        self.updateEnabledActions()
        # del self.sender()

    def addWindow(self, win, target):
        if target in ('current', 'background'):
            win.closed.connect(self.closeTabForced)
            win.shortcutsChanged.connect(self.shortcutsChanged)
            self.tabWidget.addTab(win, win.name)
            # If shift key is pressed do not show the added tab
            if target != 'background':
                self.tabWidget.setCurrentIndex(self.tabWidget.count() - 1)
        else:
            # When opening in a new window we make the dialog modal. This way,
            # wizards that use this method and were called from a button, they
            # return to the button code and it can refresh the view after the
            # wizard has finished.
            parent = QApplication.activeModalWidget()
            if not parent:
                parent = self
            dialog = QDialog(parent)
            dialog.setWindowTitle(_('Wizard'))
            dialog.setModal(True)
            layout = QHBoxLayout(dialog)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(win)
            win.setParent(dialog)
            win.closed.connect(dialog.accept)
            win.show()
            dialog.exec_()

    def updateEnabledActions(self):

        if not self.menuBar:
            return

        view = self.tabWidget.currentWidget()
        for x in self.actions:
            action = eval('self.action' + x)
            if view and x in view.handlers:
                action.setEnabled(True)
            else:
                action.setEnabled(False)

        if Rpc.session.open:
            self.actionFullTextSearch.setEnabled(True)
        else:
            self.actionFullTextSearch.setEnabled(False)

        if Settings.value('koo.allow_massive_updates', True):
            self.actionBatchInsert.setVisible(True)
            self.actionBatchUpdate.setVisible(True)
            self.actionBatchButton.setVisible(True)
        else:
            self.actionBatchInsert.setVisible(False)
            self.actionBatchUpdate.setVisible(False)
            self.actionBatchButton.setVisible(False)

        if Settings.value('koo.allow_import_export', True):
            self.actionImport.setVisible(True)
            self.actionExport.setVisible(True)
        else:
            self.actionImport.setVisible(False)
            self.actionExport.setVisible(False)

        # Update the 'Reports', 'Actions' and 'Browse' Menu entries

        self.menuReports.clear()
        self.menuBrowse.clear()
        self.menuActions.clear()
        self.menuPlugins.clear()

        reports = False
        browse = False
        actions = False
        plugins = False
        if view:
            self.pushSwitchView.setMenu(view.switchViewMenu())
            for x in view.actions():
                if x.type() == 'print':
                    self.menuReports.addAction(x)
                    reports = True
                elif x.type() == 'relate':
                    self.menuBrowse.addAction(x)
                    browse = True
                elif x.type() == 'action':
                    self.menuActions.addAction(x)
                    actions = True
                else:  # Should be 'plugin'
                    self.menuPlugins.addAction(x)
                    plugins = True

        self.menuReports.setEnabled(reports)
        self.menuBrowse.setEnabled(browse)
        self.menuActions.setEnabled(actions)
        self.menuPlugins.setEnabled(plugins)

        value = Rpc.session.logged()
        self.actionOpenMenuTab.setEnabled(value)
        self.actionOpenHomeTab.setEnabled(value)
        self.actionPreferences.setEnabled(value)
        self.actionClearCache.setEnabled(value)
        self.actionSendRequest.setEnabled(value)
        self.actionReadMyRequest.setEnabled(value)
        self.actionWaitingRequests.setEnabled(value)
        self.actionDisconnect.setEnabled(value)

        if self.tabWidget.count() > 0:
            value = True
        else:
            value = False
        self.actionClose.setEnabled(value)
        self.actionNextTab.setEnabled(value)
        self.actionPreviousTab.setEnabled(value)

    def callChildView(self):
        o = self.sender()
        action = str(o.objectName()).replace('action', '')
        wid = self.tabWidget.currentWidget()
        if wid:
            res = True
            if action in wid.handlers:
                res = wid.handlers[action]()

    def currentChanged(self, page):
        self.updateEnabledActions()

    def createDatabase(self):
        dialog = DatabaseCreationDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.login(dialog.url, dialog.databaseName)

    def dropDatabase(self):
        dropDatabase(self)

    def restoreDatabase(self):
        restoreDatabase(self)

    def backupDatabase(self):
        backupDatabase(self)

    def changeAdministratorPassword(self):
        dialog = AdministratorPasswordDialog(self)
        dialog.exec_()

# vim:noexpandtab:smartindent:tabstop=8:softtabstop=8:shiftwidth=8:
