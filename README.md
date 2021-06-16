# SB01 firmware
This is the software project for the Safeback SB01 controller card
 
 Author: Jan Kåre Vatne

## Development environment
For microchip's IDE and compilers go to:  
http://www.microchip.com/pagehandler/en-us/family/mplabx/

Install the following:
- MPLABX (v5.45 or later)
- XC16 Compiler (v1.61 or later)
 
### Optional linter
splint.exe (https://splint.org/download.html)
Very good for checking code reliability. The program will be run automaticaly 
at each production build (not debug build) by the prebuild.bat script

## Code syntax style
astyle.exe (https://sourceforge.net/projects/astyle/)
Automatic reformating according to style in the file "astylerc"
The style will be automaticaly enforced at each build. 

## Version tracking
The prebuild.bat file will automatically generate the file "version.h". 
This file contains the git tag using the following command:

```git describe --abbrev=8 --dirty --always --tags```

Normaly the output should be a clean tag, i.e. "v0.1.0" or similar
This means that the current git tag will be included in the hex file automatically.
Just remember to enter a tag before compiling. (git tag v0.1.0 -m "A comment")

But there is one drawback to this process: The hex file can not be included in the repo, 
and should be stored somewhere else.

## Debugging
The hex file can not be included while debugging. 
For debugging, choose the configuration "Debug" in the drop-down box in upper left corner of the screen.

For programming with the bootloader, choose the configuration "default".

