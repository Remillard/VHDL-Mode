# vhdl_code_rule.py
""" Library for VHDL keyword evaluation rules for beautification """

import re


class CodeRule():
    """
    This class contains the attributes and methods for evaluating a string
    for VHDL keywords.

    Attributes:
    - name: (string) Used for debug printing identifying the rule
    - start_pattern: (string) Regular expression that defines the keyword
    - current_indent: (integer) The number of indentation steps to apply to
        the current line.
    - next_indent: (integer) The number of indentation steps to apply to the
        next line.
    - indent_end: (integer) Combined former 'solo_flag' and 'close_offset'
        rules.  When non-zero, the number of indentation steps to apply
        to the closing structure when the closing structure is alone at the
        start of a line.

    SCRATCH PAD IDEAS:
    I need:
    * branching structures to identify different blocks, multiple ones (see
      records and functions and such)
    * Must have the branched matches be able to do things to the
      current line (see then and isclauses) along with their own rules
    * a way to define times to ignore rules

    Generically a pattern really only knows what to do with itself on its own
    line and then the next indent is always plus 1.. well except all the times
    that parentheses screw it up like port... okay so next line is NOT always
    +1, sometimes is 0.  And case uses 2 because it uses whens backwards.  So
    is there a way to encapsulate this idea into a smaller atomic structure?
    """
    def __init__(self):
        self.name = ""
        self.start_pattern = ""
        self.current_indent = 0
        self.next_indent = 0
        self.indent_end = 0



