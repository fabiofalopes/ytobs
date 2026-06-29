
<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>
# make a comparison for this 3: youtube api vs yt-dlp vs yt-dlp + api

The three approaches serve different purposes depending on your needs—YouTube API offers official access with strict quotas, yt-dlp provides unrestricted scraping with rate-limiting challenges, and combining both leverages their complementary strengths.[^1_1]

## Feature Comparison

| **Aspect** | **YouTube API** | **yt-dlp** | **yt-dlp + API** |
| :-- | :-- | :-- | :-- |
| **Legal/TOS** | Fully compliant with YouTube TOS [^1_2] | Violates YouTube TOS (scraping) [^1_2] | Hybrid compliance (API for metadata, yt-dlp for downloads) |
| **Quota Limits** | 10,000 units/day default, requires approval for extensions [^1_3][^1_4] | No quota, but subject to rate limiting and blocks [^1_5][^1_6] | API quota applies only to metadata calls [^1_1] |
| **Rate Limiting** | 1.6M queries/minute theoretical, but tied to daily quota [^1_3] | 3-56 second mandatory delays; ~75% block rate in heavy use [^1_5] | API faster for metadata; yt-dlp handles video downloads with delays |
| **Video Downloads** | Not supported—API provides metadata only [^1_1] | Full video/audio download in any format/quality [^1_7][^1_8] | yt-dlp handles all downloads by video ID [^1_1] |
| **Metadata Access** | Fast, structured, complete channel data [^1_1] | Slow (per-video queries), missing geoblocked videos in channel lists [^1_1] | API provides comprehensive metadata efficiently |
| **Setup Complexity** | Requires OAuth, API keys, Cloud Console project [^1_4] | Command-line tool, minimal setup [^1_8] | Both setups required, but architectural coordination needed |
| **Cost** | Free within quota; extensions require compliance audit [^1_9][^1_4] | Free, but risk of IP blocks [^1_5] | API quota costs; multiple Google accounts can expand limits [^1_1] |
| **Speed** | Very fast for metadata queries [^1_1] | Slow—mandatory site delays plus bandwidth throttling (40 KB/s during peak hours) [^1_6] | Optimal—API for fast metadata, yt-dlp only when video needed |

## Use Case Recommendations

**Use YouTube API alone** when you only need metadata (titles, descriptions, comments, channel info) and want legal compliance without video downloads.[^1_2][^1_4]

**Use yt-dlp alone** for simple video archiving, offline viewing, or small-scale projects where TOS compliance isn't critical and you can tolerate rate limits.[^1_8][^1_10]

**Use yt-dlp + API** for metadata-first workflows like building a YouTube clone, managing large channel archives, or systems where you need comprehensive metadata with selective video downloads—this is the most efficient approach for scale.[^1_1]
<span style="display:none">[^1_11][^1_12][^1_13][^1_14]</span>

<div align="center">⁂</div>

[^1_1]: https://www.reddit.com/r/youtubedl/comments/1eiun85/youtube_metadata_scrapping_ytdlp_vs_api/

[^1_2]: https://dev.to/pavithran_25/how-to-legally-scrape-youtube-videos-using-the-youtube-data-api-5bk0

[^1_3]: https://stackoverflow.com/questions/77551759/please-explain-the-youtube-data-apis-quota-limits

[^1_4]: https://elfsight.com/blog/youtube-data-api-v3-limits-operations-resources-methods-etc/

[^1_5]: https://www.reddit.com/r/youtubedl/comments/1mx9kh4/why_is_ytdlp_getting_ratelimited_so_hard_lately/

[^1_6]: https://github.com/yt-dlp/yt-dlp/issues/14229

[^1_7]: https://github.com/yt-dlp/yt-dlp

[^1_8]: https://www.rapidseedbox.com/blog/yt-dlp-complete-guide

[^1_9]: https://developers.google.com/youtube/terms/developer-policies

[^1_10]: https://www.videoproc.com/download-record-video/yt-dlp-vs-youtube-dl.htm

[^1_11]: https://debricked.com/select/compare/github-yt-dlp/yt-dlp-vs-github-Tyrrrz/YoutubeExplode-vs-pypi-yt-dlp

[^1_12]: https://manpages.ubuntu.com/manpages/jammy/man1/yt-dlp.1.html

[^1_13]: https://github.com/yt-dlp/yt-dlp/issues/1170

[^1_14]: https://www.youtube.com/watch?v=MHUGuw1Agnc


---

# Deep Dive: How `yt-dlp` Actually Works

You are absolutely correct to question the "magic" under the hood. To be precise: **No, `yt-dlp` does not use the public YouTube Data API (v3).**

If it used the official API, you would need to provide a Google Cloud API Key (which costs money or has strict quotas). Instead, `yt-dlp` relies on a clever mix of **web scraping** and **Internal API emulation**.

