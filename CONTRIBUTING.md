# Contributing to YouTube to Obsidian

Thanks for your interest in contributing!

## Development Setup

```bash
# Clone the repo
git clone <repo-url>
cd yt-dlp-tests

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variable
export OBSVAULT="/path/to/your/obsidian/vault"

# Test it works
./yt --help
```

## Project Structure

- `yt` - Main CLI entry point
- `lib/` - Core Python modules
- `docs/` - Architecture and design docs
- `config.yaml` - Default configuration

## Making Changes

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Test thoroughly: `./yt --quick <test-url>`
4. Commit with clear messages
5. Push and create a pull request

## Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and small

## Testing

Currently manual testing. Run with various video types:
- Short videos (<5 min)
- Long videos (>1 hour)
- Different content types (education, music, etc.)

## Areas for Contribution

- [ ] Unit tests
- [ ] Better error messages
- [ ] Performance improvements
- [ ] Additional Fabric patterns
- [ ] Documentation improvements
- [ ] Bug fixes

## Questions?

Check `CONTEXT.md` for project decisions and state.
