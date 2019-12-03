# pylint: disable=C0103, C0111
"""
--------------------------------------------------------------------------------
 VHDL Language Module.

 Defines class structures and methods for identifying and
 manipulating text structures, and extracting and replicating
 lexical elements.
--------------------------------------------------------------------------------
"""
import re
import collections
import copy
import sublime
import ruamel.yaml

_debug = False


# ------------------------------------------------------------------------------
def debug(string):
    """
    Some of these functions ended up with a lot of debug output for analyzing
    processing.  I needed a way to turn it on and off.
    """
    if _debug:
        print(string)


# ------------------------------------------------------------------------------
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


# ------------------------------------------------------------------------------
class Parentheses():
    '''
    An object whose purpose is to keep track of parenthesis counts
    and provide helper functions while traversing a text file.

    May be initialized with a two element list indicating the starting
    counts if needed.

    open_cnt and close_cnt represent the current number of unmatched
    open and closing parentheses.

    open_pos and close_pos represent the character position of the UNMATCHED
    open and closing parentheses in the last scanned string.
    '''
    def __init__(self, counts=[0, 0]):
        self.open_cnt = counts[0]
        self.close_cnt = counts[1]
        self.open_pos = []
        self.close_pos = []

    @property
    def delta(self):
        return self.open_cnt - self.close_cnt

    @property
    def balanced(self):
        return bool(self.open_cnt == self.close_cnt)

    def reset(self):
        self.__init__()

    def scan(self, line):
        # Reset the position lists.
        self.open_pos = []
        self.close_pos = []
        for i in range(len(line)):
            if line[i] == '(':
                # If we find a ( then increment the count and append the
                # position.
                self.open_cnt += 1
                self.open_pos.append(i)
            elif line[i] == ')':
                # If we find a ) there are several options.
                # If open_pos has members, pop off the mate.  Also decrement
                # the count.
                # If open_cnt > 0 then decrement the count of the prior
                # unmatched open.
                # If open_cnt = 0 then increment the closing count and
                # append the position.
                if self.open_pos:
                    self.open_cnt -= 1
                    self.open_pos.pop()
                elif self.open_cnt > 0:
                    self.open_cnt -= 1
                else:
                    self.close_pos.append(i)
                    self.close_cnt += 1

    def stats(self):
        return '#(={}, #)={}, OPos={}, CPos={}'.format(self.open_cnt,
            self.close_cnt, self.open_pos, self.close_pos)

    def extract(self, line):
        '''Given a string, extracts the contents of the next parenthetical
        grouping (including interior parenthetical groups.)'''
        start = 0
        end = 0
        pcount = 0
        for i in range(len(line)):
            if line[i] == '(' and pcount == 0:
                pcount += 1
                start = i + 1
            elif line[i] == '(':
                pcount += 1

            if line[i] == ')' and pcount > 1:
                pcount -= 1
            elif line[i] == ')' and pcount == 1:
                end = i
                pcount -= 1
                break
        if start >= end:
            return None
        else:
            return line[start:end]

    def first_close(self, line):
        """Given a string, returns a boolean if the first character
        is a closing paren which is useful for identifying end of
        group conditions."""
        m = re.match(r'\s*\)', line)
        if m:
            return True
        return False

