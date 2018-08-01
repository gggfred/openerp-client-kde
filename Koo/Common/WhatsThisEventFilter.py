#   Copyright (C) 2009 by Albert Cervera i Areny  albert@nan-tic.com
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from Koo.Common import Shortcuts


class WhatsThisEventFilter(QObject):
    """
    The WhatsThisEventFilter class provides an eventFilter that allows
    viewing the What's This information of the current widget by pressing a key.

    This is mostly interesting for viewing help of form fields. By default the
    shortcut is F10.

    To install it in an application use
    'app.installEventFilter( Koo.Common.WhatsThisEventFilter( mainWindow ) )'
    """

    def __init__(self, parent=None):
        """
        Creates a new WhatsThisEventFilter object.
        :param parent:
        """
        QObject.__init__(self, parent)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyRelease and event.key() == Shortcuts.WhatsThis:
            QApplication.postEvent(obj, QEvent(QEvent.WhatsThis))
            return True
        return QObject.eventFilter(self, obj, event)
