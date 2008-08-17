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

from osv import osv, fields

# This class holds the different priorities available
class priority(osv.osv):
	_name = 'fts.priority'
	_columns = {
		'name' : fields.char('Name', size=1),
		'value' : fields.float('Value (0-1.0)')
	}
priority()

# This class defines all full text search (TSearch) configurations available
# There can be configurations for strings and numbers, for example. Or different languages.
class configuration(osv.osv):
	_name = 'fts.configuration'
	_columns = {
		'name' : fields.char('Name', size=64)
	}
configuration()

# This class holds the indexes that we want to be created
# as soon as we execute the update index functions...
class full_text_index(osv.osv):
	_name = 'fts.full_text_index'
	_columns = {
		'field_id' : fields.many2one('ir.model.fields', 'Field', required=True),
		'priority' : fields.many2one('fts.priority', 'Priority', required=True),
		'configuration' : fields.many2one('fts.configuration', 'Configuration', required=True)
	}
full_text_index()

# This class holds the indexes that are currently created
class current_full_text_index(osv.osv):
	_name = 'fts.current_full_text_index'
	_columns = {
		'field_id' : fields.many2one('ir.model.fields', 'Field', required=True),
		'priority' : fields.many2one('fts.priority', 'Priority', required=True),
		'configuration' : fields.many2one('fts.configuration', 'Configuration', required=True)
	}
current_full_text_index()