Here is the technical breakdown of its architecture and how to navigate its massive interface.

***

### 1. The Architecture: "Innertube" vs. Public API

The confusion comes from the fact that `yt-dlp` *does* talk to an API, just not the one developers are supposed to use.

* **Public Data API (Official):** This is the "front door" for developers. It is documented, rate-limited (10k units/day), and requires an API Key. `yt-dlp` **ignores this completely**.
* **Innertube API (Internal):** This is the "back door." It is the undocumented private API that YouTube's own apps (Android app, iOS app, Smart TV app, Web Desktop) use to talk to YouTube servers.


#### How `yt-dlp` works step-by-step:

1. **Client Mimicry:** When you run a command, `yt-dlp` pretends to be a specific official client (e.g., an Android phone or a Web browser). It constructs a JSON payload with a "Context" object that perfectly matches what the real YouTube Android app sends.
2. **The "Handshake":** It sends this request to endpoints like `https://www.youtube.com/youtubei/v1/player`. YouTube's servers verify the signature and reply with the video data, thinking they are talking to a real phone.
3. **Extraction:** The response contains the "streaming data" (direct URLs to the `.mp4` or `.webm` files) and "microformat" data (metadata). `yt-dlp` parses this JSON and downloads the file.

**Why this matters:**

* **Speed:** It bypasses the overhead of loading the full visual website (HTML/CSS/JS).
* **Bypassing Limits:** If YouTube throttles the "Web" client, `yt-dlp` can switch to mimicking the "Android" or "TV" client (using flags like `--impersonate`) to get different streams that might not be throttled.

***

### 2. Navigating the "Massive Interface"

The help text is overwhelming because it exposes every single knob of this emulation engine. You can mentally group the 100+ flags into **4 Essential Layers**:

#### Layer 1: The "What" (Format \& Selection)

Controls *what* file you actually get. The default often grabs the best video but might merge incompatible formats (MKV).

* `-f bestvideo+bestaudio`: Explicitly asks for the best streams.
* `--merge-output-format mp4`: Forces the final file to be an MP4 (remuxing if necessary).
* `--write-auto-subs`: Grabs the auto-generated captions (great for AI/NLP).


#### Layer 2: The "Who" (Authentication \& Evasion)

Controls *who* YouTube thinks you are. This is critical for age-gated content or premium videos.

* `--cookies-from-browser chrome`: The "God Mode" flag. It steals the authentication session from your real Chrome browser, letting `yt-dlp` access anything *you* can see (Premium videos, Age-gated content) without you needing to extract cookie files manually.
* `--user-agent "Mozilla/..."`: Changes the browser signature.


#### Layer 3: The "How" (Network \& Throttling)

Controls the download behavior to avoid IP bans.

* `--limit-rate 5M`: Caps download speed to avoid triggering YouTube's "bot detection" alarms.
* `--sleep-requests 2`: Adds a delay between extracting data for multiple videos. **Crucial for playlists** to prevent your IP from being flagged.


#### Layer 4: The "After" (Post-Processing)

`yt-dlp` includes a mini-video-editor engine (via FFmpeg) to clean up files *after* download.

* `--embed-metadata`: Writes the title, artist, and description *inside* the .mp4 file itself.
* `--sponsorblock-remove all`: Integrates with the SponsorBlock API to automatically *cut out* sponsored segments from the video file before saving it.

***

### 3. Validated Comparison: Why "yt-dlp + API" exists

Now that we know `yt-dlp` uses the Internal API, the "Hybrid" approach makes perfect sense technically:

* **The Problem:** `yt-dlp` is **slow at discovery**. If you ask it to "Download all videos from Channel X," it has to scrape the "Videos" tab of that channel page. YouTube makes this hard by using "lazy loading" (infinite scroll). `yt-dlp` has to fire dozens of requests just to find the video URLs. It’s slow and prone to breaking if YouTube changes the UI layout.
* **The Solution (Hybrid):**

1. **Use Official Data API (Code):** You write a tiny Python script using the official Google API Key. You ask: *"Give me the list of all Upload IDs for Channel X."* The API returns a clean JSON list of 1,000 IDs in milliseconds.
2. **Use yt-dlp (Tool):** You feed those 1,000 IDs into `yt-dlp` just for the downloading part.

**Verdict:**

* **yt-dlp:** The engine for **extraction** (getting the file).
* **Official API:** The engine for **discovery** (finding the IDs).
* **Together:** The only scalable way to archive massive channels/playlists without getting IP-banned for excessive scraping.
<span style="display:none">[^2_1][^2_10][^2_11][^2_12][^2_13][^2_14][^2_15][^2_16][^2_17][^2_18][^2_19][^2_2][^2_20][^2_21][^2_3][^2_4][^2_5][^2_6][^2_7][^2_8][^2_9]</span>

