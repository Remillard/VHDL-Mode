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

#from threading import Thread
from . import vhdl_lang as vhdl
from . import vhdl_util as util


#-------------------------------------------------------------------------------
class vhdlModeVersionCommand(sublime_plugin.TextCommand):
    """
    Prints the version to the console.
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

    def run(self, edit):
        print("vhdl-mode: VHDL Mode Version 1.8.11")


#-------------------------------------------------------------------------------
class vhdlModeInsertHeaderCommand(sublime_plugin.TextCommand):
    """
    This command is used to insert a predefined header into the
    current text file.
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

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
        linesize = util.get_vhdl_setting(self, 'vhdl-line-length')
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

        # Set the string to dynamically replace the line field to the chosen
        # line length.
        linestr = '-'*linesize

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
            copyright = re.sub(r'\${LINE}', linestr, copyright)
            copyright = '\n' + copyright
        else:
            copyright = ''
        if use_revision:
            revision = '\n'.join(revision_list)
            revision = re.sub(r'\${LINE}', linestr, revision)
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
                "REVISION_BLOCK" : revision,
                "LINE"     : linestr
            })
        print('vhdl-mode: Inserted header template.')


#-------------------------------------------------------------------------------
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
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

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


#-------------------------------------------------------------------------------
class vhdlModeBeautifyBufferCommand(sublime_plugin.TextCommand):
    """
    This is a Sublime Text variation of the standalone beautify
    code program.  Sets the region to the entire buffer, obtains
    the lines, then processes them and writes them back.
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

    def run(self, edit):
        # Finding the current view and location of the point.
        x, y = self.view.viewport_position()
        row, col = self.view.rowcol(self.view.sel()[0].begin())
        #print('vhdl-mode: x={}, y={}, row={}, col={}'.format(x, y, row, col))

        # Create points for a region that define beginning and end.
        begin = 0
        end = self.view.size()-1

        # Slurp up entire buffer and create CodeBlock object
        whole_region = sublime.Region(begin, end)
        buffer_str = self.view.substr(whole_region)
        cb = vhdl.CodeBlock.from_block(buffer_str)

        # Get the scope for each line.  There's commented out code here for
        # which scope to get first column of the line, and first character of
        # the line.  The first column seems to give the best results, though
        # there are anomalies (like a when <choice> => followed by a line that
        # uses => as a discrete member group assignment).
        point = 0
        scope_list = []
        while not util.is_end_line(self, point):
            #point = util.move_to_1st_char(self, point)
            scope_list.append(self.view.scope_name(point))
            #point = util.move_to_bol(self, point)
            point = util.move_down(self, point)
        scope_list.append(self.view.scope_name(point))

        # Process the block of code.  Prep pads symbols and removes extra
        # spaces.
        cb.prep()
        cb.left_justify()

        # Do the initial alignment after justification.
        print('vhdl-mode: Pre-indent symbol alignment.')
        cb.align_symbol(r':(?!=)', 'pre', scope_list)
        cb.align_symbol(r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post', scope_list)
        cb.align_symbol(r'<(?==)|:(?==)', 'pre', scope_list)
        cb.align_symbol(r'=>', 'pre', scope_list)

        # Indent!  Get some settings first.
        use_spaces = util.get_vhdl_setting(self, 'translate_tabs_to_spaces')
        tab_size = util.get_vhdl_setting(self, 'tab_size')
        print('vhdl-mode: Indenting.')
        cb.indent_vhdl(0, tab_size, use_spaces)

        # Post indent alignment
        print('vhdl-mode: Post-indent symbol alignment.')
        # This is mostly for the case when stuff, also for the concurrent
        # conditional assignment.
        cb.align_symbol(r'=>', 'pre', scope_list, True)
        cb.align_symbol(r'<(?==)|:(?==)', 'pre', scope_list, True)
        cb.align_symbol(r'\bwhen\b', 'pre', scope_list)
        print('vhdl-mode: Aligning comments.')
        cb.align_comments(tab_size, use_spaces)

        # Recombine into one big blobbed string.
        buffer_str = cb.to_block()

        # Annnd if all went well, write it back into the buffer
        self.view.replace(edit, whole_region, buffer_str)
        # New replacement routine that does not trigger Sublime's
        # repainting mechanism that seems to be triggered by using
        # self.view.replace()
        #self.view.run_command("select_all")
        #self.view.run_command("left_delete")
        #self.view.run_command("append", {"characters": buffer_str})

        # Restore the view.
        original_point = self.view.text_point(row, col)
        util.set_cursor(self, original_point)
        # Trying out another method for handling the viewport.  You can have
        # a zero value for set_timeout() delay so this executes after the
        # command exits.
        restore = lambda: self.view.set_viewport_position((x, y), False)
        sublime.set_timeout(restore, 1)
        #self.view.set_viewport_position((x, y), False)


#-------------------------------------------------------------------------------
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


#-------------------------------------------------------------------------------
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


#-------------------------------------------------------------------------------
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


#-------------------------------------------------------------------------------
class vhdlModeInsertCommentLine(sublime_plugin.TextCommand):
    """
    This should insert a line out to the margin (80 characters)
    starting where the point is.  This is intended to run after
    the user types '---' (see keybindings)
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

    def run(self, edit):
        """Standard TextCommand Run method"""
        # Get the current point.
        region = self.view.sel()[0]
        original_point = region.begin()
        point_r, point_c = self.view.rowcol(original_point)
        # Figure out if any tab characters were used.
        line = self.view.substr(self.view.line(original_point))
        numtabs = line.count('\t')
        # Get the current tab size and line length.
        tabsize = util.get_vhdl_setting(self, 'tab_size')
        linesize = util.get_vhdl_setting(self, 'vhdl-line-length')
        # Create string of correct amount of dashes.  A tab consumed
        # one character but generates tabsize-1 space.
        numdash = linesize-point_c-(tabsize-1)*numtabs
        if numdash <= 2:
            print('vhdl-mode: Warning: Line length setting violation.  Setting number of dashes to 2.')
            numdash = 2
        line = '-'*numdash
        num_chars = self.view.insert(edit, original_point, line)
        print('vhdl-mode: Inserted comment line.')


#-------------------------------------------------------------------------------
class vhdlModeInsertCommentBox(sublime_plugin.TextCommand):
    """
    This should insert a box out to the margin (80 characters)
    starting where the point is, and taking into account tabs.
    This is intended to run after the user types '----' (see
    keybindings)
    """
    def is_visible(self):
        return self.view.match_selector(0, "source.vhdl")

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
        linesize = util.get_vhdl_setting(self, 'vhdl-line-length')
        # Create string of correct amount of dashes.  A tab consumed
        # one character but generates tabsize-1 space.
        numdash = linesize-point_c-(tabsize-1)*numtabs
        if numdash <= 2:
            print('vhdl-mode: Warning: Line length setting violation.  Setting number of dashes to 2.')
            numdash = 2
        line = '-'*numdash
        # Create snippet object.
        snippet = line + '\n' + '-- $0' + '\n' + line + '\n'
        # Inserting template/snippet
        self.view.run_command("insert_snippet",
            {
                "contents" : snippet
            })
        print('vhdl-mode: Inserted comment box.')


#-------------------------------------------------------------------------------
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
        keys = ['vhdl-line-length',
                'vhdl-user',
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


#-------------------------------------------------------------------------------
class vhdlModeViewportSniffer(sublime_plugin.TextCommand):
    def run(self, edit):
        x, y = self.view.viewport_position()
        print('vhdl-mode: Viewport X: {} Y: {}'.format(x,y))
        #self.view.set_viewport_position((0, y), False)


