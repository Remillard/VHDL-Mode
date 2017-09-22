"""
----------------------------------------------------------------
 VHDL Language Module.

 Defines class structures and methods for identifying and
 manipulating text structures, and extracting and replicating
 lexical elements.
----------------------------------------------------------------
"""
import re
import collections

_debug = False


# ---------------------------------------------------------------------------
def debug(string):
    """
    Some of these functions ended up with a lot of debug output for analyzing
    processing.  I needed a way to turn it on and off.
    """
    if _debug:
        print(string)


# ---------------------------------------------------------------------------
def left_justify(lines):
    """
    Method removes all whitespace at the beginning of a line.
    """
    for i in range(len(lines)):
        lines[i] = re.sub(r"^\s*", '', lines[i])


# ---------------------------------------------------------------
def check_for_comment(line):
    """
    Simple method that will return False if a line does not
    begin with a comment, otherwise True.  Mainly used for
    disabling alignment.
    """
    pattern = r'^\s*--'
    p = re.compile(pattern, re.IGNORECASE)
    s = re.search(p, line)
    return bool(s)


# ---------------------------------------------------------------
def strip_comments(line):
    """
    Removes any inline comment from the line, accounting for
    comment symbols inside of a text string.  Does not account
    for multiline commenting.
    """
    str_p = r'".*?"'
    comment_p = r'--.*$'
    # First check for an inline string.  Will only handle one.
    str_s = re.search(str_p, line)
    # If a string exists, then we break up into searching the
    # beginning and end separately.  Otherwise, just a basic
    # whole line search is fine.
    if str_s:
        comment_s = re.search(comment_p, line[:str_s.start()])
        if comment_s:
            return line[:comment_s.start()]
        else:
            comment_s = re.search(comment_p, line[str_s.end():])
            if comment_s:
                return line[:str_s.end()+comment_s.start()]
            else:
                return line
    else:
        comment_s = re.search(comment_p, line)
        if comment_s:
            return line[:comment_s.start()]
        else:
            return line

# ---------------------------------------------------------------------------
def pad_vhdl_symbols(lines):
    """
    Ensuring that special symbols that later we'll align on have a minimum
    leading and trailing space.  Aids correct alignment.  Leaving it at
    assignment and languaage delimeters for now.
    """
    for i in range(len(lines)):
        if not check_for_comment(lines[i]):
            lines[i] = re.sub(':(?!=)', ' : ',  lines[i])
            lines[i] = re.sub(':=',     ' := ', lines[i])
            lines[i] = re.sub('<=',     ' <= ', lines[i])
            lines[i] = re.sub('=>',     ' => ', lines[i])


# ---------------------------------------------------------------------------
def remove_extra_space(lines):
    """
    Method that takes out extra whitespace in a line.  Avoids
    full line comments and attempts to avoid in-line comments.
    """
    for i in range(len(lines)):
        if not check_for_comment(lines[i]):
            # Check and save off inline comments.
            cs = re.search(r'--.*$', lines[i])
            if cs:
                comment = lines[i][cs.start():]
                code = lines[i][0:cs.start()]
            else:
                comment = ''
                code = lines[i]
            # Compress space in code portion of the line.
            code = re.sub(r'\s+', ' ', code)
            code = re.sub(r'\t', ' ', code)
            lines[i] = code + comment


# ---------------------------------------------------------------
def analyze_parens(line, count=[0, 0]):
    """
    Method is passed a line, and a current count
    (defaulting to 0) as a list of open and closed.
    Returns a list structure containing the incremented
    count as a list, and then a list of the offset
    locations of the unmatched parens
    """
    open_paren = []
    close_paren = []
    for i in range(len(line)):
        if line[i] == '(':
            open_paren.append(i)
        elif line[i] == ')':
            if open_paren:
                open_paren.pop()
            else:
                close_paren.append(i)
    count = [count[0]+len(open_paren), count[1]+len(close_paren)]
    return [count, open_paren, close_paren]


# ---------------------------------------------------------------
def parens_balanced(count):
    """
    Short method to check the values in the parenthesis count
    list.
    """
    return bool(count[0] == count[1])


