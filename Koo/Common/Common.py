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

from Koo.Common import Api
from Koo.Common.Settings import *
from Koo import Rpc

import os
import sys
from Koo.Common import Debug

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from Koo.Common.Ui import *

from Koo.Common.Paths import *

try:
    QString = unicode
except NameError:
    # Python 3
    QString = str

try:
    if Settings.value('kde.enabled'):
        from PyKDE5.kdecore import ki18n
        isKdeAvailable = True
    else:
        isKdeAvailable = False
except:
    isKdeAvailable = False


def isQtVersion45():
    return PYQT_VERSION >= 0x40500


serverVersion = None
serverMajorVersion = None


# Load Resource
from Koo.Common import common_rc
# When using loadUiType(), the generated (and executed) code will try to import
# common_rc and it will crash if we don't ensure it's available in PYTHONPATH
# so by no we have to add Koo/Common to sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


def nodeAttributes(node):
    """
    Returns a dictionary with all the attributes found in a XML with their name
    as key and the corresponding value.
    :param node:
    :return:
    """
    result = {}
    attrs = node.attributes
    if attrs is None:
        return {}
    for i in range(attrs.length):
        result[attrs.item(i).localName] = attrs.item(i).nodeValue
    return result


def sendEMail(to, subject, body):
        # Import smtplib for the actual sending function
    import smtplib

    # Import the email modules we'll need
    from email.mime.text import MIMEText

    source = Settings.value('koo.smtp_from')

    msg = MIMEText(body)

    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = source
    msg['To'] = to

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    s = smtplib.SMTP(Settings.value('koo.smtp_server'))
    s.sendmail(source, [to], msg.as_string())
    s.quit()


(SelectionDialogUi, SelectionDialogBase) = loadUiType(uiPath('win_selection.ui'))



class SelectionDialog(QDialog, SelectionDialogUi):
    """
    The SelectionDialog class shows a dialog prompting the user to choose
    among a list of items.

    The selected value is stored in the 'result' property.
    @see selection()
    """
    def __init__(self, title, values, parent=None):
        QDialog.__init__(self, parent)
        SelectionDialogUi.__init__(self)
        self.setupUi(self)

        if title:
            self.uiTitle.setText(title)
        for x in list(values.keys()):
            item = QListWidgetItem()
            item.setText(x)
            item.value = values[x]
            self.uiList.addItem(item)
        self.pushAccept.clicked.connect(self.selected)

    def selected(self):
        self.result = ""
        item = self.uiList.currentItem()
        self.result = (str(item.text()), item.value)
        self.accept()

# @brief


def selection(title, values, alwaysask=False):
    """
    Shows the SelectionDialog

    It returns the selected item or False if none was selected.

    No dialog will be shown if the dictionary of values is empty. If alwaysask
    is False (the default) no dialog is shown and the only element is returned
    as selected.

    :param title:
    :param values:
    :param alwaysask:
    :return:
    """
    if len(values) == 0:
        return None
    elif len(values) == 1 and (not alwaysask):
        key = list(values.keys())[0]
        return (key, values[key])
    s = SelectionDialog(title, values)
    if s.exec_() == QDialog.Accepted:
        return s.result
    else:
        return False


def warning(title, message):
    """
    Shows a warning dialog. Function used by the notifier in the Koo
    application.
    :param title:
    :param message:
    :return:
    """
    QApplication.setOverrideCursor(Qt.ArrowCursor)
    QMessageBox.warning(None, title, message)
    QApplication.restoreOverrideCursor()


class ConcurrencyErrorDialog(QMessageBox):
    """
    The ConcurrencyErrorDialog class provices a Dialog used when a
    concurrency error is received from the server.
    """
    def __init__(self, parent=None):
        QMessageBox.__init__(self, parent)
        self.setIcon(QMessageBox.Warning)
        self.setWindowTitle(_('Concurrency warning'))
        self.setText(
            _('<b>Write concurrency warning:</b><br/>This document has been modified while you were editing it.'))
        self.addButton(_('Save anyway'), QMessageBox.AcceptRole)
        self.addButton(_('Compare'), QMessageBox.ActionRole)
        self.addButton(_('Do not save'), QMessageBox.RejectRole)


