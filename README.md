VHDL Mode
=========

Overview
--------
This package attempts to recreate the functionality found in the well-loved language mode in Emacs.  The extensibility of Sublime Text makes it an excellent platform upon which to attempt this.

This package may stand alone, however it was created to co-exist peacefully alone with the Emacs Pro Essential (formerly Sublemacs Pro) package.  In that same vein, the keyboard shortcuts were designed around the vhdl-mode shortcuts in Emacs.

Initially, the package relied upon the TextMate syntax file by Brian Padalino (after conversion to the ST3 YAML format).  However after working with this syntax definition, it became apparent that this syntax file was dated, had some issues with certain syntactical structures, and did not conform well to scope naming best practices.  An effort was undertaken to rewrite the syntax file from the language reference and incorporate meaningful and fine grained lexical scopes.  Some VHDL-2008 constructs are handled gracefully, some constructs are handled accidentally, and some are not handled at all and further work will be performed to try to get everything well defined.

Feature Set
-----------
* Port copying from entity or component declarations.
* Interface pasting as entity, component, signals, direct entity instantiation, and testbench.
* Natural language shortcuts through use of snippets including a mimicry of stutter typing for commonly used symbols and structures.
* Code beautification supporting several parenthetical code styles natively (Kernigan & Ritchie, Allman, and Lisp)
* Rewritten syntax file featuring greater granularity for lexical scope that should better support future functionality.
* Region comment/uncommenting

Known Issues and Design Commentary
----------------------------------
* This is a work in progress however I've been eating my own dog food and it works fairly satisfactorily for me currently.  I've thrown several code styles and files from other authors at it and tried to iron out the stranger bugs.  However there are a lot of coding styles and I do not promise that the beautifier will work with every one of them.  If there is an issue with a particular structure, I'm happy to get a sample and see if I can make it work.
* VHDL-2008 support is patchy currently.  All the reserved words are handled, however some lexical constructs will either beautify oddly or be scoped oddly.  Again, I'm happy to get some code samples to see it used in real life (largely not used at my place of work) and see if I can handle it.
* The TextMate VHDL syntax supported non-matching identifiers in several locations.  In order to get greater scope granularity, I had to sacrifice that feature in a few constructs because match captures do not persist through syntax scope set commands.  More work can be done in identifying illegal identifiers in various locations however.
* Designed to work with Sublime Text 3.  It is unlikely to work with Sublime Text 2 (that is to say, I would be delighted if it did, however I have never used ST2 nor tested against it so your mileage may vary.)
* Interface instantiation is still somewhat 'dumb' in that it uses a dummy label for instantiation.  Once outlining is in place, it would be nice for the label to update to an unique identfier.
* I wrote my own comment routine for the region.  This may not work the same way as ST3's own comment/uncommenter.  I tried to keep the vhdl-mode behavior where it will region indent everything at the same column.
* I have not tested this on Linux or Mac so I cannot tell how well it may work, or not, as the case may be.  I would love to find out if there are any issues and happy to attempt to resolve them.
* I did not create a snippet for everything under the sun.  In vhdl-mode, the templates were one of my least used features.  Generally I like the templates to cover large scale things that save a lot of typing.  That is to say, there's no real need in my mind for every single keyword to have its own snippet.  That being said, other packages have some of those things, and Sublime Text 3's snippet creation capability is simple, easy-to-use, and quite customizable.  If anyone creates one they believe flows naturally from regular coding I'd be happy to evaluate it and include it with attribution.
* There's no particularly graceful way to handle vhdl-mode's prompting for fields, for example, when creating an entity.  Thus, some of these behaviors were broken up into several snippets.  Typing `entity <Tab>` will form the starting and stopping entity structure, then place the cursor in the middle.  Typing `port <Tab>` at this point will start a port interface list.  In this way the flavor of the templating is retained but within a ST3 model.  If I can find a way to handle a full prompt construction, I will try to implement it, but for now it's limited to snippet support.

Future Design Goals
-------------------
* Proper project level outlining
* 'Smart' insertion of instantiation labels
* Better settings and configuration
* Subprogram smart copy and paste seems like it could be a meaningful shortcut.
* Leverage good scoping for better behaviors in all features.

Usage
-----
**Key Mappings**
As mentioned, the goal here was to be familiar with Emacs vhdl-mode users.  However I am well aware that I'm also in a Windows environment and the commonly used `C-c` prefix for code mode commands in Emacs is likely to conflict with non Sublemacs Pro users for the standard Windows copy command.  However Sublime Text 3 seems to use `M-k` as an extension keymap and this seemed a suitable replacement (in the Windows environment the `Meta` key is `Alt`).  I did a review of the default key mappings for ST3 and I don't believe I'm stepping on any toes here.