<div align="center">⁂</div>

[^2_1]: paste.txt

[^2_2]: https://github.com/yt-dlp/yt-dlp

[^2_3]: https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en

[^2_4]: https://stackoverflow.com/questions/76145392/youtube-internal-api-innertube-has-not-been-used-in-project

[^2_5]: https://roundproxies.com/blog/scrape-youtube-captions/

[^2_6]: https://www.reddit.com/r/youtubedl/comments/14q2sox/does_ylpdlp_use_youtube_api/

[^2_7]: https://stackoverflow.com/questions/73247208/youtube-data-api-v3-no-longer-returns-video-captions

[^2_8]: https://skywork.ai/skypage/en/kevin-watt-yt-dlp-mcp-guide-ai-engineers/1978647870209040384

[^2_9]: https://stackoverflow.com/questions/71347719/set-metadata-based-on-the-output-filename-in-yt-dlp

[^2_10]: https://github.com/yt-dlp/yt-dlp/wiki/extractors

[^2_11]: https://mcpmarket.com/zh/server/youtube-api

[^2_12]: https://www.seedhost.net/wp/blog/yt-dlp-complete-guide

[^2_13]: https://www.reddit.com/r/youtubedl/comments/128wfzr/using_extractorargs_and_matchfilter_in_python/

[^2_14]: https://git.akarpov.ru/yt-dlp/yt-dlp/commit/2ae778b8fc56087462e48d1e31208c2a398409c1?style=unified\&whitespace=show-all\&show-outdated=

[^2_15]: https://nv1t.github.io/blog/scraping-by-my-youtube-data-adventure/

[^2_16]: https://blog.maxrenke.com/posts/ytdlpllm-A-Natural-Language-Youtube-Downloader/

[^2_17]: https://www.reddit.com/r/youtubedl/comments/x0kldb/ytdlp_extractor_arguments_and_limiting_comments/

[^2_18]: https://news.ycombinator.com/item?id=43324384

[^2_19]: https://gitea.lemnoslife.com/Benjamin_Loison/YouTube_captions_search_engine/issues/5

[^2_20]: https://www.reddit.com/r/youtubedl/comments/qzqzaz/can_someone_please_post_a_simple_guide_on_making/

[^2_21]: https://github.com/yt-dlp/yt-dlp/wiki/Extractors/47f4276c6541a5327835d6db84bbf7eac7c9a54b


---

# `yt-dlp` Practical Command Reference

**Architecture Primer:** `yt-dlp` does NOT use YouTube's public Data API v3. It emulates YouTube's internal "Innertube" API (the same one used by Android/iOS apps) by mimicking official client requests. This bypasses quotas but requires understanding how to avoid rate-limiting and IP blocks.[^3_1][^3_2]

***

## 🎯 The 4 Essential Layers (Mental Model)

### **Layer 1: THE "WHAT"** (Format \& Selection)

What quality/format you extract.

### **Layer 2: THE "WHO"** (Authentication \& Evasion)

Who YouTube thinks you are (bypass age-gates, premium content).

### **Layer 3: THE "HOW"** (Network \& Throttling)

How you download without triggering bot detection.

### **Layer 4: THE "AFTER"** (Post-Processing)

What happens to the file after download (metadata, encoding, editing).

***

## 📚 Practical Command Recipes

### **1. Audio Extraction (High-Quality Opus)**

Your existing workflow—extracting audio with embedded artwork and metadata.[^3_3]

```bash
yt-dlp --cookies-from-browser firefox \
       --user-agent "$(yt-dlp --dump-user-agent)" \
       -f bestaudio/ba* -x --audio-format opus \
       --embed-thumbnail --embed-metadata \
       -o "%(title)s.%(ext)s" \
       https://youtu.be/VIDEO_ID
```

**Breakdown:**

- `--cookies-from-browser firefox`: Steals your Firefox session cookies. Critical for age-gated or premium content.[^3_3]
- `-f bestaudio/ba*`: Requests the highest quality audio stream available.
- `-x --audio-format opus`: Extracts audio and converts to Opus codec (smallest size, excellent quality).
- `--embed-thumbnail --embed-metadata`: Writes album art and title/artist into the audio file itself.
- `-o "%(title)s.%(ext)s"`: Saves with video title as filename.[^3_4]

**Variants:**

```bash
# MP3 for compatibility with older devices
-x --audio-format mp3 --audio-quality 320K

# FLAC for archival (lossless)
-x --audio-format flac
```


***

### **2. Video Download (Best Quality, Efficient Format)**

Download highest quality video while forcing MP4 container (universally compatible).[^3_5]

```bash
yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" \
       --merge-output-format mp4 \
       -o "%(uploader)s - %(title)s [%(id)s].%(ext)s" \
       https://youtu.be/VIDEO_ID
```

