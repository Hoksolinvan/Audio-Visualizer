import sys
import os
import threading
import tempfile
import wave
import numpy as np
import pygame
import yt_dlp

URL   = "https://youtu.be/kjUwLy9h20k?si=i4Kc79Oim29v240K"
W, H  = 1200, 700
FPS   = 60
CHUNK = 2048
RATE  = 44100
N_BARS    = 80
SMOOTHING = 0.78
PEAK_HOLD = 45
PEAK_FALL = 0.92
GRAD_TOP  = (0, 220, 255)
GRAD_MID  = (80, 255, 100)
GRAD_BOT  = (255, 60, 80)


class AudioAnalyzer:
    def __init__(self, url):
        self.url         = url
        self._title      = ""
        self._lock       = threading.Lock()
        self._audio_data = None

    def start(self):
        threading.Thread(target=self._download_and_play, daemon=True).start()

    def stop(self):
        pygame.mixer.stop()

    def get_title(self):
        return self._title

    def get_chunk(self):
        with self._lock:
            if self._audio_data is None:
                return None
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms < 0:
                return None
            pos_sample = int(pos_ms / 1000 * RATE)
            start = max(0, pos_sample - CHUNK // 2)
            end   = start + CHUNK
            if end > len(self._audio_data):
                return None
            return self._audio_data[start:end].copy()

    def _download_and_play(self):
        tmp_dir  = tempfile.mkdtemp()
        ydl_opts = {
            "format":     "bestaudio/best",
            "outtmpl":    os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "quiet":      True,
            "noplaylist": True,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav"}],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.url, download=True)
            self._title = info.get("title", "Unknown")

        wav_path = next(os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith(".wav"))

        with wave.open(wav_path, "rb") as wf:
            n_ch, sampw, fr, n_frame = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
            raw = wf.readframes(n_frame)

        dtype_map = {2: np.int16, 4: np.int32}
        scale_map = {2: 32768.0, 4: 2147483648.0}
        samples   = np.frombuffer(raw, dtype=dtype_map[sampw]).astype(np.float32) / scale_map[sampw]

        if n_ch > 1:
            samples = samples.reshape(-1, n_ch).mean(axis=1)
        if fr != RATE:
            new_len = int(len(samples) / fr * RATE)
            samples = np.interp(np.linspace(0, len(samples)-1, new_len), np.arange(len(samples)), samples)

        with self._lock:
            self._audio_data = samples

        pygame.mixer.music.load(wav_path)
        pygame.mixer.music.play()


def compute_spectrum(chunk):
    magnitude = np.abs(np.fft.rfft(chunk * np.hanning(len(chunk)), n=CHUNK))
    freqs     = np.fft.rfftfreq(CHUNK, 1 / RATE)
    edges     = np.logspace(np.log10(20), np.log10(18000), N_BARS + 1)
    bars      = np.array([magnitude[(freqs >= edges[i]) & (freqs < edges[i+1])].max()
                          if ((freqs >= edges[i]) & (freqs < edges[i+1])).any() else 0
                          for i in range(N_BARS)])
    bars = np.log1p(bars)
    mx   = bars.max()
    return bars / mx if mx > 0 else bars


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))

def bar_color(v):
    return lerp_color(GRAD_BOT, GRAD_MID, v * 2) if v < 0.5 else lerp_color(GRAD_MID, GRAD_TOP, (v - 0.5) * 2)


def main():
    pygame.init()
    pygame.mixer.init(frequency=RATE, size=-16, channels=1, buffer=CHUNK)

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Audio Visualizer")
    clock   = pygame.time.Clock()
    font_lg = pygame.font.SysFont("monospace", 22, bold=True)
    font_sm = pygame.font.SysFont("monospace", 14)

    bars_smooth = np.zeros(N_BARS)
    peaks       = np.zeros(N_BARS)
    peak_timers = np.zeros(N_BARS, dtype=int)

    analyzer = AudioAnalyzer(URL)
    analyzer.start()
    state = "loading"
    frame = 0

    # pre-bake background
    bg = pygame.Surface((W, H))
    for y in range(H):
        pygame.draw.line(bg, lerp_color((8, 8, 20), (18, 8, 35), y / H), (0, y), (W, y))
    for x in range(0, W, 60):
        pygame.draw.line(bg, (20, 20, 45), (x, 0), (x, H))
    for y in range(0, H, 60):
        pygame.draw.line(bg, (20, 20, 45), (0, y), (W, y))

    VIS_TOP    = 100
    VIS_BOT    = H - 80
    VIS_H      = VIS_BOT - VIS_TOP
    BAR_AREA_W = W - 120
    BAR_W      = BAR_AREA_W // N_BARS - 2
    X_OFF      = 60

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                analyzer.stop()
                pygame.quit()
                sys.exit()

        if state == "loading" and analyzer.get_chunk() is not None:
            state = "playing"

        screen.blit(bg, (0, 0))

        if state == "loading":
            dots = "." * ((frame // 20) % 4)
            surf = font_lg.render(f"Downloading{dots}", True, (80, 200, 255))
            screen.blit(surf, (W//2 - surf.get_width()//2, H//2 - 20))

        elif state == "playing":
            chunk = analyzer.get_chunk()
            if chunk is not None and len(chunk) == CHUNK:
                raw_bars    = compute_spectrum(chunk)
                bars_smooth = bars_smooth * SMOOTHING + raw_bars * (1 - SMOOTHING)
                for i in range(N_BARS):
                    if bars_smooth[i] >= peaks[i]:
                        peaks[i], peak_timers[i] = bars_smooth[i], PEAK_HOLD
                    else:
                        peak_timers[i] = max(0, peak_timers[i] - 1)
                        if peak_timers[i] == 0:
                            peaks[i] *= PEAK_FALL

            for i in range(N_BARS):
                amp   = float(bars_smooth[i])
                bh    = int(amp * VIS_H)
                bx    = X_OFF + i * (BAR_AREA_W // N_BARS)
                by    = VIS_BOT - bh
                color = bar_color(amp)

                if bh > 2:
                    glow = pygame.Surface((BAR_W + 12, bh + 12), pygame.SRCALPHA)
                    pygame.draw.rect(glow, (*color, 30), (0, 0, BAR_W + 12, bh + 12), border_radius=3)
                    screen.blit(glow, (bx - 6, by - 6))
                    pygame.draw.rect(screen, color, (bx, by, BAR_W, bh), border_radius=3)
                    pygame.draw.rect(screen, lerp_color(color, (255,255,255), 0.4),
                                     (bx, by, BAR_W, max(2, bh // 10)), border_radius=2)

                pk_y = VIS_BOT - int(float(peaks[i]) * VIS_H)
                pygame.draw.rect(screen, lerp_color(color, (255,255,255), 0.5), (bx, pk_y - 3, BAR_W, 3), border_radius=1)

            pygame.draw.line(screen, (40, 40, 80), (X_OFF, VIS_BOT), (W - X_OFF, VIS_BOT), 1)

            title = analyzer.get_title()[:80]
            ts = font_lg.render(f"♪  {title}", True, (140, 200, 255))
            screen.blit(ts, (W//2 - ts.get_width()//2, 22))

            pos_ms = pygame.mixer.music.get_pos()
            ps = font_sm.render(f"{pos_ms//60000:02d}:{(pos_ms//1000)%60:02d}", True, (60, 100, 160))
            screen.blit(ps, (W - 80, 28))

        pygame.display.flip()
        clock.tick(FPS)
        frame += 1


if __name__ == "__main__":
    main()