Another note, these are sequence keystrokes.  For example to copy a port interface from an entity, move the point into the structure (anywhere should be fine) and hit `Alt-k` then `p` then `w`.  These should not be chorded.

**Port Functions**
It may help to remember 'p' for port, then 'w' for write/copy, and then the first letter of the desired outcome.
* Copy Ports : `M-k p w`
* Paste as Signals : `M-k p s`
* Paste as Component: `M-k p c`
* Paste as Entity: `M-k p e`
* Paste as (Direct Entity) Instance: `M-k p i`
* Paste as Testbench: `M-k p t` -- Opens a new view and fills out boilerplate material with the interface as the unit under test.

**Commenting**
It may help to remember 'c' for code, then 'c' for comment, 'b' for beautify, etc.
* Toggle Comment Region : `M-k c c`
* Beautify Entire Buffer : `M-k c b`

**Template**
Largely templating is handled by the snippet system, however the header is a special feature as it inserts various fields automatically.  Remember 't' for template and 'h' for header.
* Insert Header : `M-k t h`

**Snippets**
Most snippets will execute from the keyword associated with them (i.e. 'entity' will fill out the beginning and ending structures and leave the cursor in the middle.)  However there are some that are created to mimic stutter typing in emacs.  This feature would let the author type one easy sequence and get replaced by a more complex typing sequence.  For example typing '..' would produce =>.  Another example, two dashes and a space '-- ' would be a normal non-stuttered comment.  However typing three dashes '---' would create a line out to the margin, and four dashes '----' would create a box.  I couldn't find a way to do this directly, however there are some close analogs in the Snippets.  Each of these snippet words require hitting Tab afterwards to execute.  This is just a list of the less obvious shortcuts.  ST3 will show snippets with completion off the Tools >> Snippets menu for further documentation.
* `spro` : Synchronous Process
* `cpro` : Combinatorial Process
* `---` : A comment line
* `--=` : A comment box (open ended on the right)
* `..` : Produces a right arrow =>
* `,,` : Produces a left arrow <=
* `;;` : Produces a colon left arrow :=
* `header` : Produces a header structure at the point (not to be confused by the insert header command which actually puts this at the top of the file.)
* `funcd` : Produces a function specification/declaration
* `funcb` : Produces a function with body.
* `procd` : Produces a procedure specification/declaration
* `procb` : Produces a procedure with body.
* `genmap` : Produces a generic map association list, differentiated from a generic interface list.
* `portmap` : Produces a port map association list, differentiated from a port interface list.
* And others... see the Snippets directory or the Tools >> Snippets menu for complete list.

**Miscellaneous Features**

* The insert header command uses a few fields from the package settings directory.  For author and company and so forth please modify this file.  The header text may be adjusted to taste.  There are comments on the fields that the command will look for.
* The on-save event is trapped and will do a scan of the file and look for `-- Last update : `.  If it finds this structure it will update the time and date on that line automatically.  This pattern is hardcoded currently and I'm trying to decide on the best way to make it user configurable.  Perhaps I can leverage settings for this.
* Most commands (save for snippets) will leave a trace in the ST3 console which may be useful for debugging.  Any package message specific to this package will start with 'vhdl-mode:'
* There is a scope 'sniffer' keybinding `M-k s`.  This is primarily for debugging the syntax file but might be useful in some fashion for other developers or for using ST3's tagging and searching functions.  It prints to the ST3 console.
* The version of the package is available with `M-k v`.
* A command-line version of the beautifier exists.  This is primarily intended for debugging, and it doesn't have access to scoping information, however it's particularly useful for debugging beautification issues since debug can be turned on in the module and the output (pretty verbose) output to a file.  Usage: `python beautifier.py input_file output_file`.
* If anyone cares, the syntax file was written with great reference and an attempt to conform to the _Designer's Guide to VHDL, 3rd Edition_ by Ashenden.  The language definition reference is in Appendix B, and library reference taken from Appendix A.  Knowing how the language is structured may help understanding the syntax file and why it's done the way it is.

Conclusion
----------
This package is offered with no warranty and no liability.  It's free to use and distribute with any code, however I would appreciate attribution for my work if forking, modifying, or incorporating.  Happy to work with other Sublime Text package authors as well.

Copyright 2017 Mark Norton

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