**Breakdown:**

- `-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"`: Downloads best MP4 video + M4A audio, merges them. Falls back to single-file MP4 if merge fails.
- `--merge-output-format mp4`: Guarantees output is MP4 (remuxes if necessary).
- `-o "%(uploader)s - %(title)s [%(id)s].%(ext)s"`: Organizes filename as `Channel - Video Title [VIDEO_ID].mp4`.[^3_4]

**Advanced Format Selection:**

```bash
# 1080p max (saves bandwidth)
-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]"

# VP9 codec preference (better compression than H.264)
-f "bestvideo[vcodec^=vp9]+bestaudio/best"

# Specific resolution and FPS
-f "bestvideo[height=1080][fps=60]+bestaudio"
```


***

### **3. Playlist Download (Organized, Resumable)**

Download entire playlist with intelligent naming and skip already-downloaded videos.[^3_6][^3_7]

```bash
yt-dlp --download-archive archive.txt \
       --sleep-interval 5 --max-sleep-interval 15 \
       -f bestvideo+bestaudio \
       --merge-output-format mkv \
       -o "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s" \
       https://www.youtube.com/playlist?list=PLAYLIST_ID
```

**Breakdown:**

- `--download-archive archive.txt`: Creates a log file tracking downloaded video IDs. On subsequent runs, skips videos already in the log (essential for updating playlists).[^3_7]
- `--sleep-interval 5 --max-sleep-interval 15`: Waits 5-15 seconds between videos to avoid rate-limiting (randomized delay).[^3_3]
- `-o "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s"`: Creates folder named after playlist, numbers videos with zero-padding (`01, 02, 03...`).[^3_4]

**Playlist Variants:**

```bash
# Download only new videos added to playlist
--download-archive archive.txt --break-on-existing

# Download playlist in reverse (oldest first)
--playlist-reverse

# Download specific range
-I 10:50  # Videos 10 through 50

# Random shuffle
--playlist-random
```


***

### **4. Channel Archival (Metadata-Rich)**

Download all uploads from a channel with full metadata, thumbnails, and description files.[^3_5]

```bash
yt-dlp --download-archive channel_archive.txt \
       --write-info-json --write-description --write-thumbnail \
       --embed-metadata --embed-thumbnail \
       -o "%(uploader)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s" \
       https://www.youtube.com/@CHANNEL_HANDLE/videos
```

**Breakdown:**

- `--write-info-json`: Saves complete video metadata as JSON (view count, upload date, tags, etc.).[^3_3]
- `--write-description`: Saves video description to `.description` file.
- `--write-thumbnail`: Downloads thumbnail image separately.
- `-o "%(uploader)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s"`: Organizes as `Channel/YYYYMMDD - Title [ID].ext` for chronological sorting.[^3_4]

***

### **5. Live Stream Capture (From Start)**

Record a livestream from the beginning (even if you join late).[^3_3]

```bash
yt-dlp --live-from-start \
       --wait-for-video 60-300 \
       -f best \
       -o "%(upload_date)s - %(title)s.%(ext)s" \
       https://youtu.be/LIVE_STREAM_ID
```

**Breakdown:**

- `--live-from-start`: Downloads the entire stream buffer from the beginning (experimental, YouTube-only).[^3_3]
- `--wait-for-video 60-300`: If stream hasn't started, waits 60-300 seconds between checks (range creates randomized retry).

**Post-Stream Archival:**

```bash
# Wait for stream to finish, then download
--wait-for-video 60 --no-live-from-start
```


***

### **6. Subtitle/Caption Extraction**

Download auto-generated or manual subtitles in multiple formats.[^3_3]

```bash
yt-dlp --write-auto-subs --sub-langs "en.*,pt" \
       --sub-format srt \
       --convert-subs srt \
       --skip-download \
       https://youtu.be/VIDEO_ID
```

**Breakdown:**

- `--write-auto-subs`: Grabs YouTube's auto-generated captions (great for AI transcription projects).
- `--sub-langs "en.*,pt"`: Downloads all English variants (`en`, `en-US`, `en-GB`) and Portuguese. Use regex patterns for flexibility.
- `--convert-subs srt`: Forces conversion to SRT format (most compatible).
- `--skip-download`: Only downloads subtitles, skips video (fast metadata extraction).[^3_3]

***

### **7. Sponsored Content Removal (SponsorBlock Integration)**

Automatically cut out sponsor segments, intros, and outros using community-sourced timestamps.[^3_3]

```bash
yt-dlp --sponsorblock-remove sponsor,intro,outro \
       -f bestvideo+bestaudio \
       --merge-output-format mp4 \
       -o "%(title)s.%(ext)s" \
       https://youtu.be/VIDEO_ID
```

**Breakdown:**

