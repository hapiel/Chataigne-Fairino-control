import csv
import os
import threading
import time
from datetime import datetime
from queue import Queue

import tkinter as tk
from tkinter import filedialog


# ---------------------------------------------------------------------------
# Dialog helpers — each runs tkinter in its own thread to avoid blocking OSC
# ---------------------------------------------------------------------------

def _ask_save_path_thread(default_name: str, save_dir: str, result_queue: Queue):
    """Runs in a background thread. Puts the chosen path (or None) into result_queue."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # bring dialog to front
    path = filedialog.asksaveasfilename(
        parent=root,
        title="Save Recording",
        initialdir=os.path.abspath(save_dir),
        initialfile=default_name,
        defaultextension=".csv",
        filetypes=[("CSV recordings", "*.csv"), ("All files", "*.*")],
    )
    root.destroy()
    result_queue.put(path if path else None)


def _ask_open_path_thread(save_dir: str, result_queue: Queue):
    """Runs in a background thread. Puts the chosen path (or None) into result_queue."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        parent=root,
        title="Load Recording",
        initialdir=os.path.abspath(save_dir),
        filetypes=[("CSV recordings", "*.csv"), ("All files", "*.*")],
    )
    root.destroy()
    result_queue.put(path if path else None)


def ask_save_path(default_name: str, save_dir: str, callback):
    """
    Opens a save-as dialog in a background thread.
    Calls callback(path) when done. path is None if cancelled.
    """
    q = Queue()

    def run():
        _ask_save_path_thread(default_name, save_dir, q)
        callback(q.get())

    threading.Thread(target=run, daemon=True).start()


def ask_open_path(save_dir: str, callback):
    """
    Opens a file-open dialog in a background thread.
    Calls callback(path) when done. path is None if cancelled.
    """
    q = Queue()

    def run():
        _ask_open_path_thread(save_dir, q)
        callback(q.get())

    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------
# PathRecorder
# ---------------------------------------------------------------------------

class PathRecorder:
    """
    Records robot joint + TCP frames from the telemetry stream.

    Usage
    -----
    recorder = PathRecorder(save_dir="recordings")

    # In your telemetry loop:
    if recorder.is_recording:
        recorder.add_frame(joints, tcp_pose)

    # Via OSC:
    recorder.start()
    recorder.stop_and_save()          # opens save dialog
    recorder.stop_and_save("my_path") # saves directly to that path
    """

    def __init__(self, save_dir: str = "recordings"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

        self._frames: list[dict] = []
        self._start_time: float | None = None
        self._lock = threading.Lock()
        self.is_recording = False

    # ------------------------------------------------------------------
    # Record
    # ------------------------------------------------------------------

    def start(self):
        with self._lock:
            if self.is_recording:
                print("[Recorder] Already recording — ignoring start")
                return
            self._frames = []
            self._start_time = time.perf_counter()
            self.is_recording = True
            print("[Recorder] Recording started")

    def add_frame(self, joints: tuple | list, tcp_pose: tuple | list):
        """Call this from your telemetry loop at ~100 Hz."""
        if not self.is_recording:
            return
        t = time.perf_counter() - self._start_time
        frame = {
            "t":  t,
            "j1": joints[0], "j2": joints[1], "j3": joints[2],
            "j4": joints[3], "j5": joints[4], "j6": joints[5],
            "x":  tcp_pose[0], "y":  tcp_pose[1], "z":  tcp_pose[2],
            "rx": tcp_pose[3], "ry": tcp_pose[4], "rz": tcp_pose[5],
        }
        with self._lock:
            self._frames.append(frame)

    def stop_and_save(self, path: str | None = None):
        """
        Stop recording.
        - If path is given, save directly to that path.
        - If path is None, open a save-as dialog (non-blocking).
        """
        with self._lock:
            if not self.is_recording:
                print("[Recorder] Not recording — ignoring stop")
                return
            self.is_recording = False
            frames_snapshot = list(self._frames)

        duration = frames_snapshot[-1]["t"] if frames_snapshot else 0
        print(f"[Recorder] Stopped — {len(frames_snapshot)} frames, {duration:.2f}s")

        if path:
            self._write(frames_snapshot, path)
        else:
            default_name = _default_filename()
            ask_save_path(
                default_name=default_name,
                save_dir=self.save_dir,
                callback=lambda p: self._on_save_dialog(frames_snapshot, p, default_name),
            )

    def _on_save_dialog(self, frames: list, path: str | None, fallback_name: str):
        if path:
            self._write(frames, path)
        else:
            # Cancelled — autosave so nothing is lost
            fallback = os.path.join(self.save_dir, fallback_name)
            print(f"[Recorder] Dialog cancelled — autosaving to {fallback}")
            self._write(frames, fallback)

    def _write(self, frames: list, path: str):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            fieldnames = ["t", "j1", "j2", "j3", "j4", "j5", "j6",
                          "x", "y", "z", "rx", "ry", "rz"]
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for frame in frames:
                    writer.writerow({k: f"{v:.3f}" for k, v in frame.items()})
            print(f"[Recorder] Saved {len(frames)} frames → {path}")
        except Exception as e:
            print(f"[Recorder] Save failed: {e}")

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def frame_count(self) -> int:
        with self._lock:
            return len(self._frames)

    @property
    def duration(self) -> float:
        with self._lock:
            if not self._frames:
                return 0.0
            return self._frames[-1]["t"]


# ---------------------------------------------------------------------------
# Default filename helper
# ---------------------------------------------------------------------------

def _default_filename() -> str:
    return f"rec_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
