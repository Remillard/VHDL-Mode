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