# ------------------------------------------------------------------------------
class CodeLine():
    """
    The CodeLine object encapsulates a number of methods used to manipulate a
    string of code.
    * Masking methods block off portions of the string in order not to trigger
      any regular expression hits in strings or comments.
    * Left Justify removes space at the beginning of the line, prelude to
      indentation efforts.
    * Padding symbols is done to ensure spaces around symbols which aids
      pattern matching.  Only done for symbols we intend to align vertically.
    * Removing extra space (except in strings and comments) is done to prep
      the line for alignment.

    WARNING: When using CodeLine masking, should always mask strings before
    comments simply because the regexp for comments gets triggerred when the
    pattern is in a string.
    """
    def __init__(self, line):
        self.line = line
        self.matches = []
        self.index = 0

    def mask_strings(self):
        matches = re.finditer(r'(\".*?\")', self.line)
        for m in matches:
            x, y = m.start(), m.end()
            pattern = '$%02d' % self.index + 'x'*(y-x-3)
            self.line = self.line.replace(m.group(0), pattern)
            self.matches.append([pattern, m.group(0)])
            self.index = self.index + 1

    def mask_comments(self):
        matches = re.finditer(r'(--.*)', self.line)
        for m in matches:
            x, y = m.start(), m.end()
            pattern = '$%02d' % self.index + 'x'*(y-x-3)
            self.line = self.line.replace(m.group(0), pattern)
            self.matches.append([pattern, m.group(0)])
            self.index = self.index + 1

    def restore(self):
        # Reversing the order of matches for the case of nested masks
        for pattern, original in reversed(self.matches):
            self.line = self.line.replace(pattern, original)
        self.matches = []
        self.index = 0

    def left_justify(self):
        self.line = re.sub(r'^\s*', '', self.line)

    def pad_vhdl_symbols(self):
        self.line = re.sub(':(?!=)', ' : ', self.line)
        self.line = re.sub(':=', ' := ', self.line)
        self.line = re.sub('<=', ' <= ', self.line)
        self.line = re.sub('=>', ' => ', self.line)
        self.line = re.sub(';', '; ', self.line)

    def remove_spaces(self):
        self.line = re.sub(r'\s+', ' ', self.line)
        self.line = re.sub(r'\t', ' ', self.line)
        self.line = re.sub(r'\s*$', '', self.line)

    @property
    def is_full_comment(self):
        return bool(re.search(r'^\s*(--.*)', self.line, re.I))

    @property
    def has_inline_comment(self):
        # Masking strings so we don't get a false positive for the pattern
        # inside a string literal.
        self.mask_strings()
        s = re.search(r'^\s*(?!--)\S+.*(--.*)', self.line, re.I)
        self.restore()
        return bool(s)


