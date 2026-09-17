[app]

# Información básica
title = Bomberman Ultra Color
package.name = bombermanultracolor
package.domain = com.bombermanultracolor
source.dir = .
source.include_exts = py,png,jpg,jfif,mp3,wav,ogg
source.include_patterns = sprites/**,madara/**,pain_frames_big/**,music/**

# Dependencias
requirements = python3,kivy,pillow

# Archivos y directorios a incluir en el APK
source.include_dirs = sprites,madara,pain_frames_big,music

# Icono y splash
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png

# Orientación
orientation = landscape

# Permiso para Internet
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# Versión
version = 1.0
version.code = 1

# Configuración de Android
android.api = 33
android.minapi = 24
android.ndk = 27b
android.sdk = 33
android.accept_sdk_license = True

# Compile with ARMv7a (most common)
android.archs = arm64-v8a

# Buildozer
fullscreen = 1
fullscreen_mode = 1

#日志
log_level = 2

# Preservar datos del juego
android.presplash_color = #FF6F00

# Ejecutar en segundo plano
android.allow_backup = True

# Configuración de P4A (Python for Android)
p4a.bootstrap = sdl2
p4a.branch = develop
p4a.commit = 5865575d81d53617784428ee29f57be2716311ea
