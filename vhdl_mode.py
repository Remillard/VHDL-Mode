"""
---------------------------------------------------------------
VHDL Mode for Sublime Text 3

This set of commands attempts to duplicate many of the features
of the Emacs vhdl-mode for the Sublime Text editor.
---------------------------------------------------------------
"""
import os
import time
import re
import textwrap
import sublime
import sublime_plugin

from . import vhdl_lang as vhdl
from . import vhdl_util as util

_interface = vhdl.Interface()

#----------------------------------------------------------------
class vhdlModeVersionCommand(sublime_plugin.TextCommand):
    """
    Prints the version to the console.
    """
    def run(self, edit):
        print("vhdl-mode: VHDL Mode Version 1.1.2")

#----------------------------------------------------------------
class vhdlModeInsertHeaderCommand(sublime_plugin.TextCommand):
    """
    This command is used to insert a predefined header into the
    current text file.
    """
    def run(self, edit):
        # Assigning this to a string to keep command shorter later.
        template = "Packages/VHDL Mode/Snippets/vhdl-header.sublime-snippet"

        # Looking for a name, first the buffer name, then the file name,
        # then finally a default value.
        buffname = self.view.name()
        longname = self.view.file_name()
        if buffname:
            filename = buffname
        elif longname:
            # Convert Windows slashes to Unix slashes (if any)
            longname = re.sub(r'\\', '/', longname)
            namechunks = longname.split('/')
            filename = namechunks[len(namechunks)-1]
        else:
            filename = '<filename>'

        # Get the other fields out of settings.
        project = util.get_vhdl_setting(self, 'vhdl-project-name')
        author = util.get_vhdl_setting(self, 'vhdl-user')
        company = util.get_vhdl_setting(self, 'vhdl-company')
        platform = util.get_vhdl_setting(self, 'vhdl-platform')
        standard = util.get_vhdl_setting(self, 'vhdl-standard')

        date = time.ctime(time.time())
        year = time.strftime("%Y",time.localtime())

        # Moving insertion point to the beginning of the file.
        bof = self.view.text_point(0,0)
        self.view.sel().clear()
        self.view.sel().add(sublime.Region(bof))
        self.view.show(bof)

        # Inserting template/snippet
        self.view.run_command("insert_snippet",
            {
                "name"     : template,
                "PROJECT"  : project,
                "FILENAME" : filename,
                "AUTHOR"   : author,
                "COMPANY"  : company,
                "CDATE"    : date,
                "MDATE"    : date,
                "YEAR"     : year,
                "PLATFORM" : platform,
                "STANDARD" : standard
            })
        print('vhdl-mode: Inserted header template.')

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
    def run(self, edit):
        # Get the current point location.
        region = self.view.sel()[0]
        original_point = region.begin()

        # Move to the beginning of the line the point is on.
        next_point = util.move_to_bol(self, original_point)

        # Construct structure
        block_str = _interface.instance()
        num_chars = self.view.insert(edit, next_point, block_str)
        print('vhdl-mode: Inserted interface as instance.')

#----------------------------------------------------------------
class vhdlModeToggleCommentRegionCommand(sublime_plugin.TextCommand):
    """
    The command analyzes the block delivered to the command
    and attempts to find the leftmost point and uses that for
    the location of the commenting characters so that it provides
    an even margin and eases removal later.

    If the starting line of the region begins with a comment,
    the command attempts to remove the comment from that and
    each subsequent line.
    """
    def run(self, edit):
        # This could theoretically run on multiple regions but
        # it's not a likely application and I'm just going to
        # worry about the first one for now.
        region = self.view.sel()[0]
        # The line method when applied to a region says it
        # returns a new region that is blocked to the
        # beginning of the line and the end of the line.
        # Exactly what I want, so let's try it.
        region = self.view.line(region)
        block = self.view.substr(region)
        lines = block.split('\n')

        # Setting the value to an absurd value for
        # comparison.  Search for the first non-
        # whitespace character to determine the
        # left margin.
        margin = 1000
        for line in lines:
            s = re.search(r'\S', line)
            if s:
                if s.start() < margin:
                    margin = s.start()

        # Check for comment on first line.  This
        # determines if we're commenting or
        # uncommenting.
        comment = True
        s = re.search(r'^\s*--', lines[0])
        if s:
            comment = False

        # Process lines.
        for index, line in enumerate(lines):
            if comment:
                lines[index] = lines[index][0:margin] + \
                               '--' + \
                               lines[index][margin:]
            else:
                # Assuming this is a commented block, we replace
                # only the first comment designator.  Weird things
                # will happen if there are uncommented lines in the
                # block and there's also inline comments.
                lines[index] = re.sub('--', '', lines[index], 1)

        # Put together into big string
        block = '\n'.join(lines)
        #print(block)
        # Replace the current region with the new region
        self.view.replace(edit, region, block)

