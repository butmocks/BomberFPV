[app]

# (str) Title of your application
title = BomberFPV

# (str) Package name
package.name = bomberfpv

# (str) Package domain (needed for android/ios packaging)
package.domain = com.bomberfpv

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,json,ttf,otf,wav,ogg

# (str) Application versioning (method 1)
version = 0.1

# (list) Application requirements
requirements = python3,pygame,pyjnius,android

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

#
# Android specific
#

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (int) Target Android API, should be at least 28
android.api = 28

# (int) Minimum API your APK / AAB will support.
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) The Android logcat filters to use
android.logcat_filters = *:S python:D