- `--sponsorblock-remove sponsor,intro,outro`: Downloads video, then uses FFmpeg to physically cut out segments flagged by the SponsorBlock community database.[^3_3]
- Categories: `sponsor`, `intro`, `outro`, `selfpromo`, `preview`, `filler`, `interaction`, `music_offtopic`.

**Chapter Marking (Non-Destructive):**

```bash
# Mark segments as chapters instead of removing them
--sponsorblock-mark all
```


***

### **8. Geo-Restricted Content Bypass**

Access region-locked videos using proxy or VPN.[^3_3]

```bash
yt-dlp --proxy socks5://127.0.0.1:1080 \
       --geo-verification-proxy 127.0.0.1:1080 \
       -f best \
       https://youtu.be/VIDEO_ID
```

**Breakdown:**

- `--proxy socks5://...`: Routes traffic through SOCKS5 proxy (combine with SSH tunnel or commercial VPN).
- `--geo-verification-proxy`: Uses separate proxy just for geo-checks (main download can use direct connection for speed).

***

### **9. Batch Download from File**

Process multiple URLs from a text file (one per line).[^3_3]

```bash
yt-dlp --batch-file urls.txt \
       --download-archive batch_archive.txt \
       --sleep-interval 10 \
       -f best \
       -o "%(uploader)s/%(title)s.%(ext)s"
```

**urls.txt format:**

```
https://youtu.be/VIDEO_ID_1
https://youtu.be/VIDEO_ID_2
# Comments start with #
https://www.youtube.com/playlist?list=PLAYLIST_ID
```


***

### **10. Metadata-Only Extraction (No Download)**

Fetch video metadata as JSON without downloading video (useful for building databases).[^3_8][^3_7]

```bash
yt-dlp --dump-json --skip-download \
       https://youtu.be/VIDEO_ID > metadata.json
```

**Extract Specific Fields:**

```bash
# Print just title and view count
yt-dlp --print "%(title)s - %(view_count)d views" \
       --skip-download \
       https://youtu.be/VIDEO_ID

# Build archive of video IDs without downloading
yt-dlp --download-archive archive.txt \
       --skip-download --force-write-archive \
       https://www.youtube.com/@CHANNEL/videos
```


***

## 🛡️ Anti-Ban Best Practices

YouTube's anti-scraping measures trigger on aggressive behavior. Use these flags together for large-scale operations:[^3_9][^3_10]

```bash
# "Stealth Mode" template
yt-dlp --cookies-from-browser chrome \
       --sleep-requests 2 \
       --sleep-interval 10 --max-sleep-interval 30 \
       --limit-rate 5M \
       --download-archive archive.txt \
       [URLs...]
```

**Key Tactics:**

- `--sleep-requests 2`: 2-second delay between metadata API calls (not downloads).[^3_3]
- `--limit-rate 5M`: Caps download speed at 5 MB/s (avoids "streaming too fast" detection).[^3_3]
- `--retries 10 --fragment-retries infinite`: Resilient to temporary throttling.[^3_3]

***

## 📖 Output Template Cheat Sheet

Common variables for `-o` flag:[^3_4]


| **Variable** | **Example Output** | **Use Case** |
| :-- | :-- | :-- |
| `%(title)s` | `How to Use yt-dlp` | Human-readable filename |
| `%(id)s` | `dQw4w9WgXcQ` | Unique video identifier |
| `%(uploader)s` | `Rick Astley` | Channel name |
| `%(upload_date)s` | `20091025` | YYYYMMDD format |
| `%(playlist)s` | `Best of 2024` | Playlist name |
| `%(playlist_index)02d` | `05` | Zero-padded position |
| `%(ext)s` | `webm` | File extension |
| `%(height)sp` | `1080p` | Resolution tag |
| `%(duration)d` | `213` | Length in seconds |

**Advanced Expressions:**

```bash
# Conditional formatting (if/else logic)
-o "%(uploader,NA)s/%(title).100s.%(ext)s"
# Truncates title to 100 chars, uses "NA" if uploader is missing

# Date formatting
-o "%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s"
# Output: 2024-12-08 - Video Title.mp4
```


***

## 🔧 Configuration File (Permanent Settings)

Instead of typing flags every time, save defaults to `~/.config/yt-dlp/config` (Linux/macOS) or `%APPDATA%\yt-dlp\config.txt` (Windows):[^3_3]

```ini
# Always use Firefox cookies
--cookies-from-browser firefox

# Embed metadata and thumbnails by default
--embed-metadata
--embed-thumbnail

# Rate limiting to avoid bans
--sleep-interval 5
--max-sleep-interval 15
--limit-rate 5M

# Archive tracking
--download-archive ~/.config/yt-dlp/archive.txt

# Default output template
-o "%(uploader)s/%(title)s [%(id)s].%(ext)s"
```

**Override config for one-off commands:**

