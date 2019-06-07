"""
Subprogram Command Module -- Contains the editor commands that
handle copying a subprogram declaration and permit copying in
various forms.
"""

import time
import re
import sublime
import sublime_plugin

from . import vhdl_lang as vhdl
from . import vhdl_util as util

_subprogram = vhdl.Subprogram()


class vhdlModeCopySubprogram(sublime_plugin.TextCommand):
    """
    This command scans upwards from the point looking for a
    subprogram beginning, then down to find the end.  It parses
    out the gooey center and saves it so it can be repasted in
    various handy forms.
    """

    def find_start(self, point, subprogram):
        """Scans the text for the subprogram beginning.  Uses class
        method to determine success."""
        # Use the beginning of the line for all operations so we avoid
        # potential oddities from where the point was originally.
        next_point = util.move_to_bol(self, point)
        while True:
            # The start method returns the column of the starting of the
            # subprogram.
            check = subprogram.subprogram_start(util.line_at_point(self, next_point))
            if check is None:
                if util.is_top_line(self, next_point):
                    print('vhdl-mode: Subprogram not found.')
                    return None
                else:
                    next_point = util.move_up(self, next_point)
            else:
                print('vhdl-mode: Subprogram beginning found.')
                return self.view.text_point(self.view.rowcol(next_point)[0], check)

    def find_end(self, point, subprogram):
        """Scans the text for the subprogram ending.  Uses class
        method to determine success."""
        next_point = util.move_to_bol(self, point)
        while True:
            check = subprogram.subprogram_end(util.line_at_point(self, next_point))
            if check is None:
                if util.is_end_line(self, next_point):
                    print('vhdl-mode: End of subprogram not found.')
                    return None
                else:
                    next_point = util.move_down(self, next_point)
            else:
                print('vhdl-mode: Subprogram end found.')
                return self.view.text_point(self.view.rowcol(next_point)[0], check)


    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

    def run(self, edit):
        """Fundamental ST Command method."""
        global _subprogram

        # Save the point.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Freshen up the variable
        _subprogram.reset()

        # Attempt to find a subprogram beginning.
        startpoint = self.find_start(original_point, _subprogram)
        if startpoint is None:
            util.set_cursor(self, original_point)
            return

        # Attempt to find a subprogram end.
        endpoint = self.find_end(startpoint, _subprogram)
        if endpoint is None:
            util.set_cursor(self, original_point)
            return

        block = sublime.Region(startpoint, endpoint)
        _subprogram.if_string = self.view.substr(block)
        _subprogram.parse_block()
        #_subprogram.print()

#----------------------------------------------------------------
class vhdlModePasteAsDeclarationCommand(sublime_plugin.TextCommand):
    """Pastes the currently copied subprogram as a declaration."""
    def description(self):
        return "Paste {} as Declaration".format(_subprogram.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_subprogram.name)

    def run(self, edit):
        """Fundamental ST Command method."""
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        block_str = _subprogram.declaration()
        #print(block_str)
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as subprogram declaration.')

        # Set point to the end of insertion.
        util.set_cursor(self, next_point+num_chars)

#----------------------------------------------------------------
class vhdlModePasteAsBodyCommand(sublime_plugin.TextCommand):
    """Pastes the currently copied subprogram as a declaration."""

    def description(self):
        return "Paste {} as Body".format(_subprogram.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_subprogram.name)

    def run(self, edit):
        """Fundamental ST Command method."""
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        block_str = _subprogram.body()
        #print(block_str)
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as subprogram body.')

        # Set point to the end of insertion.
        util.set_cursor(self, next_point+num_chars)

#----------------------------------------------------------------
class vhdlModePasteAsCallCommand(sublime_plugin.TextCommand):
    """Pastes the currently copied subprogram as a declaration."""

    def description(self):
        return "Paste {} as Call".format(_subprogram.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_subprogram.name)

    def run(self, edit):
        """Fundamental ST Command method."""
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        block_str = _subprogram.call()
        #print(block_str)
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as subprogram call.')

        # Set point to the end of insertion.
        util.set_cursor(self, next_point+num_chars)


#----------------------------------------------------------------
class vhdlModeFlattenParamsCommand(sublime_plugin.TextCommand):
    '''
    This command scans over the internal data structure of a
    subprogram interface and whenever there is an interface that
    has multiple names on the same line, it'll separate these
    into their own lines, one name per line.
    '''
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_subprogram.name)

    def run(self, edit):
        global _subprogram
        _subprogram.flatten()
        print('vhdl-mode: Flattening parameters for next paste.')
