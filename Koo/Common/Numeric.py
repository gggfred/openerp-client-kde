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

import locale


def textToInteger(text):
    """
    This function converts a string into an integer allowing
    operations (+, -, /, *).

    The formula is calculated and the output is returned by
    the function. If the formula contains floating point
    values or results they're converted into integer at the end.
    :param text:
    :return:
    """
    chars = ['+', '-', '/', '*', '.', '(', ')', ',']
    chars = chars + [str(x) for x in range(10)]
    text = text.replace(',', '.')
    try:
        return int(eval(text))
    except:
        return False


def textToFloat(text):
    """
    This function converts a string into a float allowing
    operations (+, -, /, *).

    The formula is calculated and the output is returned by
    the function.
    :param text:
    :return:
    """
    chars = ['+', '-', '/', '*', '.', '(', ')', ',']
    chars = chars + [str(x) for x in range(10)]
    newtext = text.replace(',', '.')
    value = False
    try:
        value = float(eval(newtext))
    except:
        if '.' in text and ',' in text:
            if text.rindex('.') > text.rindex(','):
                newtext = text.replace(',', '')
            else:
                newtext = text.replace('.', '')
            newtext = newtext.replace(',', '.')
            try:
                value = float(newtext)
            except:
                pass
    return value


def floatToText(number, digits=None, thousands=False):
    """
    This function converts a float into text. By default the number
    of decimal digits is 2.
    :param number:
    :param digits:
    :param thousands:
    :return:
    """
    if isinstance(number, int):
        number = float(number)
    if not isinstance(number, float):
        number = 0.0
    if digits:
        # Digits might come from the server as a tuple, list or a string
        # So: (14,2), [14,2], '(14,2)' and '[14,2]' are all valid forms
        if isinstance(digits, list) or isinstance(digits, tuple):
            d = str(digits[1])
        else:
            d = digits.split(',')[1].strip(' )]')
    else:
        d = '2'

    if thousands:
        return locale.format('%.' + d + 'f', number, True, True)
    else:
        return ('%.' + d + 'f') % number


def integerToText(number):
    """
    This function converts an integer into text.
    :param number:
    :return:
    """
    if isinstance(number, float):
        number = int(number)
    if not isinstance(number, int):
        number = 0
    return '%d' % number


def isNumeric(value):
    """
    This function returns True if the given value can be converted into
    a float number. Otherwise it returns False.
    :param value:
    :return:
    """
    try:
        return float(value) or True
    except (ValueError, TypeError) as e:
        return False


def bytesToText(number):
    """
    This function converts the given paramter (which should be a number) into
    a human readable storage value, ie. bytes, Kb, Mb, Gb, Tb.
    :param number:
    :return:
    """
    number = float(number)
    texts = [_('%d bytes'), _('%.2f Kb'), _(
        '%.2f Mb'), _('%.2f Gb'), _('%.2f Tb')]
    i = 0
    while number >= 1024 and i < len(texts) - 1:
        number = number / 1024
        i += 1
    return texts[i] % number
