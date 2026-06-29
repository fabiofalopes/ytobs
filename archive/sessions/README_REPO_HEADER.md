# YouTube to Obsidian

Transform YouTube videos into AI-enhanced Obsidian notes with one command.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## Features

- 🎯 **One Command** - Extract metadata, transcript, and AI analysis
- 🤖 **Smart AI Analysis** - Automatic pattern selection based on content
- ⚡ **Three Speed Modes** - Quick (25s), Auto (50s), Deep (70s)
- 📝 **Obsidian Ready** - YAML frontmatter, tags, and backlinks
- 🔧 **Highly Configurable** - Persistent preferences via config file

---

## Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd yt-dlp-tests

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set Obsidian vault location
export OBSVAULT="/path/to/your/obsidian/vault"

# Make executable
chmod +x yt

# Test it works
./yt --help
```

---

