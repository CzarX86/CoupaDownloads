# Release Strategy for CoupaDownloads

## Distribution Options

### 1. Self-Contained Portable (Recommended)

- **Description**: Complete package with Python runtime and all dependencies
- **Size**: ~50-100MB (includes Python, Selenium, EdgeDriver)
- **Installation**: Unzip and run - no installation required
- **Target**: End users who want simplicity

### 2. Framework-Dependent (Lightweight)

- **Description**: Requires Python 3.8+ to be installed separately
- **Size**: ~10-20MB (just the application code)
- **Installation**: Requires Python environment setup
- **Target**: Developers and power users

### 3. User-Installable (Windows)

- **Description**: Windows installer with optional admin rights
- **Size**: ~30-50MB
- **Installation**: Standard Windows installer
- **Target**: Enterprise environments

## Update Notification System

### Implementation Strategy

1. **Version Check**: Check GitHub releases API for latest version
2. **Local Version**: Store current version in config file
3. **Notification**: Show update prompt when newer version available
4. **Auto-Download**: Optional automatic download of new version

### Update Flow

```
App Startup → Check Version → Compare with Latest → Show Notification → Download & Install
```

## Release Process

### 1. Version Management

- Use semantic versioning (MAJOR.MINOR.PATCH)
- Store version in `src/core/config.py`
- Update `pyproject.toml` version

### 2. Build Process

- Create portable distribution with PyInstaller
- Package EdgeDriver binaries
- Create Windows installer with NSIS
- Generate checksums for security

### 3. Release Automation

- GitHub Actions for automated builds
- Release notes generation
- Asset upload to GitHub releases

## File Structure for Releases

```
CoupaDownloads-v1.0.0/
├── CoupaDownloads.exe (portable)
├── drivers/
│   ├── msedgedriver.exe
│   └── msedgedriver
├── config/
│   └── settings.json
├── README.md
└── LICENSE
```

## Implementation Plan

### Phase 1: Portable Distribution

- [ ] Set up PyInstaller configuration
- [ ] Create build script
- [ ] Package with EdgeDriver
- [ ] Test portable distribution

### Phase 2: Update System

- [ ] Implement version checking
- [ ] Add update notification UI
- [ ] Create update downloader
- [ ] Add auto-update functionality

### Phase 3: Release Automation

- [ ] GitHub Actions workflow
- [ ] Automated version bumping
- [ ] Release notes generation
- [ ] Multi-platform builds

## Benefits of This Approach

1. **User-Friendly**: No complex installation required
2. **Enterprise-Ready**: Supports admin and non-admin installations
3. **Self-Updating**: Keeps users on latest version
4. **Cross-Platform**: Works on Windows, macOS, Linux
5. **Offline-Capable**: Can work without internet after initial download
