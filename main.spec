# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('viewer.ui', '.'),                      # 메인 UI
        ('ROI/roi.ui', 'ROI'),                   # ROI 설정 UI
        ('yolov8n.pt', '.'),                     # YOLO 모델 파일
    ],
    hiddenimports=[
        'PyQt5.sip'                              # PyQt5의 내부 모듈 (필수)
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False    # 콘솔창 없이 GUI 앱으로 빌드
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main'
)