#----------------------------------------------------------------
class vhdlModeBeautifyBufferCommand(sublime_plugin.TextCommand):
    """
    This is a Sublime Text variation of the standalone beautify
    code program.  Sets the region to the entire buffer, obtains
    the lines, then processes them and writes them back.
    """
    def run(self, edit):
        # Save original point, and convert to row col.  Beautify
        # will change the number of characters in the file, so
        # need coordinates to know where to go back to.
        original_region = self.view.sel()[0]
        original_point = original_region.begin()
        orig_x, orig_y = self.view.rowcol(original_point)

        # Create points for a region that define beginning and end.
        begin = 0
        end = self.view.size()-1

        # Slurp up entire buffer
        whole_region = sublime.Region(begin, end)
        buffer_str = self.view.substr(whole_region)
        lines = buffer_str.split('\n')

        # Get the scope for column 0 of each line.
        point = 0
        scope_list = []
        while not util.is_end_line(self, point):
            scope_list.append(self.view.scope_name(point))
            point = util.move_down(self, point)
        scope_list.append(self.view.scope_name(point))

        # Process each line
        # Left justify
        vhdl.left_justify(lines)

        # Because there are some really terrible typists out there
        # I end up having to MAKE SURE that symbols like : := <= and =>
        # have spaces to either side of them.  I'm just going to wholesale
        # replace them all with padded versions and then I remove extra space
        # later, which seems wasteful, but easier than trying to come up with
        # a ton of complicated patterns.
        vhdl.pad_vhdl_symbols(lines)

        # Remove extra blank space and convert tabs to spaces
        vhdl.remove_extra_space(lines)

        # Align
        print('vhdl-mode: Aligning symbols.')
        vhdl.align_block_on_re(lines=lines, regexp=r':(?!=)', scope_data=scope_list)
        vhdl.align_block_on_re(
            lines=lines,
            regexp=r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*',
            padside='post',
            scope_data=scope_list)
        vhdl.align_block_on_re(lines=lines, regexp=r'<|:(?==)', scope_data=scope_list)
        vhdl.align_block_on_re(lines=lines, regexp=r'=>', scope_data=scope_list)

        # Indent!
        print('vhdl-mode: Indenting.')
        vhdl.indent_vhdl(lines)

        # Post indent alignment
        vhdl.align_block_on_re(lines=lines, regexp=r'\bwhen\b', scope_data=scope_list)

        # Recombine into one big blobbed string.
        buffer_str = '\n'.join(lines)

        # Annnd if all went well, write it back into the buffer
        self.view.replace(edit, whole_region, buffer_str)

        # Put cursor back to original point (roughly)
        original_point = self.view.text_point(orig_x, orig_y)
        util.set_cursor(self, original_point)

#----------------------------------------------------------------
class vhdlModePasteAsTestbenchCommand(sublime_plugin.WindowCommand):
    """
    After copying a port, this will open a new window and
    inject the skeleton of a testbench.  Note, this isn't a
    TextCommand, but rather a WindowCommand so the run method
    has slightly different parameters.
    """
    def run(self):
        """Sublime TextCommand run method"""
        # Assigning this to a string to keep command shorter later.
        template = "Packages/VHDL Mode/Snippets/vhdl-testbench.sublime-snippet"

        tb_view = self.window.new_file()
        tb_view.assign_syntax('Packages/VHDL Mode/VHDL.sublime-syntax')
        tb_view.set_name('{}_tb.vhd'.format(_interface.name))

        signals_str = _interface.signals()
        instance_str = _interface.instance("DUT")

        # Inserting template/snippet
        tb_view.run_command("insert_snippet",
            {
                "name"     : template,
                "ENAME"    : _interface.name,
                "SIGNALS"  : signals_str,
                "INSTANCE" : instance_str
            })
        tb_view.run_command("vhdl_mode_insert_header")
        print('vhdl-mode: Created testbench from interface.')

