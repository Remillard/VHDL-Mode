"""
#----------------------------------------------------------------
# VHDL Mode Utility Module
# Contains methods that were useful in more than one location
#----------------------------------------------------------------
"""
import re
import sublime
import sublime_plugin

def move_up(self, point):
    """
    Moves up one line, attempting to maintain column position.
    """
    row, col = self.view.rowcol(point)
    if row == 0:
        return self.view.text_point(0, 0)
    else:
        return self.view.text_point(row-1, col)

#----------------------------------------------------------------------------
def move_down(self, point):
    """
    Moves down one line, attempting to maintain column position.
    """
    eof_row, eof_col = self.view.rowcol(self.view.size())
    row, col = self.view.rowcol(point)
    #print('row={} col={} eof_row={} eof_col={}'.format(x, y, eof_x, eof_y))
    if row == eof_row:
        # The size is the number of characters and the point is
        # zero indexed, so subtract one from the size.
        return self.view.size()-1
    else:
        return self.view.text_point(row+1, col)

#----------------------------------------------------------------------------
def move_to_bol(self, point):
    """
    Moves the point to the beginning of the line for searching.
    """
    x, y = self.view.rowcol(point)
    return self.view.text_point(x, 0)

#----------------------------------------------------------------------------
def move_to_1st_char(self, point):
    row, col = self.view.rowcol(point)
    #print('Row={} Col={} Char="{}"'.format(row+1, col, self.view.substr(point)))
    while self.view.substr(point) == ' ' or self.view.substr(point) == '\t':
        point += 1
        #print('Row={} Col={} Char="{}"'.format(row+1, col, self.view.substr(point)))
    return point

#----------------------------------------------------------------------------
def is_top_line(self, point):
    """
    A simple check for the top line of the file.
    """
    row, col = self.view.rowcol(point)
    return bool(row == 0)

#----------------------------------------------------------------------------
def is_end_line(self, point):
    """
    A simple check for the bottom line of the file
    (not necessarily the end of file.)
    """
    row, col = self.view.rowcol(point)
    # The size is the number of characters and the
    # point is zero indexed, so subtract on from the size
    # for the final character.
    eof_row, eof_col = self.view.rowcol(self.view.size()-1)
    return bool(row == eof_row)

#----------------------------------------------------------------------------
def set_cursor(self, point):
    """
    Just setting the point to a particular location.
    """
    self.view.sel().clear()
    self.view.sel().add(sublime.Region(point))
    self.view.show(point)

#----------------------------------------------------------------------------
def line_at_point(self, point):
    """
    Shorthand string extraction method.
    """
    return self.view.substr(self.view.line(point))

#----------------------------------------------------------------------------
def is_vhdl_file(line):
    """
    Receives a string formatted as identifying the
    language scope of the point.  Scope identifiers all
    end with the language name as the trailing clause,
    so we look for 'vhdl'
    """
    s = re.search(r'vhdl', line)
    return bool(s)

#----------------------------------------------------------------------------
def extract_scopes(self):
    """
    This method scans column zero of each line and extracts
    the scope at that point.  Aids in alignment.
    """
    scope_list = []
    point = 0
    while not is_end_line(self, point):
        scope_list.append(self.view.scope_name(point))
        point = move_down(self, point)
    # One final append for the last line.
    scope_list.append(self.view.scope_name(point))
    # Debug
    for i in range(len(scope_list)):
        print('{}: {}'.format(i, scope_list[i]))
    return scope_list

#----------------------------------------------------------------------------
def get_vhdl_setting(cmd_obj, key):
    '''
    Borrowing an idea from OdatNurd from ST forum, creating a method
    that will return the value of a key and also check to see if
    it's been overridden in project files.  Defaults are handled by
    the supplied sublime-settings file.

    This will actually work on the regular Preferences as well I think
    though might do bad things if the key doesn't exist.
    '''
    # Load the defaults, or user overridden defaults.
    vhdl_settings = sublime.load_settings('vhdl_mode.sublime-settings')
    default = vhdl_settings.get(key, None)
    # Load the view's settings
    view_settings = cmd_obj.view.settings()
    return view_settings.get(key, default)

#----------------------------------------------------------------------------
def scan_instantiations(cmd_obj):
    '''
    Obtaining a list of all regions that contain instantiation labels
    and then creating a dictionary of instantiated components and their
    associated labels.
    '''
    instances = {}
    selector = 'meta.block.instantiation entity.name.label'
    regions = cmd_obj.view.find_by_selector(selector)
    for region in regions:
        line = cmd_obj.view.substr(cmd_obj.view.full_line(region))
        line = re.sub(r'\n', '', line)
        row, col = cmd_obj.view.rowcol(region.begin())
        pattern = r'^\s*(?P<label>\w+)\s*:\s*(?:entity)?\s*((?P<lib>\w+)\.)?(?P<entity>[\w\.]+)'
        s = re.search(pattern, line, re.I)
        if s:
            if s.group('entity') in instances:
                instances[s.group('entity')].append(s.group('label'))
            else:
                instances[s.group('entity')] = [s.group('label')]
        else:
            print('vhdl-mode: Could not match instantiation on line {}'.format(row+1))
    return instances

