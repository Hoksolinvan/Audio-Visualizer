# 🎵 YouTube Audio Visualizer
 
A real-time audio spectrum visualizer that streams any YouTube video as audio and renders an animated bar visualizer using pygame.
 
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![pygame](https://img.shields.io/badge/pygame-2.x-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)
 
---
 
## Features
 
- **YouTube audio streaming** — downloads and plays audio from any YouTube URL via `yt-dlp` and FFmpeg
- **Real-time FFT spectrum analysis** — 80 frequency bars across a logarithmic 20 Hz–18 kHz scale
- **Smooth animations** — exponential smoothing and peak-hold/fall indicators per bar
- **Gradient coloring** — bars shift from red (low amplitude) through green to cyan (high amplitude)
- **Glow effect** — semi-transparent bloom drawn behind each bar
- **Track title + playback timer** — displayed live on screen
 
---
 
## Requirements
 
### Python packages
 
```
pygame
numpy
yt-dlp
```
 
Install with:
 
```bash
pip install pygame numpy yt-dlp
```
 
### System dependency
 
**FFmpeg** must be installed and available on your `PATH` — `yt-dlp` uses it to extract audio as WAV.
 
| OS | Install command |
|----|----------------|
| macOS | `brew install ffmpeg` |
| Ubuntu/Debian | `sudo apt install ffmpeg` |
| Windows | Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH |
 
---
 
## Usage
 
1. Clone or download the script.
2. Open the file and set the `URL` constant to any YouTube video URL:
 
```python
URL = "https://youtu.be/your_video_id"
```
 
3. Run it:
 
```bash
python visualizer.py
```
 
The window will show a **"Downloading…"** indicator while `yt-dlp` fetches and converts the audio. Playback and visualization begin automatically once the download is complete.
 
**Press `Escape` or close the window to quit.**
 
---
 
## Configuration
 
All tuneable constants are at the top of the file:
 
| Constant | Default | Description |
|----------|---------|-------------|
| `URL` | YouTube link | Source video to visualize |
| `W`, `H` | `1200`, `700` | Window dimensions (px) |
| `FPS` | `60` | Target frame rate |
| `CHUNK` | `2048` | FFT window size (samples) |
| `RATE` | `44100` | Audio sample rate (Hz) |
| `N_BARS` | `80` | Number of frequency bars |
| `SMOOTHING` | `0.78` | Bar smoothing factor (0 = none, 1 = frozen) |
| `PEAK_HOLD` | `45` | Frames a peak marker holds before falling |
| `PEAK_FALL` | `0.92` | Decay multiplier applied to falling peaks |
| `GRAD_TOP` | `(0, 220, 255)` | Cyan — top of amplitude gradient |
| `GRAD_MID` | `(80, 255, 100)` | Green — mid gradient |
| `GRAD_BOT` | `(255, 60, 80)` | Red — bottom of amplitude gradient |
 
---
 
## How It Works
 
1. **Download** — `yt-dlp` downloads the best available audio stream and `FFmpegExtractAudio` converts it to a `.wav` file in a temp directory.
2. **Load** — The WAV is read into a NumPy float32 array, down-mixed to mono, and resampled to `RATE` if needed.
3. **Playback** — `pygame.mixer.music` plays the WAV file.
4. **Analysis** — Each frame, the current playback position is used to slice a `CHUNK`-sample window from the audio array. A Hann-windowed real FFT is computed, and bins are grouped into `N_BARS` logarithmically-spaced bands.
5. **Render** — Bars are drawn with smoothing, peak markers, glow surfaces, and a gradient color mapped to amplitude.
 
---
 
## Notes
 
- The entire audio file is downloaded before playback begins — there is no live streaming of audio data.
- Temporary WAV files are written to the OS temp directory and are not cleaned up automatically on exit.
- Visualizer sync is based on `pygame.mixer.music.get_pos()`, which may drift slightly for very long tracks.
 