# ---------------------------------------------------------------
def align_block_on_re(lines, regexp, padside='pre', scope_data=None):
    """
    Receives a list of individual lines.  Scans each line looking
    for the provided lexical pattern that should align on
    adjoining lines. Once a pattern is found, record the line index
    and pattern location.  For each subsequent line that also
    identifies the pattern, add the line index and pattern location.
    When a line is identified that does not have the pattern, find
    the line in the list with the most leftmost symbol, and then
    iterate through the list of affected lines and pad on the side
    declared (anything that is not 'post' is prepend because that's
    most common.)

    Alignment should happen when the strings are left justified
    so that it doesn't need to know about the spacing.

    This is intended to be run in several passes on several patterns
    which is why it takes the regexp as a parameter.

    Added some blacklist words, otherwise you can get some matching
    between conditionals and assignments and other nonsense.

    TODO: Add scope checking for alignment instead of ban list
    when provided.
    """
    ban_raw = [
        r':\s+process\b',
        r'\bif\b',
        r'\bthen\b',
    ]
    ban_list = []
    for pattern in ban_raw:
        ban_list.append(re.compile(pattern, re.IGNORECASE))

    prior_scope = ""
    match_data = []
    for i in range(len(lines)):

        # Check for banned lines we don't even want to think about.
        banned = False
        for pattern in ban_list:
            ban_search = re.search(pattern, lines[i])
            if ban_search:
                banned = True
                break

        # Scan for the aligning pattern
        s = re.search(regexp, lines[i])

        # First decide if based on lack of pattern, scope change, or
        # a banned line or end of file whether we should process any
        # currently existing match list.
        scope_switch = False
        if scope_data is not None:
            if scope_data[i] != prior_scope:
                scope_switch = True
            else:
                scope_switch = False

        # A special check for the last line to add to the group, otherwise
        # we process before we can evaluate that line.
        if s and (i == len(lines)-1) and not check_for_comment(lines[i]) and not banned:
            if padside == 'post':
                match_data.append((i, s.end()))
            else:
                match_data.append((i, s.start()))

        if not s or scope_switch or (i == len(lines)-1) or banned:
            if len(match_data) > 1:
                # Scan for max value and check to see if extra space needed
                # due to lack of preceding space.
                maxpos = 0
                for pair in match_data:
                    if pair[1] > maxpos:
                        maxpos = pair[1]
                        if lines[pair[0]][pair[1]-1] != ' ':
                            maxpos = maxpos + 1
                # Now insert spaces on each line (max-current+1)
                # to make up the space.
                for pair in match_data:
                    lines[pair[0]] = lines[pair[0]][0:pair[1]] + \
                                     ' '*(maxpos-pair[1]) + \
                                     lines[pair[0]][pair[1]:]
            # No match for more than one line so erase match
            # data
            match_data = []

        # Next, if this line has an alignment symbol in it (and not banned)
        # start adding data again.
        if s and not check_for_comment(lines[i]) and not banned:
            # If we find a match, record the line and
            # location but do nothing else.
            #print("Match on Line: {} Start:'{}' Stop:'{}'".\
            #       format(line_num, lines[line_num][0:s.start()],\
            #              lines[line_num][s.start():]))
            if padside == 'post':
                match_data.append((i, s.end()))
            else:
                match_data.append((i, s.start()))

        # Make sure we save the current scope off before looping
        if scope_data is not None:
            prior_scope = scope_data[i]