```bash
yt-dlp --ignore-config [other flags...] URL
```


***

## 🚨 Common Gotchas

1. **Slow Downloads (40 KB/s):** YouTube throttles during peak hours. Use `--throttled-rate 100K` to trigger re-extraction if speed drops below threshold.[^3_10]
2. **"No video formats" Error:** Video might be private/deleted. Use `--ignore-no-formats-error` to continue processing other URLs.[^3_3]
3. **FFmpeg Missing:** Required for merging streams and post-processing. Install via package manager: `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Linux).
4. **Cookie Expiration:** If `--cookies-from-browser` fails, manually export cookies using a browser extension and use `--cookies cookies.txt` instead.
5. **Playlist Limits:** Some channels have thousands of videos. Use `-I 1:500` to download in chunks, then `-I 501:1000`, etc.

***

## 🎓 Learning Path

**Beginner:** Start with single video downloads using `-f best`.
**Intermediate:** Master playlist downloads with `--download-archive`.
**Advanced:** Combine with Official YouTube Data API for metadata discovery, then feed IDs to `yt-dlp` for downloads.[^3_11]

**Essential Commands to Memorize:**

```bash
# Test output filename without downloading
yt-dlp --print filename -o "YOUR_TEMPLATE" URL

# List available formats
yt-dlp -F URL

# Simulate download (dry-run)
yt-dlp -s URL
```

This reference covers the 95% use cases for YouTube content archival, audio extraction, and metadata collection workflows.[^3_6][^3_7][^3_5][^3_4][^3_3]
<span style="display:none">[^3_12][^3_13][^3_14][^3_15][^3_16]</span>

<div align="center">⁂</div>

[^3_1]: https://www.reddit.com/r/youtubedl/comments/14q2sox/does_ylpdlp_use_youtube_api/

[^3_2]: https://git.akarpov.ru/yt-dlp/yt-dlp/commit/2ae778b8fc56087462e48d1e31208c2a398409c1?style=unified\&whitespace=show-all\&show-outdated=

[^3_3]: paste.txt

[^3_4]: https://yt-dlp.eknerd.com/docs/basic usage/output-templates/

[^3_5]: https://www.rapidseedbox.com/blog/yt-dlp-complete-guide

[^3_6]: https://www.tglyn.ch/blog/youtube_download_for_djs/

[^3_7]: https://github.com/yt-dlp/yt-dlp/issues/2754

[^3_8]: https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en

[^3_9]: https://www.reddit.com/r/youtubedl/comments/1mx9kh4/why_is_ytdlp_getting_ratelimited_so_hard_lately/

[^3_10]: https://github.com/yt-dlp/yt-dlp/issues/14229

[^3_11]: https://www.reddit.com/r/youtubedl/comments/1eiun85/youtube_metadata_scrapping_ytdlp_vs_api/

[^3_12]: https://github.com/yt-dlp/yt-dlp

[^3_13]: https://www.reddit.com/r/youtubedl/comments/1632a40/ytdlp_unexpected_output_template_examples_while/

[^3_14]: https://github.com/yt-dlp/yt-dlp/issues/6063

[^3_15]: https://www.reddit.com/r/youtubedl/comments/yfh70l/how_to_download_an_entire_playlist_total_and/

[^3_16]: https://manpages.debian.org/trixie-backports/yt-dlp/yt-dlp.1.en.html


---

# I don't know if it's possible, but can you organize this more into a table? I mean, in the sense that it could be an actual way for us to organize the flags that are needed and how they are needed. Almost like a note about creating these commands depending on what we need to do.

So: what flags are available, how to pass in all types of flags for these different categories, and how to build all of these flags into the final command.

I want to note that the focus should be on creating this idea—on actually organizing this information around the yt-dlp commands. I kind of just passed my own example before so it could serve as an example that we ourselves can keep saving. But at the same time, it becomes harder to get both the scope of what yt-dlp actually does plus, when we're actually troubleshooting and building commands, sometimes we're really lost.

Even that help command is of no use. It's just overwhelming to filter out what you want from that big pile of shit. That's what we're doing—putting our gloves on and organizing this whole mess into a clear, practical note. It's really more like a real walkthrough guide that doesn't exist. I feel like we can create our own here, really properly, focusing on how we can generate commands properly, more than anything else.

And this big help command is just to show how unpractical things can be sometimes.

Below is a compact, “command-building” guide for `yt-dlp`, organized in tables and focused on how to combine flags into usable commands. It is not exhaustive, but it gives a practical mental model and concrete patterns for composing commands.

***

## Overview: Command Skeleton

```bash
yt-dlp [GLOBAL FLAGS] [WHAT] [WHO] [HOW] [AFTER] URL...
```

Think in four layers:

- WHAT = formats, selection, subtitles
- WHO = cookies, identity
- HOW = network, sleep, retries
- AFTER = metadata, audio extraction, SponsorBlock, etc.

***

## WHAT: Formats, Selection, Subtitles

### Video/Audio Formats

| Goal | Key Flags | Notes / Typical Usage |
| :-- | :-- | :-- |
| Best video + audio (separate, merged) | `-f "bestvideo+bestaudio"` | Highest quality, often results in MKV if codecs differ. |
| Force MP4 output | `-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"` + `--merge-output-format mp4` | Good default for compatibility. |
| Limit resolution (e.g. 1080p max) | `-f "bestvideo[height<=1080]+bestaudio/best[height<=1080]"` | Keeps bandwidth/storage reasonable. |
| Prefer certain codec (e.g. VP9) | `-f "bestvideo[vcodec^=vp9]+bestaudio/best"` | Prioritize VP9 if present. |
| Audio-only (best) | `-f bestaudio` | Use alone or with `-x` to extract to audio file. |

