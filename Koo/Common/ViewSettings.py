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

from Koo import Rpc


class ViewSettings:
    """
    ViewSettings class allows storing and retrieving of view state
    information such as column size and ordering in QListViews and the such.

    Settings are stored as a string (not unicode) and in most cases
    end up converted to/from a QByteArray; hence the need of ensuring
    we use str instead of unicode. That's why we enforce str() in a
    couple of places.
    """
    cache = {}
    databaseName = None
    uid = None
    hasSettingsModule = True

    @staticmethod
    def store(id, settings):
        """
        Stores settings for the given view id.
        :param id:
        :param settings:
        :return:
        """
        if not id:
            return

        ViewSettings.checkConnection()

        if settings:
            # Ensure it's a string and not unicode
            settings = str(settings)

        # Do not update store data in the server if it settings have not changed
        # from the ones in cache.
        if id in ViewSettings.cache and ViewSettings.cache[id] == settings:
            return

        # Add settings in the cache. Note that even if the required koo
        # module is not installed in the server view settings will be kept
        # during user session.
        ViewSettings.cache[id] = settings

        if not ViewSettings.hasSettingsModule:
            return

        try:
            # We don't want to crash if the koo module is not installed on the server
            # but we do want to crash if there are mistakes in setViewSettings() code.
            ids = Rpc.session.call('/object', 'execute', 'nan.koo.view.settings', 'search', [
                ('user', '=', Rpc.session.uid), ('view', '=', id)
            ])
        except:
            ViewSettings.hasSettingsModule = False
            return
        # As 'nan.koo.view.settings' is proved to exist we don't need try-except here. And we
        # can use execute() instead of call().
        if ids:
            Rpc.session.execute('/object', 'execute', 'nan.koo.view.settings', 'write', ids, {
                'data': settings
            })
        else:
            Rpc.session.execute('/object', 'execute', 'nan.koo.view.settings', 'create', {
                'user': Rpc.session.uid,
                'view': id,
                'data': settings
            })

    # @brief
    @staticmethod
    def load(id):
        """
        Loads information for the given view id.
        :param id:
        :return:
        """
        if not id:
            return None

        ViewSettings.checkConnection()
        if id in ViewSettings.cache:
            # Restore settings from the cache. Note that even if the required koo
            # module is not installed in the server view settings will be kept
            # during user session.
            return ViewSettings.cache[id]

        if not ViewSettings.hasSettingsModule:
            return None

        try:
            # We don't want to crash if the koo module is not installed on the server
            # but we do want to crash if there are mistakes in setViewSettings() code.
            ids = Rpc.session.call('/object', 'execute', 'nan.koo.view.settings', 'search', [
                ('user', '=', Rpc.session.uid), ('view', '=', id)
            ])
        except:
            ViewSettings.hasSettingsModule = False
            return None

        # As 'nan.koo.view.settings' is proved to exist we don't need try-except here.
        if not ids:
            ViewSettings.cache[id] = None
            return None
        settings = Rpc.session.execute(
            '/object', 'execute', 'nan.koo.view.settings', 'read', ids, ['data'])[0]['data']

        if settings:
            # Ensure it's a string and not unicode
            settings = str(settings)

        ViewSettings.cache[id] = settings

        return settings

    @staticmethod
    def checkConnection():
        """
        Checks if connection has changed and clears cache and hasSettingsModule flag
        :return:
        """
        if ViewSettings.databaseName != Rpc.session.databaseName or ViewSettings.uid != Rpc.session.uid:
            ViewSettings.clear()

    @staticmethod
    def clear():
        """
        Clears cache and resets state. This means that after installing the koo
        module you don't have to close session and login again because
        hasSettingsModule is reset to True.
        :return:
        """
        ViewSettings.databaseName = Rpc.session.databaseName
        ViewSettings.uid = Rpc.session.uid
        ViewSettings.hasSettingsModule = True
        ViewSettings.cache = {}