# ---------------------------------------------------------------
def indent_vhdl(lines, initial=0, tab_size=4, use_spaces=True):
    """
    This method takes a list of lines of source code, that have
    been left justified, and attempts impose indentation rules
    upon it for beautification.
    """
    # 3rd Iteration of how the ruleset is formatted.  Now it
    # is comprised of two dictionaries.  The first is an
    # collections.OrderedDict(ionary) because I scan through
    # this item by item and I wish to preserve some sort of
    # priority.  This dictionary is of lexical scope beginning
    # items.  Each item is a dictionary (normal) with the
    # following keys:
    #   pattern - The regexp pattern identifying the element.
    #   indent_rule - A tuple comprising the indent for the
    #       current line and the next line.
    #   close_rule - A tuple of tuples, possibly only one
    #       comprising how to deal with internals.  Most of
    #       the time it's a single element, however things
    #       like procedures have a couple different ways
    #       they can end.
    #   solo_flag - A boolean value indicating whether we
    #       apply the ending/solo rule or just deindent
    #       immediately.
    #   close_offset - An integer value that applies an
    #       offset to the closing current line, used for
    #       the 'map' elements.
    #
    # The second dictionary is shorter and is comprised of
    # lexical scope ending items.
    #
    # Workaround for Python 3.3.6 inside of ST3.  Passing
    # dictionary elements in during instantiation does not
    # preserve order because at that point, method arguments
    # are passed as a regular dictionary.  Python 3.6
    # will pass arguments retaining order which is why it
    # worked with the command line tool.  So, right now,
    # using OrderedDict is not useful.  I will turn
    # open_rules into a regular dictionary, and then create
    # a list of keys that can be iterated over to create
    # the order.

    key_list = ['entity', 'component', 'package', 'genmap', 'portmap',
        'generic', 'port', 'config', 'architecture', 'type', 'constant',
        'procedure', 'function', 'process', 'ifthen', 'solothen',
        'elseclause', 'elsifclause', 'loop', 'generate', 'case', 'casewhen',
        'begin', 'assertion', 'assignment', 'default']

    open_rules = {
        'entity': {
            'pattern': r'^entity\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'component': {
            'pattern': r'^\s*(?<!end )\bcomponent\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'package': {
            'pattern': r'(?<!end )\bpackage\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'genmap': {
            'pattern': r'\bgeneric map\b',
            'indent_rule': (1, 1),
            'close_rule': (
                ('close_paren', None),
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'portmap': {
            'pattern': r'\bport map\b',
            'indent_rule': (1, 1),
            'close_rule': (
                ('close_semi', None),
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'generic': {
            'pattern': r'\bgeneric\b',
            'indent_rule': (0, 0),
            'close_rule': (
                ('close_semi', None),
            ),
            'solo_flag': True,
            'close_offset': 0
        },

        'port': {
            'pattern': r'\bport\b',
            'indent_rule': (0, 0),
            'close_rule': (
                ('close_semi', None),
            ),
            'solo_flag': True,
            'close_offset': 0
        },

        'config': {
            'pattern': r'(?<!end )configuration\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'architecture': {
            'pattern': r'^architecture\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'type': {
            'pattern': r'^\btype\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('semicolon', None),
                ('record', 'record')
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'constant': {
            'pattern': r'^\bconstant\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('semicolon', None),
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'procedure': {
            'pattern': r'^(?<!end )\bprocedure\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('semicolon', None),
                ('isclause', 'isclause')
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'function': {
            'pattern': r'^(?<!end )(?:(pure|impure) )?function\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('function_semi', None),
                ('function_is', 'function_is')
            ),
            'solo_flag': True,
            'close_offset': 1
        },

        'process': {
            'pattern': r'(?<!end )(?<!end postponed )\bprocess\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'ifthen': {
            'pattern': r'(?<!end )\bif\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'solothen': {
            'pattern': r'^then\b',
            'indent_rule': (-1, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        'elseclause': {
            'pattern': r'^else\b',
            'indent_rule': (-1, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        'elsifclause': {
            'pattern': r'^elsif\b',
            'indent_rule': (-1, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        'loop': {
            'pattern': r'(?<!end )\bloop\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'generate': {
            'pattern': r'(?<!end )\bgenerate\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'case': {
            'pattern': r'(?<!end )\bcase\b',
            'indent_rule': (0, 2),
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'close_offset': 0
        },

        'casewhen': {
            'pattern': r'^when\b',
            'indent_rule': (-1, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        'begin': {
            'pattern': r'\bbegin\b',
            'indent_rule': (-1, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        'assertion': {
            'pattern': r'^assert\b',
            'indent_rule': (0, 1),
            'close_rule': (
                ('semicolon', None),
            ),
            'solo_flag': True,
            'close_offset': 0
        },

        'assignment': {
            'pattern': r' <= ',
            'indent_rule': (0, 1),
            'close_rule': (
                ('semicolon', None),
            ),
            'solo_flag': True,
            'close_offset': 0
        },

        'default': {
            'pattern': r'.*',
            'indent_rule': (0, 0),
            'close_rule': None,
            'solo_flag': False,
            'close_offset': 0
        },

        # Keys past here are only dummies for continuing
        # a statement whose lexical possibilities branch.
        # They will not be scanned as a primary opener
        # because default will catch everything not matched.
        # Still need the closing result parameters.  These
        # guys have one more parameter that others don't have
        # which is a start_offset.  Because they are in
        # a special class that's not a proper open, nor a
        # proper close, funny things happen on the line
        # they're on.

        # 'is' ends a procedure/function in the same place
        # as a semicolon, but sets up another closing
        #
        # Maintaining these entries at the bottom of the list
        # in case I can ever go back to OrderedDict.
        # Excluding them from the key_list iteration does
        # the same thing as the default matching everything.
        'isclause': {
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': True,
            'start_offset': -1,
            'close_offset': 0
        },

        'function_is': {
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': True,
            'start_offset': -1,
            'close_offset': 0
        },

        # 'record' is a branch off of type.
        'record': {
            'close_rule': (
                ('endclause', None),
            ),
            'solo_flag': False,
            'start_offset': 0,
            'close_offset': 0
        }
    }

    close_rules = {
        'semicolon': r';',
        'close_paren': r'\)',
        'close_semi': r'\);',
        'endclause': r'\bend\s?(\w+)?\s?(\w+)?\s?(\w+)?\s?',
        'isclause': r'\bis\b',
        'record': r'\brecord\b',
        'function_is': r'\breturn\s+\w+\s+is',
        'function_semi': r'\breturn\s+\w+;'
    }

    # Initialize the indent indexes.
    # closing_stack is using deque() and each element is:
    # 0. The key name matched.
    # 1. The current indent level.
    # Since it's a stack, we're always referencing element 0 (top).
    current_indent = initial
    next_indent = current_indent
    paren_count = [0, 0]
    closing_stack = collections.deque()
    unbalance_flag = False
    # Set the indent to tabs or spaces here
    if use_spaces:
        indent_char = ' '*tab_size
    else:
        indent_char = '\t'

    # Scan the lines.
    for i in range(len(lines)):
        # Strip any comment from the line before analysis.
        # TODO: Need to avoid comment triggers inside of strings.
        #line = re.sub('--.*$', '', lines[i])
        line = strip_comments(lines[i])
        # Figure out the line's parentheses
        paren_count, open_paren_pos, close_paren_pos = \
            analyze_parens(line, paren_count)

        debug('{}: ci={} ni={} : {}'.format(i, current_indent,
                                            next_indent, lines[i]))

        ############################################################
        # Modification Rules
        # Priority 1: Keywords
        for key in key_list:
            rule = open_rules[key]
            key_search = re.search(rule['pattern'], line, re.IGNORECASE)
            if key_search:
                debug('{}: Evaluation line: {}'.format(i, line))
                debug('{}: Evaluation pattern: {}'.format(i, rule['pattern']))
                debug('{}: Type: {}'.format(i, key))
                # If an ending type is noted, push the key onto the
                # stack.
                if rule['close_rule'] is not None:
                    closing_stack.appendleft([key, current_indent])
                # Apply the current and next indent values to
                # the current values.
                current_indent += rule['indent_rule'][0]
                next_indent += rule['indent_rule'][1]
                break

        # Priority 2: Unbalanced Parenthesis
        # Unbalanced parenthesis rules.  The line where an unbalanced paren
        # begins is not modified, however for every line after that while we are
        # unbalanced, indent one additional level to the current line (but not the
        # next because we don't want to keep incrementing outwards.)  When balance
        # is restored, reset the flag.
        if unbalance_flag:
            debug('{}: Unbalanced indenting.'.format(i))
            current_indent += 1
        unbalance_flag = not parens_balanced(paren_count)

        # Special: Closing Item Reset
        # Scan the line for ending key if one exists. If
        # parentheses are balanced and then ending key has been found
        # then reset the current and next indent level to this state.
        # The evaluate flag is used because a branching lexical
        # structure was discovered and the line needs to be rescanned.
        if len(closing_stack):
            eval_line = True
            while eval_line:
                debug('{}: depth={} top={}'.format(i, len(closing_stack), closing_stack[0]))
                # Assume that we will traverse only once, and set the flag
                # to false.  If we need to rescan, the flag will be set
                # true.
                eval_line = False

                # Since the closing rule pattern could be multiple patterns, we have to scan
                # through that item, referencing into the close_rules dictionary for the
                # pattern.  Assigning the rule tuple to another name to stop the madness
                # of indirection.
                stack_key, stack_indent = closing_stack[0]
                rules = open_rules[stack_key]['close_rule']

                # Step through and search for the end pattern.
                for close_key, result in rules:
                    debug('{}: Evaluation line: {}'.format(i, line))
                    debug('{}: Evaluation pattern: {}'.format(i, close_rules[close_key]))
                    close_search = re.search(close_rules[close_key], line, re.IGNORECASE)
                    if close_search and parens_balanced(paren_count):
                        # We've found a match and are in a balanced state.
                        debug('{}: Found closing match to {}'.format(i, stack_key))
                        if result is not None:
                            # We have found a continuation of the structure.
                            # Pop off the top of the stack, then append the new
                            # key to the top of the stack and re-evaluate.
                            debug('{}: Continuation found.  Re-evaluating for {}'.format(i, result))
                            closing_stack.popleft()
                            closing_stack.appendleft([result, stack_indent])
                            # Need to do a solo line check, mainly for those is clauses.
                            if open_rules[result]['solo_flag']:
                                solo_search = re.search(r'^\)?\s?'+close_rules[close_key], line, re.IGNORECASE)
                                if solo_search:
                                    # Unindent this line most likely
                                    debug('{}: Solo intermediate found.'.format(i))
                                    current_indent += open_rules[result]['start_offset']
                            eval_line = True
                        else:
                            # This is the endpoint of the structure.
                            # Behavior changes based on the solo flag
                            if open_rules[stack_key]['solo_flag']:
                                # Solo flag rules means we only apply the closing
                                # rule to the current line if the symbol is alone
                                # on a line, otherwise we apply the closing rule
                                # to the following line.
                                # Scan the line again to check for the beginning
                                # of the line variation.  (Small alteration to
                                # check for an paren in the case of endclauses
                                # that might not have the built-in paren)
                                debug('{}: Using solo line rule.'.format(i))
                                solo_search = re.search(r'^\)?\s?'+close_rules[close_key], line, re.IGNORECASE)
                                if solo_search:
                                    # Revert on this line
                                    debug('{}: Solo closing found here.'.format(i))
                                    current_indent = stack_indent + open_rules[stack_key]['close_offset']
                                    next_indent = stack_indent
                                else:
                                    debug('{}: Close is not alone on this line.'.format(i))
                                    # Revert on the next line
                                    next_indent = stack_indent
                            else:
                                debug('{}: Regular ending rule.'.format(i))
                                # No special rule handling.  Revert on this line.
                                current_indent = next_indent = stack_indent
                            # Pop the top of the stack and we're done with evaluating
                            # closing strings.
                            closing_stack.popleft()

        # Modify the line here.
        lines[i] = indent_char*current_indent+lines[i]
        debug('{}: ci={} ni={} : {} \n'.format(i, current_indent, next_indent, lines[i]))
        # Set current for next line.
        current_indent = next_indent


# ---------------------------------------------------------------
class Port():
    """
    This is the class of ports and ways to manipulate ports.
    A port consists of a name (string), a mode (optional) (string),
    and a type (string).
    """
    def __init__(self, port_str):
        self.name = ""
        self.mode = ""
        self.type = ""
        self.success = False
        self.parse_str(port_str)

    def parse_str(self, port_str):
        """Searches a string for the port fields."""
        port_pattern = r'\s?(?P<name>.*?)\s?(?::)\s?(?P<mode>in\b|out\b|inout\b|buffer\b)?\s?(?P<type>.*)'
        pp = re.compile(port_pattern, re.IGNORECASE)
        s = re.search(pp, port_str)
        if s:
            self.name = s.group('name')
            self.mode = s.group('mode')
            self.type = s.group('type')
            # Sometimes the type has a trailing space.  Eliminating it.
            if self.type[-1] == ' ':
                self.type = self.type[:-1]
            self.success = True
        else:
            print('vhdl-mode: Could not parse port string.')
            self.success = False

    def print_as_signal(self):
        """Returns a string with the port formatted for a signal."""
        # Trailing semicolon provided by calling routine.
        line = 'signal {} : {}'.format(self.name, self.type)
        #print(line)
        return line

    def print_as_portmap(self):
        """Returns a string with the port formatted as a portmap."""
        # A port name might be a comma separated list which
        # needs to be split into several lines.
        # Remove any spaces.
        compact = re.sub(r'\s', '', self.name)
        # Split at commas
        names = compact.split(',')
        lines = []
        for name in names:
            lines.append('{} => {}'.format(name, name))
        # This is a departure from the other "print as" methods as
        # it returns a list instead of a string.
        return lines

    def print_as_port(self):
        """Returns a string with the port formatted as a port."""
        # Trailing semicolon provided by calling routine.
        line = '{} : {} {}'.format(self.name, self.mode, self.type)
        #print(line)
        return line


# ---------------------------------------------------------------
class Generic():
    """
    This is the class of generics and ways to manipulate them.
    A generic consists of a name (string), a type (string),
    and a default value (string).
    """
    def __init__(self, gen_str):
        self.name = ""
        self.type = ""
        self.success = False
        self.parse_str(gen_str)

    def parse_str(self, gen_str):
        """Attempts to extract the information from a generic interface."""
        # Right now I'm going to punt.  There are so many variations
        # on these that it's difficult to write a RE for it.  Also
        # there are few ways to have to rewrite it.  We will extract
        # a name, and then a type string (which may include defaults)
        gen_pattern = r'\s?(?P<name>.*?)\s?(?::)\s?(?P<type>.*)'
        gp = re.compile(gen_pattern, re.IGNORECASE)
        s = re.search(gp, gen_str)
        if s:
            self.name = s.group('name')
            self.type = s.group('type')
            self.success = True
        else:
            print('vhdl-mode: Could not parse generic string.')
            self.success = False

    def print_as_generic(self):
        """Returns a string with the generic interface as a generic."""
        line = '{} : {}'.format(self.name, self.type)
        return line

    def print_as_genmap(self):
        """Returns a string with the generic interface as a generic map."""
        line = '{} => {}'.format(self.name, self.name)
        return line

# ---------------------------------------------------------------
class Parameter():
    """
    This is the class of subprogram parameters.  Might ultimately
    replace even Port and Generic as the pattern has improved
    since starting the package.
    """
    def __init__(self, param_str):
        self.storage = ""
        self.identifier = ""
        self.mode = ""
        self.type = ""
        self.expression = ""
        self.success = False
        self.parse_str(param_str)

    def parse_str(self, param_str):
        """Better regexp should be able to extract everything!"""
        regex = r"^\s*((?P<storage>constant|signal|variable|file)\s*)?((?P<name>.*?)\s*)(?::\s*)((?P<mode>inout\b|in\b|out\b|buffer\b)\s*)?((?P<type>.*?)\s*)((?:\:\=)\s*(?P<expression>.*?)\s*)?$"
        #print('Input: "{}"'.format(param_str))
        s = re.search(regex, param_str)
        if s:
            #print('Storage: "{}", Name: "{}", Mode: "{}", Type: "{}", Expression: "{}"'.format(s.group('storage'), s.group('name'), s.group('mode'), s.group('type'), s.group('expression')))
            if s.group('storage'):
                self.storage = s.group('storage')
            self.identifier = s.group('name')
            if s.group('mode'):
                self.mode = s.group('mode')
            self.type = s.group('type')
            if s.group('expression'):
                self.expression = s.group('expression')
            self.success = True
        else:
            print('vhdl-mode: Could not parse parameter string.')
            self.success = False

    def print_formal(self):
        """Lots of optional parameters, needs to be build up gradually."""
        string = ""
        if self.storage:
            string = string + '{} '.format(self.storage)
        string = string + '{} : '.format(self.identifier)
        if self.mode:
            string = string + '{} '.format(self.mode)
        string = string + '{}'.format(self.type)
        if self.expression:
            string = string + ' := {}'.format(self.expression)
        #print(string)
        return string

    def print_call(self):
        """Super easy transform."""
        string = '{} => {}'.format(self.identifier, self.identifier)
        return string


# ---------------------------------------------------------------
class Interface():
    """
    The Interface class contains the essential elements to a
    VHDL interface structure as defined by an entity or component
    declaration.  In addition, it comprises the methods used to
    extract the structural elements from strings passed to it
    from the Sublime Text API routines, and to produce string
    variations on these structures so that the structure can
    be transformed in various ways.
    """
    def __init__(self):
        self.name = ""
        self.type = ""
        self.if_string = ""
        self.if_ports = []
        self.if_generics = []

    def interface_start(self, line):
        """Attempts to identify the start of an interface."""
        # Checks for both entity or component starting lines
        head_pattern = r"(?P<type>entity|component)\s*(?P<name>\w*)\s*(?:is)"
        p = re.compile(head_pattern, re.IGNORECASE)
        s = re.search(p, line)
        if s:
            # Note, it's returning the horizontal position which
            # is different from the "startpoint" class variable
            # above which is the position in the file.
            self.type = s.group('type')
            self.name = s.group('name')
            return s.start()
        else:
            return None

    def interface_end(self, line):
        """Attempts to identify the end of an interface."""
        # Checks to see if the line passed contains the
        # end string matching the starting type.  The
        # type and name are optional technically.
        tail_pattern = r"(?:end)\s*(?:{})?\s*(?:{})?\s*;".format(self.type, self.name)
        p = re.compile(tail_pattern, re.IGNORECASE)
        s = re.search(p, line)
        if s:
            # The end point (from experimentation) seems to
            # be the index AFTER the final character, so
            # subtracting 1 here for the return value.
            return s.end()
        else:
            return None

    def strip_comments(self):
        """Removes comments from the interface to aid parsing."""
        # Comments will likely screw up the parsing of the
        # block and we don't need to copy them, so strip them out
        # TODO : Handle block comments someday.
        p = re.compile(r"(?:--).*?(\n|$)")
        self.if_string = re.sub(p, r"\n", self.if_string)

    def strip_whitespace(self):
        """Removes extra whitespace to aid parsing."""
        # Making sure I don't have to deal with newlines while
        # parsing.  Changing all whitespace to a single space.
        # This is required due to rules regarding port modes
        # which might conflict with type names.
        p = re.compile(r"\s+")
        self.if_string = re.sub(p, " ", self.if_string)

    def strip_head_tail(self):
        """Removes the interface lexical beginning and end to
        aid in parsing the interior."""
        # Stripping off the beginning portion of the block
        # as well as the end -- simplifies the chunk.
        head_pattern = '{} {} is'.format(self.type, self.name)
        tail_pattern = 'end\s?(?:{})?\s?(?:{})?\s?;'.format(self.type, self.name)
        hp = re.compile(head_pattern, re.IGNORECASE)
        tp = re.compile(tail_pattern, re.IGNORECASE)
        hs = re.search(hp, self.if_string)
        ts = re.search(tp, self.if_string)
        self.if_string = self.if_string[hs.end():ts.start()]

    def parse_generic_port(self):
        """Attempts to break the interface into known generic and
        port sections and then calls individual parsing routines."""
        # Initialize things.
        self.if_ports = []
        self.if_generics = []

        # Now checking for the existence of generic and port zones.
        # Split into generic string and port strings and then parse
        # each separately.  Standard demands generic first, then port.
        gen_pattern  = re.compile(r"(generic)(\s)?\(", re.IGNORECASE)
        port_pattern = re.compile(r"(port)(\s)?\(", re.IGNORECASE)
        tail_pattern = re.compile(r"\)\s?;\s*$", re.IGNORECASE)
        gen_search   = re.search(gen_pattern, self.if_string)
        port_search  = re.search(port_pattern, self.if_string)
        # Starting from the end and working back, so checking port first.
        # We don't have to search for internal parenthesis this way.
        if port_search:
            # First snip from port to the end.  Then snip the tail portion
            # (the trailing parenthesis and semicolon).  This leaves a string
            # delimited by semicolons that can be split and individually
            # parsed.
            port_str = self.if_string[port_search.end():]
            port_str = re.sub(tail_pattern, "", port_str)
            port_list = port_str.split(';')
            for port_str in port_list:
                port = Port(port_str)
                if port.success:
                    self.if_ports.append(port)
        else:
            print('vhdl-mode: No ports found')
            port_str = ""

        # Generic is actually a little tricker because if port
        # exists, the endpoint for generic is in the middle of the
        # string.  If not, it's at the end of the string.
        if gen_search:
            if port_search:
                gen_str = self.if_string[gen_search.end():port_search.start()]
            else:
                gen_str = self.if_string[gen_search.end():]
            # Snip the tail
            gen_str = re.sub(tail_pattern, "", gen_str)
            gen_list = gen_str.split(';')
            for gen_str in gen_list:
                generic = Generic(gen_str)
                if generic.success:
                    self.if_generics.append(generic)
        else:
            print('vhdl-mode: No generics found')
            gen_str = ""

    def parse_block(self):
        """Top level routine for extracting information out of a
        string block believed to contain a VHDL interface."""
        # This contains the whole parsing routine in a single method
        # because the calling command method doesn't need to know
        # about it.
        self.strip_comments()
        self.strip_whitespace()
        self.strip_head_tail()
        self.parse_generic_port()

    def signals(self):
        """
        This method returns a string that consists of the interface
        listed as signals
        """
        lines = []
        # Construct structure and insert
        if self.if_ports:
            for port in self.if_ports:
                lines.append(port.print_as_signal() + ';')
            align_block_on_re(lines, r':')
            indent_vhdl(lines, 1)
            return '\n'.join(lines)
        else:
            return None

    def instance(self, name=""):
        """This method returns a string that consists of the
        interface listed as an instantiation
        """
        # Choose a name based on a given (for testbench use) or
        # regular instantiation.
        if name:
            inst_name = name
        else:
            inst_name = self.name+'_1'
        lines = []
        lines.append("{} : entity work.{}".format(inst_name, self.name))
        if self.if_generics:
            lines.append("generic map (")
            # Put the generics in here.  Join with , and a temp
            # character then split at the temp character.  That
            # should create the lines with semicolons on all but
            # the last.
            gen_strings = []
            for generic in self.if_generics:
                gen_strings.append(generic.print_as_genmap())
            gen_strings = ',^'.join(gen_strings).split('^')
            for gen_str in gen_strings:
                lines.append(gen_str)
            lines.append(")")
        if self.if_ports:
            lines.append("port map (")
            # Put the ports in here.  Same as before.
            port_strings = []
            for port in self.if_ports:
                # Print as portmap returns a list unlike others
                for mapping in port.print_as_portmap():
                    port_strings.append(mapping)
            port_strings = ',^'.join(port_strings).split('^')
            for port_str in port_strings:
                lines.append(port_str)
            lines.append(");")

        align_block_on_re(lines, '=>')
        indent_vhdl(lines, 1)

        return '\n'.join(lines)

    def component(self):
        """
        Returns a string with a formatted component
        variation of the interface.3
        """
        # Construct structure
        lines = []
        lines.append("component {} is".format(self.name))
        if self.if_generics:
            lines.append("generic (")
            # Put the generics in here.  Join with ; and a temp
            # character then split at the temp character.  That
            # should create the lines with semicolons on all but
            # the last.
            gen_strings = []
            for generic in self.if_generics:
                gen_strings.append(generic.print_as_generic())
            gen_strings = ';^'.join(gen_strings).split('^')
            for gen_str in gen_strings:
                lines.append(gen_str)
            lines.append(");")
        if self.if_ports:
            lines.append("port (")
            # Put the ports in here.  Same as before.
            port_strings = []
            for port in self.if_ports:
                port_strings.append(port.print_as_port())
            port_strings = ';^'.join(port_strings).split('^')
            for port_str in port_strings:
                lines.append(port_str)
            lines.append(");")
        lines.append("end component {};".format(self.name))

        align_block_on_re(lines, ':')
        align_block_on_re(lines, r':\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post')
        align_block_on_re(lines, ':=')
        indent_vhdl(lines, 1)

        return '\n'.join(lines)

    def entity(self):
        """
        Returns a string with the interface written as an
        entity declaration.
        """
        # Construct structure
        lines = []
        lines.append("entity {} is".format(self.name))
        if self.if_generics:
            lines.append("generic (")
            # Put the generics in here.  Join with ; and a temp
            # character then split at the temp character.  That
            # should create the lines with semicolons on all but
            # the last.
            gen_strings = []
            for generic in self.if_generics:
                gen_strings.append(generic.print_as_generic())
            gen_strings = ';^'.join(gen_strings).split('^')
            for gen_str in gen_strings:
                lines.append(gen_str)
            lines.append(");")
        if self.if_ports:
            lines.append("port (")
            # Put the ports in here.  Same as before.
            port_strings = []
            for port in self.if_ports:
                port_strings.append(port.print_as_port())
            port_strings = ';^'.join(port_strings).split('^')
            for port_str in port_strings:
                lines.append(port_str)
            lines.append(");")
        lines.append("end entity {};".format(self.name))

        align_block_on_re(lines, ':')
        align_block_on_re(lines, r':\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post')
        align_block_on_re(lines, ':=')
        indent_vhdl(lines, 0)

        return '\n'.join(lines)


# ---------------------------------------------------------------
class Subprogram():
    """
    Class that contains information about a VHDL subprogram
    declaration and methods to enable rewriting it in some
    fashion.
    """
    def __init__(self):
        self.name = ""
        self.type = ""
        self.purity = ""
        self.if_string = ""
        self.if_params = []
        self.if_generics = []
        self.if_return = ""
        self.paren_count = [0, 0]

    def reset(self):
        """Subprograms need a reset simply because there's a lot of
        optional things that change from copy to copy.  In the
        entity/component world, it's a lot more uniform."""
        self.name = ""
        self.type = ""
        self.purity = ""
        self.if_string = ""
        self.if_params = []
        self.if_generics = []
        self.if_return = ""
        self.paren_count = [0, 0]

    def subprogram_start(self, line):
        """Attempts to identify the start of a subprogram specification."""
        # Resetting the paren count here in case we end up calling this
        # entire command multiple times.  Finding the end depends on it.
        self.paren_count = [0, 0]
        head_pattern = r"((?P<purity>impure|pure)\s+)?(?P<type>procedure|function)\s+(?P<name>\w*)"
        s = re.search(head_pattern, line, re.I)
        if s:
            if s.group('purity'):
                self.purity = s.group('purity')
            self.type = s.group('type')
            self.name = s.group('name')
            return s.start()
        else:
            return None

    def subprogram_end(self, line):
        """Attempts to identify the end of the subprogram specification.
        This is somewhat trickier than finding the end of an entity or
        component simply because there's no end clause.  A procedure
        specification block ends on a semicolon in the case of the
        prototype, and ends on 'is' in the case of a declaration.
        A function ends on return <type>; or return <type> is.  Due to
        the procedure semicolon ending (which will get also used in the
        parameters) we have to match and count parens and only validate
        a tail when all parens are balanced."""
        # Patterns to check.
        proc_tail_pattern = r";|is"
        func_tail_pattern = r"return\s+(?P<rtype>.*?)\s*(;|is)"

        # Find our parenthesis state.
        self.paren_count, open_pos, close_pos = analyze_parens(line, self.paren_count)

        # If we are unbalanced, then there's nothing to do and return.  Otherwise
        # use the last paren location to trim the line and perform the search.
        if self.paren_count[0] == self.paren_count[1]:
            if close_pos:
                new_line = line[close_pos[-1]:]
                offset = close_pos[-1]
            else:
                new_line = line
                offset = 0

            if self.type.lower() == 'function':
                s = re.search(func_tail_pattern, new_line, re.I)
                if s:
                    self.if_return = s.group('rtype')
                    return s.end() + offset
                else:
                    return None
            elif self.type.lower() == 'procedure':
                s = re.search(proc_tail_pattern, new_line, re.I)
                if s:
                    return s.end() + offset
                else:
                    return None
            else:
                return None
        else:
            return None

    def parse_block(self):
        """Chops up the string and extracts the internal declarations."""
        # Remove comments, newlines, and compress spaces.
        self.if_string = re.sub(r'--.*?(\n|$)', r'\n', self.if_string)
        self.if_string = re.sub(r'\n', r'', self.if_string)
        self.if_string = re.sub(r'\s+', r' ', self.if_string)
        # Strip return clause if a function.
        if self.type == 'function':
            func_tail_pattern = r"return\s+(?P<rtype>.*?)\s*(;|is)"
            s = re.search(func_tail_pattern, self.if_string, re.I)
            self.if_string = self.if_string[:s.start()]
        # Extract parameter block.
        start, stop = None, None
        for i in range(len(self.if_string)):
            if self.if_string[i] == '(' and not start:
                start = i+1
            if self.if_string[-i] == ')' and not stop:
                stop = -i
            if start and stop:
                break
        if start and stop:
            self.if_string = self.if_string[start:stop]
            #print(self.if_string)
            param_list = self.if_string.split(';')
            for param_str in param_list:
                param = Parameter(param_str)
                if param.success:
                    self.if_params.append(param)
                    #param.print()
        else:
            print('vhdl-mode: No subprogram parameters found.')

    def print(self):
        """For debug"""
        print('Purity: {}'.format(self.purity))
        print('SP Type: {}'.format(self.type))
        print('SP Name: {}'.format(self.name))
        print('Params: {}'.format(self.if_params))
        print('Return: {}'.format(self.if_return))

    def declaration(self):
        """Constructs a subprogram declaration from the currently
        copied subprogram.  Again there are many optional things
        so construction is piece by piece.  Going to format in
        K&R style. """
        lines = []
        if self.type == 'function':
            if self.if_params:
                if self.purity:
                    lines.append('{} {} {} ('.format(self.purity, self.type, self.name))
                else:
                    lines.append('{} {} ('.format(self.type, self.name))
                param_strings = []
                for param in self.if_params:
                    param_strings.append(param.print_formal())
                param_strings = ';^'.join(param_strings).split('^')
                for param_str in param_strings:
                    lines.append(param_str)
                lines.append(') return {};'.format(self.if_return))
            else:
                if self.purity:
                    lines.append('{} {} {} return {};'.format(self.purity, self.type, self.name, self.rtype))
                else:
                    lines.append('{} {} return {};'.format(self.type, self.name, self.if_return))
        else: # Procedure
            if self.if_params:
                lines.append('{} {} ('.format(self.type, self.name))
                param_strings = []
                for param in self.if_params:

                    param_strings.append(param.print_formal())
                param_strings = ';^'.join(param_strings).split('^')
                for param_str in param_strings:
                    lines.append(param_str)
                lines.append(');')
            else:
                lines.append('{} {};'.format(self.type, self.name))

        align_block_on_re(lines, ':')
        align_block_on_re(lines, r':\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post')
        align_block_on_re(lines, ':=')
        indent_vhdl(lines, 1)

        return '\n'.join(lines)

    def body(self):
        """Constructs a subprogram body from the currently
        copied subprogram.  Again there are many optional things
        so construction is piece by piece.  Going to format in
        K&R style. """
        lines = []
        if self.type == 'function':
            if self.if_params:
                if self.purity:
                    lines.append('{} {} {} ('.format(self.purity, self.type, self.name))
                else:
                    lines.append('{} {} ('.format(self.type, self.name))
                param_strings = []
                for param in self.if_params:
                    param_strings.append(param.print_formal())
                param_strings = ';^'.join(param_strings).split('^')
                for param_str in param_strings:
                    lines.append(param_str)
                lines.append(') return {} is'.format(self.if_return))
            else:
                if self.purity:
                    lines.append('{} {} {} return {} is'.format(self.purity, self.type, self.name, self.rtype))
                else:
                    lines.append('{} {} return {} is'.format(self.type, self.name, self.if_return))
        else: # Procedure
            if self.if_params:
                lines.append('{} {} ('.format(self.type, self.name))
                param_strings = []
                for param in self.if_params:
                    param_strings.append(param.print_formal())
                param_strings = ';^'.join(param_strings).split('^')
                for param_str in param_strings:
                    lines.append(param_str)
                lines.append(') is')
            else:
                lines.append('{} {} is'.format(self.type, self.name))
        lines.append('begin')
        lines.append(' ')
        lines.append('end {} {};'.format(self.type, self.name))

        align_block_on_re(lines, ':')
        align_block_on_re(lines, r':\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post')
        align_block_on_re(lines, ':=')
        indent_vhdl(lines, 1)

        return '\n'.join(lines)

    def call(self):
        """Constructs a subprogram call.  Much simpler than the
        declaration."""
        lines = []
        param_strings = []
        if self.if_params:
            lines.append('{} ('.format(self.name))
            for param in self.if_params:
                param_strings.append(param.print_call())
            param_strings = ',^'.join(param_strings).split('^')
            for param_str in param_strings:
                lines.append(param_str)
            lines.append(');')
        else:
            lines.append('{};'.format(self.name))

        align_block_on_re(lines, '=>')
        indent_vhdl(lines, 1)

        return '\n'.join(lines)