# ------------------------------------------------------------------------------
class CodeBlock():
    """
    The CodeBlock is a way of encapsulating the CodeLine functions and contains
    whole region or block manipulations for the code.  ]

    CodeBlock receives a list of lines nominally and turns them into a list of
    CodeLines. Another factory constructor permits receiving a block of text
    with embedded newlines from which it will then extract the lines and
    construct the list of CodeLines.  There is also an append method for
    incrementally generating this block.

    CodeBlock similarly provides methods for returning the CodeLines via a list
    of lines or a block of text.

    CodeBlock provides methods for manipulating the lines of code in various
    ways (justifying, aligning, indenting, etc.)
    """
    def __init__(self, lines=None):
        """ Fundamental constructor from a list of lines. """
        self.code_lines = []
        if lines is not None:
            for line in lines:
                self.code_lines.append(CodeLine(line))

    @classmethod
    def from_block(cls, block):
        """ Constructor from a block of text. """
        lines = block.split('\n')
        return cls(lines)

    def to_list(self):
        """ Returns a list of lines. """
        lines = []
        for cl in self.code_lines:
            lines.append(cl.line)
        return lines

    def to_block(self):
        """ Returns the code in a block of text. """
        lines = []
        for cl in self.code_lines:
            lines.append(cl.line)
        return '\n'.join(lines)

    def append(self, line):
        """ Adds a single line to the list of CodeLines. """
        self.code_lines.append(CodeLine(line))

    def prep(self):
        """ This method automates a lot of the initial preparatory work with
        spacing and padding. """
        for cl in self.code_lines:
            cl.mask_comments()
            cl.mask_strings()
            cl.pad_vhdl_symbols()
            cl.remove_spaces()
            cl.restore()

    def left_justify(self):
        """ This method left justifies an entire block. """
        for cl in self.code_lines:
            cl.left_justify()

    def status(self):
        for cl in self.code_lines:
            debug('{}'.format(cl.line))

    def align_symbol(self, expr, side='pre', scope_data=None, casewhen=False):
        """
        This is a in-class rework of the original align block on regular
        expression function.  The same parameters exist except it doesn't need
        to pass the entire block of lines because that's integral to the class
        members.  Additionally the method no longer takes the ignore comment
        lines parameter because there will be a specialized method for aligning
        comments later.

        Prepares each line by masking out comments and quotes first.
        Scans each line for the provided regular expression pattern that should
        align with subsequent lines.
        Once the pattern is found, pushes the location onto a stack and
        continues to the next line.
        When a line is identified that breaks the chain, go back through the
        stack and identify the rightmost position, and then pad.
        There exists a parameter to pad afterwards as there is one case where
        we want to look for port modes and pad afterwards to align the type.
        There exist some lines we don't even want to monkey with because the
        symbols tend to conflict (conditional signals in if/thens, case choice
        lines, etc.)

        Note, the casewhen option is because the reuse of the assignment
        operator means the usual pattern of aligning symbols left to right
        doesn't work very well.  So When casewhen is False, it'll ignore lines
        that we believe are case when clauses.  Then casewhen is True, it'll
        ignore everything that ISN'T a case when clause.
        """
        ignored_expr = [
            r':\s+process\b',     # don't remember why I ignore this one
            r'\bif\b',            # ignore if statement conditional symbols
            r'\bthen\b',          # ignore if statement conditional symbols
            r'\belsif\b'         # ignore if statement conditional symbols
        ]
        casewhen_expr = r'^\s*when\b(?=.*?=>)'

        # Initializing variables
        prior_scope = ""
        match_data = []

        # Iterating over lines of code now.  Using enumerate to aid detection
        # of the last item in the list.
        for idx, cl in enumerate(self.code_lines):
            # Prep work
            cl.mask_strings()
            cl.mask_comments()

            # Check for a number of items that will trigger
            # Checking for the last line in the list.
            last_line = False
            if idx == len(self.code_lines)-1:
                last_line = True

            # Checking for lines we want to ignore
            ignored = False
            casewhen_search = re.search(casewhen_expr, cl.line, re.I)
            if (casewhen_search and not casewhen) or (not casewhen_search and casewhen) :
                ignored = True
            for pattern in ignored_expr:
                ignore_search = re.search(pattern, cl.line, re.I)
                if ignore_search:
                    ignored = True

            # Checking for a change of scope on a line which will alter the
            # context of the symbol being searched for and should not be
            # aligned.  This is for a particular special case that I don't
            # recall.
            scope_switch = False
            if scope_data is not None:
                if scope_data[idx] != prior_scope:
                    scope_switch = True
                prior_scope = scope_data[idx]

            # Search for the alignment pattern and then restore the masked
            # strings.
            match = re.search(expr, cl.line, re.I)
            cl.restore()

            # If this line has a expression match and isn't an ignored line and
            # is in the same scope context, add it to the list.
            if match and not ignored and not scope_switch:
                # If we find a match, record the line and position
                if side == 'post':
                    match_data.append((cl, match.end()))
                else:
                    match_data.append((cl, match.start()))

            # Trigger the adjustment on past stored lines.
            if not match or scope_switch or last_line or ignored:
                if len(match_data) > 1:
                    # Scan for the rightmost (maximum) position value and check
                    # to see if extra space needed due to lack of preceding
                    # space.
                    maxpos = 0
                    for mcl, pos in match_data:
                        if pos > maxpos:
                            maxpos = pos
                            if mcl.line[pos-1] != ' ':
                                maxpos = maxpos + 1
                    # Adjust the spacial padding in the line.
                    for mcl, pos in match_data:
                        mcl.line = mcl.line[0:pos] + ' '*(maxpos-pos) + mcl.line[pos:]
                match_data = []

            # Case that there was a match in a new scope context must be
            # added to the list after the previous batch was processed.
            if match and scope_switch:
                if side == 'post':
                    match_data.append((cl, match.end()))
                else:
                    match_data.append((cl, match.start()))

    def indent_vhdl(self, initial=0, tab_size=4, use_spaces=False):
        """
        This method scans the list of code lines and processes them according
        to the rules laid out in the beautification rules (YAML format).
        This iteration of the method is based around being a member of the
        CodeBlock class and uses CodeBlock and CodeLine methods where
        appropriate.
        """
        # Import beautification rules from YAML file
        yaml = ruamel.yaml.YAML()
        yaml.version = (1, 2)

        rules_str = sublime.load_resource('Packages/VHDL Mode/Syntax/beautify_rules.yaml')
        rules_blob = yaml.load(rules_str)

        key_list = rules_blob['key_list']
        open_rules = rules_blob['open_rules']
        close_rules = rules_blob['close_rules']

        # Setup initial state with indentation and the running parenthesis
        # count.
        # closing_stack is using deque() and the elements are:
        # 0: The key name matched
        # 1: The current indent level.
        # Since it's used as a stack, we're always referencing element 0 (top)
        current_indent = next_indent = initial
        parens = Parentheses()
        closing_stack = collections.deque()
        unbalance_flag = False
        # Set the indent to tabs or spaces here according to parameter passed
        if use_spaces:
            indent_char = ' '*tab_size
        else:
            indent_char = '\t'

        # Scan lines
        for idx, cl in enumerate(self.code_lines):
            # Prep line for scanning and avoiding matches in comments and
            # strings.
            debug('{}: ci={} ni={} : {}'.format(idx, current_indent, next_indent, cl.line))
            cl.mask_strings()
            cl.mask_comments()

            ############################################################
            # Modification Rules
            # Priority 1: Keywords
            for key in key_list:
                skip_match = False
                rule = open_rules[key]
                key_search = re.search(rule['pattern'], cl.line, re.I)
                if key_search:
                    debug('{}: Evaluation line: {}'.format(idx, cl.line))
                    debug('{}: Evaluation pattern: {}'.format(idx, rule['pattern']))
                    debug('{}: Type: {}'.format(idx, key))
                    debug('{}: Ignore Rules: {}'.format(idx, rule['ignore_rules']))
                    if rule['ignore_rules'] is not None:
                        for ignore_rule in rule['ignore_rules']:
                            if len(closing_stack) > 0 and ignore_rule == closing_stack[0][0]:
                                skip_match = True

                    if not skip_match:
                        # If an ending type is noted, push the key onto the
                        # stack.  Save the current indent, and the current parenthetical
                        # state as well.
                        if rule['close_rule'] is not None:
                            closing_stack.appendleft([key, current_indent, copy.copy(parens)])
                        # Apply the current and next indent values to
                        # the current values.
                        current_indent += rule['indent_rule'][0]
                        next_indent += rule['indent_rule'][1]
                        break

            # Priority 2: Unbalanced Parenthesis
            # Unbalanced parenthesis rules.  The line where an unbalanced paren
            # begins is not modified, however for every line after that while
            # we are unbalanced, indent one additional level to the current
            # line (but not the next because we don't want to keep incrementing
            # outwards.)  When balance is restored, reset the flag.
            # Adding a special check if the paren is the first non-whitespace
            # character on the line.  In that case, we don't usually want to
            # preserve the indent (this is the whole reason around the 'solo
            # flag')
            parens.scan(cl.line)
            debug('{}: Parens After Scan {}'.format(idx, parens.stats()))
            if unbalance_flag:
                if not parens.first_close(cl.line):
                    debug('{}: Unbalanced parenthesis indenting.'.format(idx))
                    current_indent += 1
                else:
                    debug('{}: Solo ) Back indent.'.format(idx))
            unbalance_flag = not parens.balanced

            # Special: Closing Item Reset
            # Scan the line for ending key if one exists. If parentheses are
            # balanced and then ending key has been found then reset the
            # current and next indent level to this state.  The evaluate flag
            # is used because a branching lexical structure was discovered and
            # the line needs to be rescanned.
            if len(closing_stack):
                eval_line = True
                while eval_line:
                    debug('{}: Closing stack depth={} top={} indent={} parens={}'.format(idx, len(closing_stack), closing_stack[0][0], closing_stack[0][1], closing_stack[0][2].stats()))
                    # Assume that we will traverse only once, and set the flag
                    # to false.  If we need to rescan, the flag will be set
                    # true.
                    eval_line = False

                    # Since the closing rule pattern could be multiple patterns,
                    # we have to scan through that item, referencing into the
                    # close_rules dictionary for the pattern.  Assigning the
                    # rule list to another name to stop the madness of
                    # indirection.
                    stack_key, stack_indent, stack_parens = closing_stack[0]
                    rules = open_rules[stack_key]['close_rule']

                    # Step through and search for the end pattern.
                    for close_key, result in rules:
                        debug('{}: Evaluation line: {}'.format(idx, cl.line))
                        debug('{}: Evaluation pattern: {}'.format(idx, close_rules[close_key]))
                        close_search = re.search(close_rules[close_key], cl.line, re.I)
                        if close_search and parens.delta == stack_parens.delta:
                            # We've found a match and are in a balanced state.
                            debug('{}: Found closing match to {}'.format(idx, stack_key))
                            if result is not None:
                                # We have found a continuation of the structure.
                                # Pop off the top of the stack, then append the new
                                # key to the top of the stack and re-evaluate.
                                debug('{}: Continuation found.  Re-evaluating for {}'.format(idx, result))
                                closing_stack.popleft()
                                closing_stack.appendleft([result, stack_indent, stack_parens])
                                # Need to do a solo line check, mainly for those is clauses.
                                if open_rules[result]['solo_flag']:
                                    solo_search = re.search(r'^\)?\s?'+close_rules[close_key], cl.line, re.I)
                                    if solo_search:
                                        # Unindent this line most likely
                                        debug('{}: Solo intermediate found.'.format(idx))
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
                                    debug('{}: Using solo line rule.'.format(idx))
                                    solo_search = re.search(r'^\)?\s?'+close_rules[close_key], cl.line, re.I)
                                    if solo_search:
                                        # Revert on this line
                                        debug('{}: Solo closing found here.'.format(idx))
                                        current_indent = stack_indent + open_rules[stack_key]['close_offset']
                                        next_indent = stack_indent
                                    else:
                                        debug('{}: Close is not alone on this line.'.format(idx))
                                        # Revert on the next line
                                        next_indent = stack_indent
                                else:
                                    debug('{}: Regular ending rule.'.format(idx))
                                    # No special rule handling.  Revert on this line.
                                    current_indent = next_indent = stack_indent
                                # Pop the top of the stack and we're done with evaluating
                                # closing strings.
                                closing_stack.popleft()

            # Modify the line here.
            cl.line = indent_char*current_indent + cl.line
            cl.line = re.sub(r'\s*$', '', cl.line)
            cl.restore()
            debug('{}: ci={} ni={} : {} \n'.format(idx, current_indent, next_indent, cl.line))
            # Set current for next line.
            current_indent = next_indent

    def align_comments(self, tab_size=4, use_spaces=False):
        """
        Comments are a little different from normal alignment and
        identation.

        1. Full comment lines should be aligned, however they should be
           indented to the level of the next code line, not the previous
           which is what happens with the indent_vhdl routine.  This is most
           notable with case/when code regions where a comment preceding a
           'when' will be indented at the level of the previous when block.
           Thus full comment lines should be aligned after regular indentation
           is complete.  The method assumes that the calling code has already
           completed indent_vhdl.

           The indentation will be accomplished by copying the text between the
           aligning line back into the comment lines, so space/tab alignment
           is preserved.  Also this way I don't need to know what the indent
           level actually is, just using what's there already.

        2. Inline comment lines cannot be aligned with symbol alignment because
           I mask off comments.  So in addition to aligning these, we'd like
           continuation comment lines (which might be full comment lines) to
           maintain the same position as the previous until non full comment
           line occurs.

           The indentation will be accomplished with spaces.  There's no way to
           do this otherwise.  However for the inline comments, I attempt to
           take tabs into account for spacing.

        To accomplish both of these, instituting a couple of properties on the
        CodeLine class that determine if a line is a full comment line or if
        a line has an inline comment.  Between these, we should be able to
        scan a CodeBlock and adjust the indentation of comment lines.
        """
        # Pass one, full line comments
        match_data = []
        for idx, cl in enumerate(self.code_lines):
            if cl.is_full_comment:
                match_data.append(cl)
            else:
                # Look for the first non blank line to align comments with.
                bls = re.search(r'^\s*$', cl.line, re.I)
                nbls = re.search(r'^(\s*)\S', cl.line, re.I)
                if bls:
                    # Do nothing and keep text at current indent level.
                    match_data = []
                elif nbls:
                    # If we've got a set of lines to align, process the match.
                    if match_data:
                        for mcl in match_data:
                            mcl.left_justify()
                            mcl.line = nbls.group(1) + mcl.line
                        match_data = []

        # Pass two, inline comments.  This is actually closer to the original
        # alignment method since I record position as well.
        match_data = []
        for idx, cl in enumerate(self.code_lines):
            if cl.has_inline_comment or cl.is_full_comment:
                s = re.search(r'^.*?(--.*)', cl.line, re.I)
                if match_data:
                    match_data.append((cl, s.start(1)))
                elif cl.has_inline_comment:
                    match_data.append((cl, s.start(1)))
            else:
                # Process matches if there's more than one.
                if len(match_data) > 1:
                    maxpos = 0
                    for mcl, pos in match_data:
                        tab_count = mcl.line.count('\t')
                        adj_pos = pos + tab_count*(tab_size-1)
                        if adj_pos > maxpos:
                            maxpos = adj_pos
                            if mcl.line[pos-1] != ' ':
                                maxpos = maxpos + 1
                    for mcl, pos in match_data:
                        tab_count = mcl.line.count('\t')
                        adj_pos = pos + tab_count*(tab_size-1)
                        mcl.line = mcl.line[0:pos] + ' '*(maxpos-adj_pos) + mcl.line[pos:]
                match_data = []