def concurrencyError(model, id, context):
    """
    Shows the ConcurrencyErrorDialog. Function used by the notifier in the
    Koo application.
    :param model:
    :param id:
    :param context:
    :return:
    """
    QApplication.setOverrideCursor(Qt.ArrowCursor)
    dialog = ConcurrencyErrorDialog()
    result = dialog.exec_()
    QApplication.restoreOverrideCursor()
    if result == 0:
        return True
    if result == 1:
        Api_instance.createWindow(False, model, id, context=context)

    return False


(ErrorDialogUi, ErrorDialogBase) = loadUiType(uiPath('error.ui'))


class ErrorDialog(QDialog, ErrorDialogUi):
    """
    The ErrorDialog class shows the error dialog used everywhere in Koo.

    The dialog shows two tabs. One with a short description of the problem and
    the second one with the details, usually a backtrace.

    @see error()
    """
    def __init__(self, title, message, details='', parent=None):
        QDialog.__init__(self, parent)
        ErrorDialogUi.__init__(self)
        self.setupUi(self)

        self.uiDetails.setText(details)
        self.uiErrorInfo.setText(message)
        self.uiErrorTitle.setText(title)

        from Koo.Common import RemoteHelp
        self.pushRemoteHelp.setVisible(RemoteHelp.isRemoteHelpAvailable())

        self.pushSend.clicked.connect(self.send)
        self.pushRemoteHelp.clicked.connect(self.remoteHelp)

    def done(self, r):
        QDialog.done(self, r)

    def remoteHelp(self):
        from Koo.Common import RemoteHelp
        RemoteHelp.remoteHelp(self)

    def send(self):
        to = Settings.value('koo.smtp_backtraces_to')

        button = QMessageBox.question(self, _('Send Error Information'), _(
            'You are about to send the details of this error, database name, user ID, and server URL to %s. Do you want to proceed?') % to, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if button == QMessageBox.No:
            return

        subject = 'Backtrace information: %s' % Rpc.session.databaseName
        body = ''
        body += 'Database: %s\n' % Rpc.session.databaseName
        body += 'User ID: %s\n' % Rpc.session.uid
        body += 'URL: %s\n\n' % Rpc.session.url
        body += 'Backtrace:\n\n'
        body += str(self.uiDetails.toPlainText()
                        ).encode('ascii', 'replace')
        try:
            sendEMail(Settings.value('koo.smtp_backtraces_to'), subject, body)
        except:
            QMessageBox.warning(self, _('Send Error Information'), _(
                'Error information could not be sent.'))
            return

        QMessageBox.information(self, _('Send Error Information'), _(
            'Error information was successfully sent.'))
        self.pushSend.setEnabled(False)


def error(title, message, details=''):
    """
    Shows the ErrorDialog. Function used by the notifier in the Koo application.
    :param title:
    :param message:
    :param details:
    :return:
    """
    QApplication.setOverrideCursor(Qt.ArrowCursor)
    dialog = ErrorDialog(str(title), str(message), str(details))
    dialog.exec_()
    QApplication.restoreOverrideCursor()


(LostConnectionDialogUi, LostConnectionDialogBase) = loadUiType(
    uiPath('lostconnection.ui'))

# @brief


class LostConnectionDialog(QDialog, LostConnectionDialogUi):
    """
    The LostConnectionDialog class shows the error dialog used when connection
    with the server has been lost.

    The show a counter which is decreased every seconds and waits for 10
    seconds before retrying.

    @see lostConnectionError()
    """
    def __init__(self, count, parent=None):
        QDialog.__init__(self, parent)
        LostConnectionDialogUi.__init__(self)
        self.setupUi(self)

        self.count = count
        self.retry = True
        self.remaining = 10
        self.updateMessage()
        self.uiTitle.setText(_('<b>Connection Lost:</b> %s') % count)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.updateMessage)
        self.rejected.connect(self.stopTimer)
        self.timer.start()

    def updateMessage(self):
        self.uiMessage.setText(
            _('Connection with the server has been lost. Will retry connection in %d seconds.') % self.remaining)
        self.remaining -= 1
        if self.remaining < 0:
            self.timer.stop()
            self.accept()

    def stopTimer(self):
        self.timer.stop()


