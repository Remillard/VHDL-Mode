# VHDL Mode

## Overview

This package attempts to recreate the functionality found in the well-loved language mode in Emacs.  The extensibility of Sublime Text makes it an excellent platform upon which to attempt this.

This package may stand alone, however it was created to co-exist peacefully alone with the Emacs Pro Essential package.  In that same vein, the keyboard shortcuts were designed around the vhdl-mode shortcuts in Emacs.

Initially, the package relied upon the TextMate syntax file by Brian Padalino (after conversion to the ST3 YAML format).  However after working with this syntax definition, it became apparent that this syntax file was dated, had some issues with certain syntactical structures, and did not conform well to scope naming best practices.  An effort was undertaken to rewrite the syntax file from the language reference and incorporate meaningful and fine grained lexical scopes.  VHDL-2008 should be handled well.

Issues are tracked [here](https://github.com/Remillard/VHDL-Mode/issues "VHDL Mode Issue Tracker") on the project in GitHub.  I will state up front that I cannot duplicate Emacs vhdl-mode completely (e.g. see the discussion on stutter typing) however if there is a particular omission or a feature that is desireable, please feel free to open an issue.  I'm happy to talk about it.  If that isn't possible, the plugin announcement on the Sublime Text forum is located [here](https://forum.sublimetext.com/t/vhdl-mode-for-sublime-text-3/29782 "VHDL Mode Announcement") and I can glean issues there as well and add them.

## Feature Set

* Port copying from entity or component declarations.
* Interface pasting as entity, component, signals, direct entity instantiation, and testbench.
* Proper stutter typing shortcuts for the assignment operators and commenting structures.
* Natural language shortcuts through use of snippets for commonly used structures.
* Code beautification supporting several parenthetical code styles natively (Kernigan & Ritchie, Allman, and Lisp)
* Rewritten syntax file featuring greater granularity for lexical scope that should better support future functionality.
* Region comment/uncommenting

## Future Design Goals

* Proper project level outlining
* 'Smart' insertion of instantiation labels
* Subprogram smart copy and paste seems like it could be a meaningful shortcut.
* Leverage good scoping for better behaviors in all features.

## Configuration

The VHDL Mode `sublime-settings` file contains fields that are used to fill in certain fields in the header template upon insertion.  A base override may be created by selecting `Preferences` >> `Package Settings` >> `VHDL Mode` >> `Settings`.  This will bring up the default settings file and a User variation on the settings.  To customize the fields, simply copy and paste the defaults over to the User override file, and edit to taste.

These fields can also be set in the `sublime-project` file under `"settings"` for project specific behavior.  To facilitate this, a project helper snippet was created to inject these settings when editing the project file.  Simply select `Project` >> `Edit Project` from the menu, move the cursor past the `"folders"` line and type `project`.  The project snippet also creates a couple of sample build methods that can be used for the project.

One particular setting meshes with both the header template and the on-save time field.  The `vhdl-modified-time-string` setting is the string that the code looks for when catching the on-save event, and updating that field.  This should only be altered if the header snippet has been modified.  When the event triggers, the code searches for that string, and replaces that line with the string, plus the time information.

Code beautification should pay attention to the `tab_size` and `translate_tabs_to_spaces` settings that are part of the standard Sublime Text preferences.  Please let me know if this causes any issues.

* `vhdl-user` : Fills in the username portion of the header template.
* `vhdl-company` : Fills in the company name portion of the header template.
* `vhdl-project-name` : Fills in the project name portion of the header template.  This field would very commonly be customized in the `sublime-project` file.
* `vhdl-platform` : Fills in the platform or part number portion of the header template.
* `vhdl-standard` : Fills in the coding standard portion of the header template.
* `vhdl-modified-time-string` : Represents the string that will be searched for when the file is saved.  If this is found, that line is replaced with a string comprising of this pattern, plus the current time.

# Usage

## Key Mappings

As mentioned, the goal here was to be familiar with Emacs vhdl-mode users.  However I am well aware that I'm also in a Windows environment, and the commonly used `C-c` prefix for code mode commands in Emacs will conflict with the standard Windows copy command.  Sublime Text 3 seems to use `M-k` as an extension keymap and this seemed a suitable replacement (in the Windows environment the `Meta` key is `Alt`).  I did a review of the default key mappings for ST3 and I don't believe I'm stepping on any toes here.

Another note, these are sequence keystrokes.  For example to copy a port interface from an entity, move the point into the structure (anywhere should be fine) and hit `Alt-k` then `p` then `w`.  These should not be chorded.

**Port Functions**

It may help to remember `p` for port, then `w` for write (to copy).  The other mnemonics are fairly straightforward.

* Copy Ports : `M-k p w`
* Paste as Signals : `M-k p s`
* Paste as Component: `M-k p c`
* Paste as Entity: `M-k p e`
* Paste as (Direct Entity) Instance: `M-k p i`
* Paste as Testbench: `M-k p t` -- Opens a new view and fills out boilerplate material with the interface as the unit under test.

The following animated GIF demonstrates a portion of the port copying feature.

![Port Copying Demonstration](./images/demo.gif)

**Commenting**

It may help to remember 'c' for code, then 'c' for comment, 'b' for beautify, etc.

* Toggle Comment Region : `M-k c c`
* Beautify Entire Buffer : `M-k c b`

**Template**

Largely templating is handled by the snippet system, however the header is a special feature as it inserts various fields automatically.  Remember 't' for template and 'h' for header.

* Insert Header : `M-k t h`

**Miscellaneous**

* Package Version : `M-k v`
* Scope at Point : `M-k s`

## Stutter Typing

I cannot duplicate the entire Emacs vhdl-mode stutter typing repetoire.  I do not have access to the keystream directly, so what I have been able to do is use keybindings and in one case a keybinding and macro to replicate the behavior.  I'll list the implemented replacements and then a note on the ones I cannot and why I cannot replicate these.

* `;;` : Produces ` : `
* `;;;` : Produces ` := ` (See notes below)
* `..` : Produces ` => `
* `,,` : Produces ` <= `
* `---` : Produces a comment line extending to column 80 starting where the cursor is, and accounting for tabs.  This one pays attention to the `tab_size` Preference if you use tabs.
* `--=` : Produces a three-sided comment box extending to column 80 starting whree the cursor is, and accounting for tabs.  (See notes.)

The following are the stutter typing replacements I cannot do.

* `[`, `[[`, `]`, `]]`, `''` : These cannot be duplicated properly.  The problem is that the Sublime API does not have direct access to the keystream.  The only way to replicate this (as I was able to with `;;;`) is to create a keybind that checks the preceding text and if it is the replaced text, execute a macro that deletes and replaces the text with the new text.  However if I replaced `[` with `(` and then looked for a preceding paren for `[[` then one would never be able to properly type nested parenthesis.
* `;;;` : I'd like to give fair warning that this is not implemented exactly like Emacs does it.  How this works is that `;;` creates ` : `.  I have also keybound `;` to check for the preceding text and if it is ` : ` then it will execute a macro that deletes and replaces with ` := `.  The side effect of this is that if the cursor is placed at a point in the text where ` : ` is just behind the point, this macro will ALSO execute then.  I think this is likely a fairly rare event and I have no other way to create this behavior, so I opted for this workaround.
* `----` : Again I cannot duplicate this by checking the prior text because that would create weird issues if someone was just trying to make a custom length comment dash line.  I created the `--=` as a replacement for the comment box.
* `==` : Honestly I could create this one however it's kind of pointless.  The `==` is not a VHDL operator and I'm not honestly certain why it's in Emacs vhdl-mode.

## Snippets

Most snippets will execute from the keyword associated with them (i.e. 'entity' will fill out the beginning and ending structures and leave the cursor in the middle.)  Each of these snippet words require hitting Tab afterwards to execute.  This is just a list of the less obvious shortcuts.  ST3 will show snippets with completion off the Tools >> Snippets menu for further documentation.

* `spro` : Synchronous Process
* `cpro` : Combinatorial Process
* `header` : Produces a header structure at the point (not to be confused by the insert header command which actually puts this at the top of the file.)
* `funcd` : Produces a function specification/declaration
* `funcb` : Produces a function with body.
* `procd` : Produces a procedure specification/declaration
* `procb` : Produces a procedure with body.
* `genmap` : Produces a generic map association list, differentiated from a generic interface list.
* `portmap` : Produces a port map association list, differentiated from a port interface list.
* `project` : Active while editing a Sublime Text project file.  Fills in local copies of the setting keys and instantiates a couple of example build systems.
* And others... see the Snippets directory or the Tools >> Snippets menu for complete list.

## Miscellaneous Features

* The insert header command uses a few fields from the package settings directory.  For author and company and so forth please modify this file.  The header text may be adjusted to taste.  There are comments on the fields that the command will look for.
* The on-save event is trapped and will do a scan of the file and by default look for `-- Last update : ` in a VHDL file.  If it finds this structure it will update the time and date on that line automatically.  This pattern is configured through settings.
* Most commands (save for snippets) will leave a trace in the ST3 console which may be useful for debugging.  Any package message specific to this package will start with 'vhdl-mode:'

## Known Issues and Design Commentary

* This is a work in progress however I've been eating my own dog food and it works fairly satisfactorily for me currently.  I've thrown several code styles and files from other authors at it and tried to iron out the stranger bugs.  However there are a lot of coding styles and I do not promise that the beautifier will work with every one of them.  If there is an issue with a particular structure, I'm happy to get a sample and see if I can make it work.
* VHDL-2008 support is patchy currently.  All the reserved words are handled, however some lexical constructs will either beautify oddly or be scoped oddly.  Again, I'm happy to get some code samples to see it used in real life (largely not used at my place of work) and see if I can handle it.
* The TextMate VHDL syntax supported non-matching identifiers in several locations.  In order to get greater scope granularity, I had to sacrifice that feature in a few constructs because match captures do not persist through syntax scope set commands.  More work can be done in identifying illegal identifiers in various locations however.
* The syntax file was written with great reference and an attempt to conform to the _Designer's Guide to VHDL, 3rd Edition_ by Peter Ashenden.  The language definition reference is in Appendix B, and library reference taken from Appendix A.  Knowing how the language is structured may help understanding the syntax file and why it's done the way it is.
* Designed to work with Sublime Text 3.  It is unlikely to work with Sublime Text 2 (that is to say, I would be delighted if it did, however I have never used ST2 nor tested against it so your mileage may vary.)
* Interface instantiation is still somewhat 'dumb' in that it uses a dummy label for instantiation.  Once outlining is in place, it would be nice for the label to update to an unique identfier.
* I wrote my own comment routine for the region.  This may not work the same way as ST3's own comment/uncommenter.  I tried to keep the vhdl-mode behavior where it will region indent everything at the same column.
* I have not tested this on Linux or Mac so I cannot tell how well it may work, or not, as the case may be.  I would love to find out if there are any issues and happy to attempt to resolve them.
* I did not create a snippet for everything under the sun.  In vhdl-mode, the templates were one of my least used features.  Generally I like the templates to cover large scale things that save a lot of typing.  That is to say, there's no real need in my mind for every single keyword to have its own snippet.  That being said, other packages have some of those things, and Sublime Text 3's snippet creation capability is simple, easy-to-use, and quite customizable.  If anyone creates one they believe flows naturally from regular coding I'd be happy to evaluate it and include it with attribution.
* There's no particularly graceful way to handle vhdl-mode's prompting for fields, for example, when creating an entity.  Thus, some of these behaviors were broken up into several snippets.  Typing `entity <Tab>` will form the starting and stopping entity structure, then place the cursor in the middle.  Typing `port <Tab>` at this point will start a port interface list.  In this way the flavor of the templating is retained but within a ST3 model.  If I can find a way to handle a full prompt construction, I will try to implement it, but for now it's limited to snippet support.

# Conclusion

This package is offered with no warranty and no liability.  It's free to use and distribute with any code, however I would appreciate attribution for my work if forking, modifying, or incorporating.  Happy to work with other Sublime Text package authors as well.

MIT License

Copyright (c) 2017 Mark Norton

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
