setlocal EnableDelayedExpansion
"C:\Program Files\Microsoft SDKs\Windows\v7.0\Bin\SetEnv.cmd" /x64 /release
set DISTUTILS_USE_SDK=1

.\jenkins_build.bat