# ------------------------------------------------------------------------------
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
            # Sometimes the type has a trailing space.  Eliminating it.
            self.type = re.sub(r'\s*$', '', s.group('type'))
            self.success = True
        else:
            print('vhdl-mode: Could not parse port string.')
            self.success = False

    def print_as_signal(self):
        """Returns a string with the port formatted for a signal."""
        # Trailing semicolon provided by calling routine.
        line = 'signal {} : {}'.format(self.name, self.type)
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
        return line


# ------------------------------------------------------------------------------
class Generic():
    """
    This is the class of generics and ways to manipulate them.
    A generic consists of a name (string), a type (string),
    and a default value (string).
    """
    def __init__(self, gen_str):
        self.gentype = False
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
        #
        # VHDL 2008 defines the capability to declare a generic type.  To
        # support this, I created the gentype attribute.  I'll use the name
        # attribute to carry the type's name, however since this isn't a
        # declaration WITH a type, that attribute will not be used.
        gentype_pattern = r'\s*type\s+(?P<name>\w+)'
        gps = re.search(gentype_pattern, gen_str, re.I)
        if gps:
            self.gentype = True
            self.name = gps.group('name')
            self.success = True
            return True

        constant_pattern = r'\s?(?P<name>.*?)\s?(?::)\s?(?P<type>.*)'
        s = re.search(constant_pattern, gen_str, re.I)
        if s:
            self.name = s.group('name')
            # Sometimes the type has a trailing space.  Eliminating it.
            self.type = re.sub(r'\s*$', '', s.group('type'))
            self.success = True
            return True
        else:
            print('vhdl-mode: Could not parse generic string.')
            self.success = False
            return False

    def print_as_generic(self):
        """Returns a string with the generic interface as a generic."""
        if self.gentype:
            line = 'type {}'.format(self.name)
        else:
            line = '{} : {}'.format(self.name, self.type)
        return line

    def print_as_genmap(self):
        """Returns a string with the generic interface as a generic map."""
        line = '{} => {}'.format(self.name, self.name)
        return line

    def print_as_constant(self):
        '''Returns a string with the generic interface as a constant.'''
        # So... generic doesn't necessarily have to have a default value
        # even though it should.  So this requires a little detective work
        # to know whether to include the whole line or add in the necessary
        # constant definition.
        #
        # Technically using VHDL-2008 generic type isn't a constant, but for
        # the moment, I'm going to include it here and just adjust the
        # testbench template.
        if self.gentype:
            line = 'type {}'.format(self.name)
        else:
            s = re.search(r':=', self.type, re.I)
            if s:
                line = 'constant {} : {}'.format(self.name, self.type)
            else:
                line = 'constant {} : {} := <value>'.format(self.name, self.type)
        return line