### Audio Extraction

| Goal | Flags | Example Command Core |
| :-- | :-- | :-- |
| Extract audio in Opus | `-x --audio-format opus` | `yt-dlp -f bestaudio -x --audio-format opus URL` |
| Extract audio in MP3 | `-x --audio-format mp3 --audio-quality 320K` | For max MP3 quality. |
| Keep original container (no re-encode) | `-x --audio-format best` | Just demux audio stream if possible. |

### Subtitles / Captions

| Goal | Flags | Example Core |
| :-- | :-- | :-- |
| List available subs | `--list-subs` | `yt-dlp --list-subs URL` |
| Download auto subtitles | `--write-auto-subs` | Grabs auto-generated captions. |
| Select languages | `--sub-langs "en.*,pt"` | Regex and multiple langs allowed. |
| Subtitle format | `--sub-format srt` | Preferred compressed text format. |
| Only subtitles, no video | `--skip-download` | Combine with sub flags for metadata-only runs. |


***

## WHO: Identity, Cookies, Auth

### Identity Basics

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Use browser cookies (recommended) | `--cookies-from-browser firefox` (or `chrome`, etc.) | Easiest way to get age-restricted/Premium content without managing cookies manually. |
| Use manual cookie file | `--cookies cookies.txt` | When exporting cookies via browser extensions. |
| Custom User-Agent | `--user-agent "..."` | You can auto-dump the default UA with `yt-dlp --dump-user-agent`. |

Your own example fits here:

```bash
yt-dlp --cookies-from-browser firefox \
       --user-agent "$(yt-dlp --dump-user-agent)" \
       -f bestaudio/ba* -x --audio-format opus \
       --embed-thumbnail --embed-metadata \
       -o "%(title)s.%(ext)s" \
       https://youtu.be/VIDEO_ID
```


***

## HOW: Network, Throttling, Robustness

### Anti-throttle / Stability Flags

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Limit bandwidth | `--limit-rate 5M` | Avoids looking like a “vacuum cleaner” connection. |
| Sleep between downloads | `--sleep-interval 5 --max-sleep-interval 15` | Random delay between items; good for playlists/channels. |
| Sleep between requests | `--sleep-requests 2` | Delay between internal metadata/API calls. |
| Retry behavior | `--retries 10 --fragment-retries infinite` | More resilient to temporary errors. |
| Per-fragment speed detection | `--throttled-rate 100K` | Trigger re-extraction when speed drops below threshold. |

### Geo / Proxy

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Use HTTP/SOCKS proxy | `--proxy socks5://127.0.0.1:1080` | Combine with local tunnel/VPN. |
| Proxy only for geo-check | `--geo-verification-proxy 127.0.0.1:1080` | Use proxy only for geo tests. |


***

## AFTER: Post-processing, Metadata, SponsorBlock

### Metadata, Thumbnails, Files

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Embed metadata into file | `--embed-metadata` | Adds title, artist, etc. into media container. |
| Embed thumbnail | `--embed-thumbnail` | Cover art in audio/video file (needs ffmpeg). |
| Save description | `--write-description` | `.description` file. |
| Save full info JSON | `--write-info-json` | For programmatic processing. |
| Clean info JSON | `--clean-info-json` / `--no-clean-info-json` | Decide whether to keep internal fields. |

### SponsorBlock \& Chapters

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Remove sponsor segments | `--sponsorblock-remove sponsor,intro,outro` | Physically cuts sections. |
| Only mark sponsors as chapters | `--sponsorblock-mark all` | Non-destructive; segments become chapters. |
| Control SB server | `--sponsorblock-api URL` | Use default or custom instance. |

### Splitting / Trimming

| Goal | Flags | Notes |
| :-- | :-- | :-- |
| Only download certain chapters/time ranges | `--download-sections "00:30-05:00"` | Needs ffmpeg. |
| Split file by chapters | `--split-chapters` | Creates multiple files from internal chapters. |
| Remove certain chapters | `--remove-chapters "sponsor"` | Based on title regex. |


