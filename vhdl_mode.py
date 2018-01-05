"""
VHDL Mode for Sublime Text 3

This package attempts to recreate to some level of fidelity the features
in the vhdl-mode in Emacs.
"""
import os
import time
import re
import textwrap
import sublime
import sublime_plugin

from . import vhdl_lang as vhdl
from . import vhdl_util as util

#----------------------------------------------------------------
class vhdlModeVersionCommand(sublime_plugin.TextCommand):
    """
    Prints the version to the console.
    """
    def run(self, edit):
        print("vhdl-mode: VHDL Mode Version 1.7.12")

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
        mtime_prefix = util.get_vhdl_setting(self, 'vhdl-modified-time-string')
        use_copyright = util.get_vhdl_setting(self, 'vhdl-use-copyright-block')
        use_revision = util.get_vhdl_setting(self, 'vhdl-use-revision-block')
        copyright_list = util.get_vhdl_setting(self, 'vhdl-copyright-block')
        revision_list = util.get_vhdl_setting(self, 'vhdl-revision-block')

        # Get the current time and create the modified time string.
        date = time.ctime(time.time())
        year = time.strftime("%Y",time.localtime())
        mod_time = mtime_prefix + date

        # Create the copyright block and revision block.  Both need
        # prefixed newlines because they are optional and the
        # snippet field is at the end of the preceding line.
        if use_copyright:
            copyright = '\n'.join(copyright_list)
            copyright = re.sub(r'\${YEAR}', year, copyright)
            copyright = re.sub(r'\${COMPANY}', company, copyright)
            copyright = '\n' + copyright
        else:
            copyright = ''
        if use_revision:
            revision = '\n'.join(revision_list)
            revision = '\n' + revision
        else:
            revision = ''

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
                "MODIFIED_TIME_STRING" : mod_time,
                "MDATE"    : date,
                "YEAR"     : year,
                "PLATFORM" : platform,
                "STANDARD" : standard,
                "COPYRIGHT_BLOCK" : copyright,
                "REVISION_BLOCK" : revision
            })
        print('vhdl-mode: Inserted header template.')

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

        # Indent!  Get some settings first.
        use_spaces = util.get_vhdl_setting(self, 'translate_tabs_to_spaces')
        tab_size = util.get_vhdl_setting(self, 'tab_size')
        print('vhdl-mode: Indenting.')
        vhdl.indent_vhdl(lines=lines, initial=0, tab_size=tab_size,
                         use_spaces=use_spaces)

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
class vhdlModeUpdateLastUpdatedCommand(sublime_plugin.TextCommand):
    """
    Finds the last updated field in the header and updates the time
    in the field.
    """
    def run(self, edit):
        """Sublime Text plugin run method."""
        # Note, if one changes the header, this might need to change too.
        pattern = util.get_vhdl_setting(self, 'vhdl-modified-time-string')
        region = self.view.find(pattern, 0)
        #print('Region Diagnostics')
        #print('------------------')
        #print('Begin: {}'.format(region.begin()))
        #print('End:   {}'.format(region.end()))
        #print('Empty? {}'.format(region.empty()))
        if not region.empty():
            region = self.view.line(region)
            date = time.ctime(time.time())
            new_mtime = pattern + '{}'.format(date)
            self.view.replace(edit, region, new_mtime)
            print('vhdl-mode: Updated last modified time.')
        else:
            print('vhdl-mode: No last modified time field found.')

#----------------------------------------------------------------
class vhdlModeUpdateModifiedTimeOnSave(sublime_plugin.EventListener):
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
            view.run_command("vhdl_mode_update_last_updated")

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
        print('Preference Settings')
        print('vhdl-mode: {}: {}'.format('tab_size', util.get_vhdl_setting(self, 'tab_size')))
        print('vhdl-mode: {}: {}'.format('translate_tabs_to_spaces', util.get_vhdl_setting(self, 'translate_tabs_to_spaces')))
        vhdl_settings = sublime.load_settings('vhdl_mode.sublime-settings')
        keys = ['vhdl-user',
                'vhdl-company',
                'vhdl-project-name',
                'vhdl-platform',
                'vhdl-standard',
                'vhdl-modified-time-string',
                'vhdl-use-copyright-block',
                'vhdl-use-revision-block',
                'vhdl-copyright-block',
                'vhdl-revision-block']
        print('Package Settings')
        for key in keys:
            print('vhdl-mode: {}: "{}"'.format(key, vhdl_settings.get(key)))

        print('View Settings')
        for key in keys:
            print('vhdl-mode: {}: {}'.format(key, util.get_vhdl_setting(self, key)))