# ------------------------------------------------------------------------------
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
        s = re.search(regex, param_str)
        if s:
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
        return string

    def print_call(self):
        """Super easy transform."""
        string = '{} => {}'.format(self.identifier, self.identifier)
        return string


# ------------------------------------------------------------------------------
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

    def parse_generic_port(self):
        """Attempts to break the interface into known generic and
        port sections and then calls individual parsing routines."""
        # Initialize things.
        self.if_ports = []
        self.if_generics = []

        # Now checking for the existence of generic and port zones.
        # Split into generic string and port strings and then parse
        # each separately.  Standard demands generic first, then port.
        gen_pattern  = re.compile(r'generic\s*\(', re.I)
        port_pattern = re.compile(r'port\s*\(', re.I)
        gen_search   = re.search(gen_pattern, self.if_string)
        port_search  = re.search(port_pattern, self.if_string)

        # The potential for a passive block in an entity means the previous
        # method of extracting the port string will no longer work and the
        # more tedious (though foolproof) method of searching forward from
        # the port starting point is necessary.
        if port_search:
            port_str = Parentheses().extract(self.if_string[port_search.start():])
            if port_str is not None:
                port_list = port_str.split(';')
                for item in port_list:
                    port = Port(item)
                    if port.success:
                        self.if_ports.append(port)
            else:
                print('vhdl-mode: No ports found.')
                port_str = ""
        else:
            print('vhdl-mode: No ports found.')
            port_str = ""

        if gen_search:
            gen_str = Parentheses().extract(self.if_string[gen_search.start():])
            if gen_str is not None:
                gen_list = gen_str.split(';')
                for item in gen_list:
                    generic = Generic(item)
                    if generic.success:
                        self.if_generics.append(generic)
            else:
                print('vhdl-mode: No generics found.')
                gen_str = ""
        else:
            print('vhdl-mode: No generics found.')
            gen_str = ""

    def parse_block(self):
        """Top level routine for extracting information out of a
        string block believed to contain a VHDL interface."""
        # This contains the whole parsing routine in a single method
        # because the calling command method doesn't need to know
        # about it.
        self.strip_comments()
        self.strip_whitespace()
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
            cb = CodeBlock(lines)
            cb.align_symbol(r':(?!=)', 'pre', None)
            cb.align_symbol(r'<|:(?==)', 'pre', None)
            cb.indent_vhdl(1)
            return cb.to_block()
        else:
            return None

    def constants(self):
        '''
        This method returns the generic portion of the interface
        listed as constants.
        '''
        lines = []
        if self.if_generics:
            for generic in self.if_generics:
                lines.append(generic.print_as_constant() + ';')
            cb = CodeBlock(lines)
            cb.align_symbol(r':', 'pre', None)
            cb.align_symbol(r':=', 'pre', None)
            cb.indent_vhdl(1)
            return cb.to_block()
        else:
            return None

    def instance(self, instances={}, name=""):
        """This method returns a string that consists of the
        interface listed as an instantiation
        """
        # Choose a name based on a given (for testbench use) or
        # regular instantiation.
        if name:
            inst_name = name
        elif self.name in instances:
            instance_count = len(instances[self.name])
            inst_name = self.name+'_{}'.format(instance_count+1)
            # Check for duplicate name and just increment index until clear.
            while inst_name in instances[self.name]:
                instance_count += 1
                inst_name = self.name+'_{}'.format(instance_count+1)
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

        cb = CodeBlock(lines)
        cb.align_symbol(r'\=\>', 'pre', None)
        cb.indent_vhdl(1)
        return cb.to_block()

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

        cb = CodeBlock(lines)
        cb.align_symbol(r':(?!=)', 'pre', None)
        cb.align_symbol(r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post', None)
        cb.align_symbol(r'<|:(?==)', 'pre', None)
        cb.indent_vhdl(1)
        return cb.to_block()

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

        cb = CodeBlock(lines)
        cb.align_symbol(r':(?!=)', 'pre', None)
        cb.align_symbol(r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post', None)
        cb.align_symbol(r'<|:(?==)', 'pre', None)
        cb.indent_vhdl(0)
        return cb.to_block()

    def flatten(self):
        '''
        Iterates over the generics and ports and if there
        is a line with multiple token names on the same line, will
        make copies of that port with the individual token names.
        '''
        if self.if_generics:
            new_generics = []
            for generic in self.if_generics:
                if ',' in generic.name:
                    name_list = re.sub(r'\s*,\s*', ',', generic.name).split(',')
                    for name in name_list:
                        new_generic = copy.copy(generic)
                        new_generic.name = name
                        new_generics.append(new_generic)
                else:
                    new_generics.append(generic)
            self.if_generics = new_generics
        if self.if_ports:
            new_ports = []
            for port in self.if_ports:
                if ',' in port.name:
                    name_list = re.sub(r'\s*,\s*', ',', port.name).split(',')
                    for name in name_list:
                        new_port = copy.copy(port)
                        new_port.name = name
                        new_ports.append(new_port)
                else:
                    new_ports.append(port)
            self.if_ports = new_ports

    def reverse(self):
        '''
        Iterates over the ports and flips the direction/mode.
        in becomes out
        out and buffer become in
        inout is unchanged.
        '''
        if self.if_ports:
            for port in self.if_ports:
                if port.mode.lower() == 'in':
                    port.mode = 'out'
                elif port.mode.lower() == 'out' or port.mode.lower() == 'buffer':
                    port.mode = 'in'


# ------------------------------------------------------------------------------
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
        self.parens = Parentheses()

    def subprogram_start(self, line):
        """Attempts to identify the start of a subprogram specification."""
        # Resetting the paren count here in case we end up calling this
        # entire command multiple times.  Finding the end depends on it.
        head_pattern = r"((?P<purity>impure|pure)\s+)?(?P<type>procedure|function)\s+(?P<name>\w*)"
        s = re.search(head_pattern, line, re.I)
        if s:
            if s.group('purity'):
                self.purity = s.group('purity')
            self.type = s.group('type')
            self.name = s.group('name')
            self.parens.reset()
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
        self.parens.scan(line)

        # If we are unbalanced, then there's nothing to do and return.  Otherwise
        # use the last paren location to trim the line and perform the search.
        if self.parens.balanced:
            if self.parens.close_pos:
                new_line = line[self.parens.close_pos[-1]:]
                offset = self.parens.close_pos[-1]
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
            param_list = self.if_string.split(';')
            for param_str in param_list:
                param = Parameter(param_str)
                if param.success:
                    self.if_params.append(param)
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

        cb = CodeBlock(lines)
        cb.align_symbol(r':(?!=)', 'pre', None)
        cb.align_symbol(r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post', None)
        cb.align_symbol(r'<|:(?==)', 'pre', None)
        cb.indent_vhdl(1)
        return cb.to_block()

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

        cb = CodeBlock(lines)
        cb.align_symbol(r':(?!=)', 'pre', None)
        cb.align_symbol(r':(?!=)\s?(?:in\b|out\b|inout\b|buffer\b)?\s*', 'post', None)
        cb.align_symbol(r'<|:(?==)', 'pre', None)
        cb.indent_vhdl(1)
        return cb.to_block()

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

        cb = CodeBlock(lines)
        cb.align_symbol(r'\=\>', 'pre', None)
        cb.indent_vhdl(1)
        return cb.to_block()

    def flatten(self):
        new_params = []
        if self.if_params:
            for param in self.if_params:
                if ',' in param.identifier:
                    name_list = re.sub(r'\s*,\s*', ',', param.identifier).split(',')
                    for name in name_list:
                        new_param = copy.copy(param)
                        new_param.identifier = name
                        new_params.append(new_param)

                else:
                    new_params.append(param)
            self.if_params = new_params

