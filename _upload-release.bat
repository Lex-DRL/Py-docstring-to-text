@echo off

call .\venv\Scripts\activate.bat

echo Where python:
echo.
where python
echo.
echo                     RELEASE?
echo.

pause

.\venv\Scripts\python.exe -m pip install -U pip
.\venv\Scripts\python.exe -m pip install -U twine

echo.
echo.
echo ============================================================
echo.
echo.

.\venv\Scripts\python.exe -m twine upload dist/*
pause
