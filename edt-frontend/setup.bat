@echo off
REM Setup script for Windows
REM Creates all project directories and files

echo Creating EDT Frontend project structure...
echo.

node setup-dirs.js

echo.
echo Project setup complete!
echo.
echo Next steps:
echo 1. npm install
echo 2. npm run dev
echo.
pause
