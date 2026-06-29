# YouTube Metadata to Obsidian Front Matter Pipeline

## Overview
A simple, single-purpose script that extracts metadata from YouTube URLs and generates markdown front matter for Obsidian notes.

## Pipeline Flow

```
User Input (YouTube URL)
    ↓
Extract Metadata
    ↓
Format Front Matter
    ↓
Create Markdown Note
```

## Process Steps

1. **Input**: Accept a YouTube URL
2. **Extract**: Pull metadata from the page:
   - Video title
   - Channel name
   - Description
   - Upload date
   - Duration
3. **Format**: Generate YAML front matter block
4. **Output**: Create markdown file ready for Obsidian

## Front Matter Output Format

```markdown
---
url: https://youtube.com/watch?v=...
title: Video Title
channel: Channel Name
date: YYYY-MM-DD
duration: HH:MM:SS
tags: [youtube]
---

## Description
[Video description here]

---

## Notes
[Space for transcription and additional content to be added later]
```

## Purpose
This component handles **only** the initial metadata extraction and front matter generation. It serves as the first step in a larger pipeline where transcriptions and other processed content will be appended to the note structure later.
