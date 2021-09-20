@echo off
set name=downloader
set pypath=C:\Users\jkv\Anaconda3\Scripts
set buildpath=build

if not exist %name%.py (
    echo ERROR: "%name%.py" does not exist here!
    pause
    exit /b
)

set CONDA_DLL_SEARCH_MODIFICATION_ENABLE=1
:: Activate virtual environment if it is used
:: C:\users\jkv\miniconda3\Scripts\activate <env>

:: Execute the pyinstaller and build exe file. 
:: NB: The anaconda script directory must be on the path (C:\Users\<user>\Anaconda3\Scripts)
%pypath%\pyinstaller --onefile --hidden-import pyodbc --hidden-import="pkg_resources.py2_warn" --workpath=build --distpath=. downloader.py