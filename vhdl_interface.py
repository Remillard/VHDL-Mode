"""
Port Copying Module -- Contains the editor commands related to
copying and pasting an interface declaration into various forms.
"""
import time
import re
import sublime
import sublime_plugin

from . import vhdl_lang as vhdl
from . import vhdl_util as util

_interface = vhdl.Interface()

#----------------------------------------------------------------
class vhdlModeCopyPortsCommand(sublime_plugin.TextCommand):
    """
    The copy ports command requires the user to have placed the
    point somewhere in the interface to be extracted.  The
    routine then scans upwards to find a known interface beginning
    and then down to find the end point.  If a good interface
    can be determined, then it uses the VHDL language classes to
    parse the text from the editor and store the structural
    elements for later pasting in other forms.
    """
    def find_start(self, point, interface):
        # Abstracting the loop for finding the beginning
        # of the declaration.
        # Moving point to beginning of line which avoids
        # checking a line twice due to line lengths.
        next_point = util.move_to_bol(self, point)
        while True:
            check = interface.interface_start(util.line_at_point(self, next_point))
            if check is None:
                if util.is_top_line(self, next_point):
                    print('vhdl-mode: Interface not found.')
                    return None
                else:
                    next_point = util.move_up(self, next_point)
            else:
                print('vhdl-mode: Interface beginning found.')
                return self.view.text_point(self.view.rowcol(next_point)[0], check)

    def find_end(self, point, interface):
        # Stepping forward to find the end of the interface.
        next_point = util.move_to_bol(self, point)
        while True:
            check = interface.interface_end(util.line_at_point(self, next_point))
            if check is None:
                if util.is_end_line(self, next_point):
                    print('vhdl-mode: End of interface not found.')
                    return None
                else:
                    next_point = util.move_down(self, next_point)
            else:
                print('vhdl-mode: Interface end found.')
                return self.view.text_point(self.view.rowcol(next_point)[0], check)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

    def run(self, edit):
        global _interface

        # Save the starting point location.  In the case of a
        # multi-selection, save point A of the first region.
        # This command does not have any meaning for a multi-
        # selection.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Search for the starting entity string.
        startpoint = self.find_start(original_point, _interface)
        if startpoint is None:
            util.set_cursor(self, original_point)
            return

        # Search for the endpoint based on the start point.
        endpoint = self.find_end(startpoint, _interface)
        if endpoint is None:
            util.set_cursor(self, original_point)
            return

        # At this point, we should have a start and end point.  Extract
        # the string that contains the interface by creating a region
        # with the points.  At this point, all the processing should be
        # in the interface class.
        block = sublime.Region(startpoint, endpoint)
        _interface.if_string = self.view.substr(block)
        _interface.parse_block()

        # At the very end, move the point back to where we
        # started
        util.set_cursor(self, original_point)

#----------------------------------------------------------------
class vhdlModePasteAsSignalCommand(sublime_plugin.TextCommand):
    """
    Once we've copied an interface, we can paste the data back as
    signals (ports only, not generics.)
    """
    def description(self):
        return "Paste {} as Signals".format(_interface.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        global _interface
        # Get the current point location.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        lines = []
        # Construct structure and insert
        block_str = _interface.signals()
        if block_str is not None:
            num_chars = self.view.insert(edit, next_point, block_str)
            print('vhdl-mode: Inserted interface as signal(s).')
            util.set_cursor(self, next_point+num_chars)
        else:
            print('vhdl-mode: No valid ports in interface for signal(s).')
            # Set the point to original location
            util.set_cursor(self, original_point)

#----------------------------------------------------------------
class vhdlModePasteAsComponentCommand(sublime_plugin.TextCommand):
    """
    Pasting the current written interface as a component
    """
    def description(self):
        return "Paste {} as Component".format(_interface.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        # Get the current point location.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        block_str = _interface.component()
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as component.')

        # Set point to the end of insertion.
        util.set_cursor(self, next_point+num_chars)

#----------------------------------------------------------------
class vhdlModePasteAsEntityCommand(sublime_plugin.TextCommand):
    """
    Pasting the currently copied interface as an entity.
    """
    def description(self):
        return "Paste {} as Entity".format(_interface.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        # Get the current point location.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        block_str = _interface.entity()
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as entity.')

        # Set the point to end of insertion
        util.set_cursor(self, next_point+num_chars)

#----------------------------------------------------------------
class vhdlModePasteAsInstanceCommand(sublime_plugin.TextCommand):
    """
    Pastes the currently copied interface into the source as
    an instantiation.  Currently does not keep track of other
    instances of the same interface in the source.
    """
    def description(self):
        return "Paste {} as Instance".format(_interface.name)

    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        # Get the current point location.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        # Construct structure.  Get the file structure.
        instances = util.scan_instantiations(self)
        block_str = _interface.instance(instances=instances)
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as instance.')

#----------------------------------------------------------------
class vhdlModePasteAsTestbenchCommand(sublime_plugin.WindowCommand):
    """
    After copying a port, this will open a new window and
    inject the skeleton of a testbench.  Note, this isn't a
    TextCommand, but rather a WindowCommand so the run method
    has slightly different parameters.
    """
    def description(self):
        return "Paste {} as Testbench".format(_interface.name)

    def is_visible(self):
        # I can't do the usual source file check because this is a
        # WindowCommand and not a TextCommand which has an associated view.
        # At the moment, simply checking to see if there is a valid interface
        # that's been copied.
        return self.window.active_view().match_selector(0, 'source.vhdl') and bool(_interface.name)

    def run(self):
        """Sublime TextCommand run method"""
        # Assigning this to a string to keep command shorter later.
        template = "Packages/VHDL Mode/Snippets/vhdl-testbench.sublime-snippet"

        tb_view = self.window.new_file()
        tb_view.assign_syntax('Packages/VHDL Mode/Syntax/VHDL.sublime-syntax')
        tb_view.set_name('{}_tb.vhd'.format(_interface.name))

        entity_name = '{}_tb'.format(_interface.name)
        signals_str = _interface.signals()
        constants_str = _interface.constants()
        instance_str = _interface.instance(name="DUT")

        # Inserting template/snippet
        tb_view.run_command("insert_snippet",
            {
                "name"     : template,
                "ENAME"    : entity_name,
                "CONSTANTS": constants_str,
                "SIGNALS"  : signals_str,
                "INSTANCE" : instance_str
            })
        tb_view.run_command("vhdl_mode_insert_header")
        print('vhdl-mode: Created testbench from interface.')

#----------------------------------------------------------------
class vhdlModeFlattenPortsCommand(sublime_plugin.TextCommand):
    """
    This command scans over the internal data structure
    for the interface and wherever there is a port or generic
    that has multiple items on the same line, it'll separate them
    onto their own lines.
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        global _interface
        _interface.flatten()
        print('vhdl-mode: Flattening ports for next paste.')

#----------------------------------------------------------------
class vhdlModeReversePortsCommand(sublime_plugin.TextCommand):
    """
    This command scans over the internal data structure
    for the interface and flips in and out/buffer modes on
    the ports.
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl") and bool(_interface.name)

    def run(self, edit):
        global _interface
        _interface.reverse()
        print('vhdl-mode: Reversing ports for next paste.')
