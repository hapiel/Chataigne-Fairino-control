import csv
import threading
import time


class PathPlayer:
    """
    Plays back a recorded CSV path by broadcasting joint positions over OSC.
    Chataigne (or any OSC router) decides what to do with those positions.

    Trim commands are DESTRUCTIVE: they modify the in-memory frames and
    immediately overwrite the source file.

    OSC API (wired in fairino_server.py):
        /playback/load  [filename]       — load file (opens dialog if no filename)
        /playback/start [speed]          — start playback (default 1.0x speed)
        /playback/stop                   — stop playback
        /playback/pause                  — pause
        /playback/resume                 — resume from pause
        /playback/scrub <0.0–1.0>        — preview a single frame (no playback)
        /playback/trim_start <0.0–1.0>   — remove everything before this point, re-zero timestamps, save
        /playback/trim_end   <0.0–1.0>   — remove everything after this point, save
        /playback/status                 — request status broadcast

    Joint output address:  /j_pos_playback  [j1, j2, j3, j4, j5, j6]

    Status broadcast on /playback/status:
        [is_playing, is_paused, current_frame, total_frames, current_position, duration]
    """

    def __init__(self, osc_client, save_dir: str = "recordings"):
        self._client = osc_client
        self.save_dir = save_dir

        self._frames: list[dict] = []
        self._loaded_path: str | None = None
        self._backup_path: str | None = None

        self._is_playing = False
        self._is_paused  = False
        self._stop_event  = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()   # set = running, clear = paused
        self._thread: threading.Thread | None = None
        self._current_frame_idx = 0

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def duration(self) -> float:
        return self._frames[-1]["t"] if self._frames else 0.0

    @property
    def current_position(self) -> float:
        """Current playback position as 0.0–1.0."""
        if not self._frames:
            return 0.0
        return self._current_frame_idx / max(len(self._frames) - 1, 1)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, path: str | None = None):
        """Load a CSV recording. Opens a file dialog if path is falsy."""
        if self._is_playing:
            print("[Player] Cannot load while playing")
            return
        if path:
            self._load_from_path(path)
        else:
            from recorder import ask_open_path
            ask_open_path(save_dir=self.save_dir, callback=self._load_from_path)

    def _load_from_path(self, path: str | None):
        if not path:
            print("[Player] Load cancelled")
            return
        try:
            with open(path, newline="") as f:
                frames = [
                    {k: float(v) for k, v in row.items()}
                    for row in csv.DictReader(f)
                ]
            self._frames = frames
            self._loaded_path = path
            self._backup_path = None
            self._current_frame_idx = 0
            print(f"[Player] Loaded {len(frames)} frames ({self.duration:.2f}s) from {path}")
            self._send_status()
        except Exception as e:
            print(f"[Player] Load failed: {e}")

    # ------------------------------------------------------------------
    # Scrub (non-destructive preview)
    # ------------------------------------------------------------------

    def scrub(self, position: float):
        """
        Broadcast the frame at normalised position 0.0–1.0 to /j_pos_playback.
        Does not modify any data. Only works when not playing.
        """
        if not self._frames or self._is_playing:
            return
        position = max(0.0, min(1.0, position))
        idx = int(position * (len(self._frames) - 1))
        self._current_frame_idx = idx
        self._client.send_message("/j_pos_playback", _joints(self._frames[idx]))
        self._send_status()

    # ------------------------------------------------------------------
    # Trim (destructive — modifies frames and overwrites file)
    # ------------------------------------------------------------------

    def trim_start(self, position: float):
        """
        Remove all frames before the normalised position.
        Timestamps are re-zeroed so the first remaining frame starts at t=0.
        The source file is overwritten immediately.
        """
        if self._is_playing:
            print("[Player] Cannot trim while playing")
            return
        if not self._frames:
            return
        position = max(0.0, min(1.0, position))
        idx = int(position * (len(self._frames) - 1))
        if idx == 0:
            print("[Player] Trim start: nothing to remove")
            return
        t_offset = self._frames[idx]["t"]
        self._frames = self._frames[idx:]
        for frame in self._frames:
            frame["t"] -= t_offset
        self._current_frame_idx = 0
        print(f"[Player] Trimmed start: removed {idx} frames ({t_offset:.3f}s)")
        self._write_backup()
        self._write()
        self._send_status()

    def trim_end(self, position: float):
        """
        Remove all frames after the normalised position.
        The source file is overwritten immediately.
        """
        if self._is_playing:
            print("[Player] Cannot trim while playing")
            return
        if not self._frames:
            return
        position = max(0.0, min(1.0, position))
        idx = int(position * (len(self._frames) - 1))
        if idx >= len(self._frames) - 1:
            print("[Player] Trim end: nothing to remove")
            return
        removed = len(self._frames) - idx - 1
        self._frames = self._frames[: idx + 1]
        self._current_frame_idx = min(self._current_frame_idx, len(self._frames) - 1)
        print(f"[Player] Trimmed end: removed {removed} frames")
        self._write_backup()
        self._write()
        self._send_status()

    def undo_trim(self):
        """Restore the file saved just before the last trim operation."""
        if self._is_playing:
            print("[Player] Cannot undo while playing")
            return
        if not self._backup_path:
            print("[Player] No backup available")
            return
        import shutil
        try:
            shutil.copy2(self._backup_path, self._loaded_path)
            print(f"[Player] Restored backup → {self._loaded_path}")
            self._backup_path = None
            self._load_from_path(self._loaded_path)
        except Exception as e:
            print(f"[Player] Undo failed: {e}")

    def _write_backup(self):
        if not self._loaded_path:
            return
        import os
        folder = os.path.dirname(self._loaded_path)
        filename = os.path.basename(self._loaded_path)
        self._backup_path = os.path.join(folder, f"backup_{filename}")
        try:
            import shutil
            shutil.copy2(self._loaded_path, self._backup_path)
        except Exception as e:
            print(f"[Player] Backup failed: {e}")
            self._backup_path = None

    def _write(self):
        if not self._loaded_path:
            print("[Player] No file path to save to")
            return
        try:
            fieldnames = ["t", "j1", "j2", "j3", "j4", "j5", "j6",
                          "x",  "y",  "z",  "rx", "ry", "rz"]
            with open(self._loaded_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for frame in self._frames:
                    writer.writerow({k: f"{v:.3f}" for k, v in frame.items()})
            print(f"[Player] Saved {len(self._frames)} frames → {self._loaded_path}")
        except Exception as e:
            print(f"[Player] Save failed: {e}")

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def start(self, speed: float = 1.0):
        if self._is_playing:
            print("[Player] Already playing")
            return
        if not self._frames:
            print("[Player] No file loaded")
            return
        speed = max(0.01, float(speed))
        self._stop_event.clear()
        self._pause_event.set()
        self._is_paused  = False
        self._is_playing = True
        self._thread = threading.Thread(
            target=self._play_loop, args=(speed,), daemon=True
        )
        self._thread.start()

    def stop(self):
        if not self._is_playing:
            return
        self._pause_event.set()   # unblock pause-hold loop
        self._stop_event.set()

    def pause(self):
        if self._is_playing and not self._is_paused:
            self._pause_event.clear()
            self._is_paused = True
            print("[Player] Paused")
            self._send_status()

    def resume(self):
        if self._is_playing and self._is_paused:
            self._is_paused = False
            self._pause_event.set()
            print("[Player] Resumed")
            self._send_status()

    # ------------------------------------------------------------------
    # Playback thread
    # ------------------------------------------------------------------

    def _play_loop(self, speed: float):
        frames = self._frames   # play the full (possibly trimmed) recording

        try:
            print(f"[Player] Playback - {len(frames)} frames at {speed:.2f}x speed")

            t0_wall = time.perf_counter()
            t0_rec  = frames[0]["t"]

            for i, frame in enumerate(frames):
                if self._stop_event.is_set():
                    break

                # --- pause hold ---
                # Wait until resumed; compensate t0_wall so timing stays correct.
                if not self._pause_event.is_set():
                    pause_started = time.perf_counter()
                    self._pause_event.wait()
                    t0_wall += time.perf_counter() - pause_started

                if self._stop_event.is_set():
                    break

                # --- timing ---
                self._current_frame_idx = i
                target_elapsed = (frame["t"] - t0_rec) / speed
                sleep_t = (t0_wall + target_elapsed) - time.perf_counter()
                if sleep_t > 0:
                    time.sleep(sleep_t)

                # --- broadcast ---
                self._client.send_message("/j_pos_playback", _joints(frame))

                # Periodic status update (~every 0.5 s at 100 Hz)
                if i % 50 == 0:
                    self._send_status()

            print("[Player] Playback complete")

        except Exception as e:
            print(f"[Player] Error: {e}")

        finally:
            self._is_playing = False
            self._is_paused  = False
            self._send_status()

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def _send_status(self):
        self._client.send_message("/playback/status", [
            int(self._is_playing),
            int(self._is_paused),
            self._current_frame_idx,
            self.frame_count,
            round(self.current_position, 3),
            round(self.duration, 2),
        ])

    def send_status(self):
        """Public — call from /playback/status OSC handler."""
        self._send_status()


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------

def _joints(frame: dict) -> list:
    return [frame["j1"], frame["j2"], frame["j3"],
            frame["j4"], frame["j5"], frame["j6"]]