#----------------------------------------------------------------
class UpdateLastUpdatedCommand(sublime_plugin.TextCommand):
    """
    Finds the last updated field in the header and updates the time
    in the field.
    """
    def run(self, edit):
        """Sublime Text plugin run method."""
        # Note, if one changes the header, this might need to change too.
        pattern = '-- Last update :'
        region = self.view.find(pattern, 0)
        #print('Region Diagnostics')
        #print('------------------')
        #print('Begin: {}'.format(region.begin()))
        #print('End:   {}'.format(region.end()))
        #print('Empty? {}'.format(region.empty()))
        if not region.empty():
            region = self.view.line(region)
            date = time.ctime(time.time())
            new_mtime = '-- Last update : {}'.format(date)
            self.view.replace(edit, region, new_mtime)
            print('vhdl-mode: Updated last modified time.')
        else:
            print('vhdl-mode: No last modified time field found.')

#----------------------------------------------------------------
class UpdateModifiedTimeOnSave(sublime_plugin.EventListener):
    """
    Watches for a save event and updates the Last update
    field in the header.
    """
    def on_pre_save(self, view):
        """
        Gets passed the view that is being saved and scans for the
        Last updated field.
        """
        # MUST CHECK FOR VHDL FILE TYPE (otherwise it
        # starts executing on this very source file which
        # is problematic!)
        if util.is_vhdl_file(view.scope_name(0)):
            view.run_command("update_last_updated")

#----------------------------------------------------------------
class vhdlModeScopeSnifferCommand(sublime_plugin.TextCommand):
    """
    My own scope sniffing command that prints to
    console instead of a popup window.
    """
    def run(self, edit):
        """ST3 Run Method"""
        region = self.view.sel()[0]
        sniff_point = region.begin()
        print('vhdl-mode: {}'.format(self.view.scope_name(sniff_point)))

#----------------------------------------------------------------
class vhdlModeInsertCommentLine(sublime_plugin.TextCommand):
    """
    This should insert a line out to the margine (80 characters)
    starting where the point is.  This is intended to run after
    the user types '---' (see keybindings)
    """
    def run(self, edit):
        """Standard TextCommand Run method"""
        # Get the current point.
        region = self.view.sel()[0]
        original_point = region.begin()
        point_r, point_c = self.view.rowcol(original_point)
        # Figure out if any tab characters were used.
        line = self.view.substr(self.view.line(original_point))
        numtabs = line.count('\t')
        # Get the current tab size
        tabsize = util.get_vhdl_setting(self, 'tab_size')
        # Create string of correct amount of dashes.  A tab consumed
        # one character but generates tabsize-1 space.
        line = '-'*(80-point_c-(tabsize-1)*numtabs)
        num_chars = self.view.insert(edit, original_point, line)
        print('vhdl-mode: Inserted comment line.')

#----------------------------------------------------------------
class vhdlModeInsertCommentBox(sublime_plugin.TextCommand):
    """
    This should insert a box out to the margin (80 characters)
    starting where the point is, and taking into account tabs.
    This is intended to run after the user types '----' (see
    keybindings)
    """
    def run(self, edit):
        """Standard TextCommand Run method"""
        # Get the current point.
        region = self.view.sel()[0]
        original_point = region.begin()
        point_r, point_c = self.view.rowcol(original_point)
        # Figure out if any tab characters were used.
        line = self.view.substr(self.view.line(original_point))
        numtabs = line.count('\t')
        # Get the current tab size
        tabsize = util.get_vhdl_setting(self, 'tab_size')
        # Create string of correct amount of dashes.  A tab consumed
        # one character but generates tabsize-1 space.
        line = '-'*(80-point_c-(tabsize-1)*numtabs)
        # Create snippet object.
        snippet = line + '\n' + '-- $0' + '\n' + line + '\n'
        # Inserting template/snippet
        self.view.run_command("insert_snippet",
            {
                "contents" : snippet
            })

#----------------------------------------------------------------
class vhdlModeSettingSniffer(sublime_plugin.TextCommand):
    '''
    Creating a command to check settings in various
    contexts
    '''
    def run(self, edit):
        '''
        Standard TextCommand Run Method
        '''
        vhdl_settings = sublime.load_settings('vhdl_mode.sublime-settings')
        keys = ['vhdl-user',
                'vhdl-company',
                'vhdl-project-name',
                'vhdl-platform',
                'vhdl-standard']
        print('Package Settings')
        for key in keys:
            print('vhdl-mode: {}: {}'.format(key, vhdl_settings.get(key)))

        print('View Settings')
        for key in keys:
            print('vhdl-mode: {}: {}'.format(key, util.get_vhdl_setting(self, key)))

        print('Preference Settings')
        print('vhdl-mode: {}: {}'.format('tab_size', util.get_vhdl_setting(self, 'tab_size')))