def lostConnectionError(count):
    """
    Shows the ErrorDialog. Function used by the notifier in the Koo application.
    :param count:
    :return:
    """
    QApplication.setOverrideCursor(Qt.ArrowCursor)
    dialog = LostConnectionDialog(count)
    if dialog.exec_() == QDialog.Rejected:
        result = QMessageBox.warning(None, _("Quit"), _(
            "Leaving the application now will lose all unsaved changes. Are you sure you want to quit?"), QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if result == QMessageBox.Yes:
            QApplication.quit()
            sys.exit(0)
    QApplication.restoreOverrideCursor()
    return True


(ProgressDialogUi, ProgressDialogBase) = loadUiType(uiPath('progress.ui'))



class ProgressDialog(QDialog, ProgressDialogUi):
    """
    The ProgressDialog class shows a progress bar moving left and right until
    you stop it.

    To use it:
    1) Create a dialog (eg. dlg = ProgressDialog(self))
    2) Call the start function (eg. dlg.start() )
    3) Call the stop function when the operation has finished (eg. dlg.stop() )
    Take into account that the dialog will only show after a couple of seconds.
    This way, it
    only appears on long running tasks.
    """
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        ProgressDialogUi.__init__(self)
        self.setupUi(self)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)

    def start(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.timeout)
        self.timer.start(2000)

    def timeout(self):
        self.timer.stop()
        self.show()

    def stop(self):
        self.timer.stop()
        self.accept()


def openFile(fileName):
    """
    Opens the given file with system's default application.
    :param fileName:
    :return:
    """
    if os.name == 'nt':
        os.startfile(fileName)
    elif os.uname()[0] == 'Darwin':
        os.system('/usr/bin/open -a Preview %s' % fileName)
    else:
        os.spawnlp(os.P_NOWAIT, 'xdg-open', 'xdg-open', fileName)


def normalizeLabel(text):
    """
    Converts GTK accelerators to Qt ones.
    GTK uses underscore as accelerator in labels and buttons whereas Qt uses
    ampersand. This function will convert a text prepared for a GTK label into
    a valid Qt one.
    :param text:
    :return:
    """
    # If text is False, we ensure a string is returned.
    if not text:
        return ''

    res = ''
    underscore = False
    for x in text:
        if x == '_':
            if underscore:
                res += '_'
                underscore = False
            else:
                underscore = True
        else:
            if underscore:
                res += '&'
                underscore = False
            if x == '&':
                res += '&&'
            else:
                res += x
    return res


def stringToBool(text):
    """
    This function converts a string into a boolean.

    Given that OpenERP has changed the way it handles booleans in view definitions
    it's a bit complicated to properly evaluate it. At first only "1" and "0" were
    used, for example.
    :param text:
    :return:
    """
    if isinstance(text, str) or isinstance(text, str):
        text = text.strip()
        if text.lower() == 'true' or text == '1':
            return True
        if text.lower() == 'false' or text == '0':
            return False
    return bool(text)


def simplifyHtml(html):
    """
    This function simplifies HTML as returned by TextEdit.toHtml() function by
    removing <html>, <head> and <body> tags, so resulting text integrates
    better when used in a web page.
    :param html:
    :return:
    """
    if isinstance(html, QString):
        html = str(html)
    if '<p' in html:
        index = html.find('<p')
        html = html[index:]
        index = html.rfind('</p>') + 4
        html = html[:index]
    return html
