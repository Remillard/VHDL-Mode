# vhdl_code_rule.py
""" Library for VHDL keyword evaluation rules for beautification """

import re


class CodeRule():
    """
    This class contains the attributes and methods for evaluating a string
    for VHDL keywords.

    Attributes:
    - name_id: (string) Used for identifying the rule.  This is utilized by
        the ignore function as well as debug information.  Must be unique
    - start_pattern: (string) Regular expression that defines the keyword
    - current_indent: (integer) The number of indentation steps to apply to
        the current line.
    - next_indent: (integer) The number of indentation steps to apply to the
        next line.
    - indent_end: (integer) Combined former 'solo_flag' and 'close_offset'
        rules.  When non-zero, the number of indentation steps to apply
        to the closing structure when the closing structure is alone at the
        start of a line.
    - ignore_list: (list of strings) List of strings for structures that cause
        the rule to be ignored.  Will be the name field of other rule
        instantiations.

    SCRATCH PAD IDEAS:
    I need:
    * branching structures to identify different blocks, multiple ones (see
      records and functions and such)
    * Must have the branched matches be able to do things to the
      current line (see then and isclauses) along with their own rules
      * Maybe if I'm careful about the order of creating instances, the
        I can continue to create continuation instances as distinct rules?
      * Maybe I could internally have a list of pattenrs and then have a list
        of indicies of currently valid patterns...and then a way of setting and
        resetting this?  I like that idea better since it makes each structure
        monolithic, but makes the internal guts a little strange.
    * a way to define times to ignore rules -- Think my list idea is
      about as good a way as any I've thought of.

    Generically a pattern really only knows what to do with itself on its own
    line and then the next indent is always plus 1.. well except all the times
    that parentheses screw it up like port... okay so next line is NOT always
    +1, sometimes is 0.  And case uses 2 because it uses whens backwards.  So
    is there a way to encapsulate this idea into a smaller atomic structure?
    """
    def __init__(self):
        self.name_id = ""
        self.pattern = ""
        self.current_indent = 0
        self.next_indent = 0
        self.indent_end = 0
        self.ignore_list = []

    def found(self, line, closing_stack_top=""):
        """ Returns True if pattern matches and no ignore rule override. """
        if closing_stack_top is not None:
            for name in self.ignore_list:
                if name == closing_stack_top.name_id:
                    return False
        return bool(re.search(self.pattern, cl.line, re.I))