***

## Output Templates: Organizing Files

### Common Fields

| Token | Meaning |
| :-- | :-- |
| `%(title)s` | Video title. |
| `%(id)s` | YouTube video ID. |
| `%(uploader)s` | Channel / uploader name. |
| `%(upload_date)s` | Date as `YYYYMMDD`. |
| `%(playlist)s` | Playlist title. |
| `%(playlist_index)02d` | Position within playlist, zero-padded. |
| `%(ext)s` | File extension. |

### Template Patterns

| Use Case | Example Template |
| :-- | :-- |
| Simple, flat | `-o "%(title)s.%(ext)s"` |
| Per-uploader folder | `-o "%(uploader)s/%(title)s.%(ext)s"` |
| Playlist with ordering | `-o "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s"` |
| Archive style (date + ID) | `-o "%(upload_date)s - %(title)s [%(id)s].%(ext)s"` |


***

## Higher-level Patterns: “Recipes” Table

Below: how to think “I want X” → “Plug these flags into the skeleton”.

### Single-Video Recipes

| Task | Core Flags | Skeleton Command |
| :-- | :-- | :-- |
| Download best video (MP4) | `-f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" --merge-output-format mp4` | `yt-dlp [WHO] [HOW] [AFTER] (these WHAT flags) URL` |
| Extract audio as Opus | `-f bestaudio -x --audio-format opus` | Add `--embed-thumbnail --embed-metadata` if desired. |
| Download with subs | `-f best --write-auto-subs --sub-langs "en.*" --sub-format srt` | Optional `--embed-subs` to mux subs. |
| Metadata-only inspect | `--dump-json --skip-download` | Redirect to file or pipe to jq. |

### Playlist / Channel Recipes

| Task | Core Flags | Notes |
| :-- | :-- | :-- |
| Archive playlist (video) | `--download-archive archive.txt -f bestvideo+bestaudio --merge-output-format mkv --sleep-interval 5 --max-sleep-interval 15 -o "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s"` | Re-run periodically; only new videos download. |
| Archive channel uploads | `--download-archive channel_archive.txt --write-info-json --write-description --write-thumbnail -f best --sleep-interval 5 --max-sleep-interval 15 -o "%(uploader)s/%(upload_date)s - %(title)s [%(id)s].%(ext)s"` | Creates structured archive tree. |
| Only new videos from playlist | `--download-archive archive.txt --break-on-existing` | Stops once it hits previously-downloaded item in feed-order lists. |

### Live / Special

| Task | Core Flags | Notes |
| :-- | :-- | :-- |
| Record livestream from start | `--live-from-start --wait-for-video 60-300 -f best` | For upcoming scheduled live events. |
| Download geoblocked video | `--proxy socks5://127.0.0.1:1080 --geo-verification-proxy 127.0.0.1:1080` | Requires working proxy/tunnel in correct region. |
| Remove sponsor segments | `--sponsorblock-remove sponsor,intro,outro -f bestvideo+bestaudio --merge-output-format mp4` | Great for long-form content. |


***

## How to Build Commands Systematically

When you’re “lost in the big help”, use this 4-step procedure:


| Step | Question | Typical Choice |
| :-- | :-- | :-- |
| 1. WHAT? | Do you want video, audio, subs, or just metadata? | Pick one of the format/subtitle recipes. |
| 2. WHO? | Does it need login / age-gated / Premium? | Add `--cookies-from-browser` and maybe custom user-agent. |
| 3. HOW? | Is this a one-off or large batch? Need to be gentle? | Add sleep, rate limits, retries for anything > a few videos. |
| 4. AFTER? | Do you want a clean media library or a raw dump? | Add metadata embed, thumbnails, SponsorBlock, chapter splitting as desired. |

Then snap them together:

```bash
yt-dlp \
  [WHO] \
  [HOW] \
  [WHAT] \
  [AFTER] \
  URL...
```

For example, “Archival audio from long playlist, safe on network, nicely tagged”:

```bash
yt-dlp \
  --cookies-from-browser firefox \
  --sleep-interval 5 --max-sleep-interval 20 --limit-rate 5M \
  --download-archive playlist_audio.txt \
  -f bestaudio -x --audio-format opus \
  --embed-thumbnail --embed-metadata \
  -o "%(playlist)s/%(playlist_index)02d - %(title)s.%(ext)s" \
  "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

You can then lift pieces out of this table-structure whenever troubleshooting:

- Change only WHAT when quality is wrong.
- Change only HOW when you’re getting rate-limited.
- Change only AFTER when tags/chapters aren’t right.

This “layered tables + skeleton” approach gives you a stable mental map so the huge `--help` dump becomes a reference instead of a wall of noise.

