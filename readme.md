# Fairino Robot Bridge

A Python OSC bridge for the Fairino cobot. It connects to the robot over its SDK and high-speed telemetry stream, and exposes everything — motion, telemetry, recording, and playback — as OSC messages. Designed to be controlled from Chataigne, though any OSC client will work.

---

## Requirements

- Python 3.10+
- `python-osc` (`pip install python-osc`)
- Fairino SDK library in the `/fairino` folder (included in this repo)
- Robot reachable at `192.168.57.2` (configure at the top of `fairino_server.py`)

---

## How to start

```bash
python fairino_server.py
```

The server listens for OSC on port **9000** and broadcasts telemetry to **192.168.57.255:8000** (UDP broadcast, so all devices on the subnet receive it).

---

## Architecture

```
fairino_server.py   — entry point; OSC wiring, motion handlers, telemetry & polling loops
recorder.py         — PathRecorder class; buffers frames and saves to CSV
player.py           — PathPlayer class; loads CSV and replays over OSC
recordings/         — CSV files land here by default
```

The server runs three threads:
- **Main thread** — OSC server (receives commands)
- **Telemetry thread** — TCP connection to robot port 8083; parses binary packets at ~100 Hz and broadcasts joint/TCP/torque/force data over OSC
- **Polling thread** — 50 Hz SDK loop for things the stream doesn't cover (e.g. the teach pendant record button)

---

## Telemetry output

These are broadcast continuously as long as the robot is connected:

| Address | Args | Description |
|---|---|---|
| `/j_pos` | `j1 j2 j3 j4 j5 j6` | Current joint positions (degrees) |
| `/tcp_pos` | `x y z rx ry rz` | TCP pose in base frame (mm / degrees) |
| `/j_torq` | `t1 t2 t3 t4 t5 t6` | Joint torques |
| `/ft_sens` | `fx fy fz tx ty tz` | Force/torque sensor |
| `/error` | `base_err main_err sub_err` | Only sent when errors are non-zero |
| `/robot/button/record` | `bool` | Teach pendant record button state (on change only) |

---

## Motion commands

### Point-to-point

| Address | Args | Description |
|---|---|---|
| `/movej` | `j1 j2 j3 j4 j5 j6 [speed] [accel] [ovl]` | Joint-space move. Speed default 20, accel 50, ovl 100 |
| `/movel` | `x y z rx ry rz [speed] [accel] [ovl]` | Cartesian linear move |

### Jogging

| Address | Args | Description |
|---|---|---|
| `/jog` | `mode ref direction` | Start jogging |
| `/jog_stop` | — | Stop jog |

### Servo (streaming, position)

Use these for high-frequency streamed motion. Always call `/servo/start` first and `/servo/stop` when done.

| Address | Args | Description |
|---|---|---|
| `/servo/start` | — | Enter servo mode |
| `/servo/stop` | — | Exit servo mode |
| `/servoj` | `j1 j2 j3 j4 j5 j6` | Stream a joint position target |
| `/servocart` | `x y z rx ry rz` | Stream a Cartesian target (absolute, base frame) |
| `/servocart_rel` | `x y z rx ry rz` | Stream a Cartesian target (relative, tool frame) |

### Servo (streaming, torque)

| Address | Args | Description |
|---|---|---|
| `/servojt/start` | — | Enter torque servo mode (also enables drag teach) |
| `/servojt/stop` | — | Exit torque servo mode |
| `/servojt` | `t1 t2 t3 t4 t5 t6` | Stream a torque target |

### Robot state

| Address | Args | Description |
|---|---|---|
| `/enable` | `0 or 1` | Enable / disable the robot |
| `/drag` | `0 or 1` | Toggle drag-teach mode |
| `/stop` | — | Stop all motion |
| `/pause` | — | Pause motion |
| `/resume` | — | Resume paused motion |
| `/clear_error` | — | Reset all errors |
| `/telemetry/hz` | `hz` | Change telemetry broadcast rate |

---

## Recording

Records joint positions and TCP pose from the live telemetry stream into a CSV file.

### Typical workflow

1. Send `/record/start` — recording begins immediately
2. Move the robot however you like (drag teach, jogging, etc.)
3. Send `/record/stop` — a save dialog appears in Python; accept, rename, or pick an existing file to overwrite. If you cancel, the file is autosaved with a timestamped name so nothing is lost.

Alternatively, send `/record/stop "take_01"` to skip the dialog and save directly to `recordings/take_01.csv`.

### OSC commands

| Address | Args | Description |
|---|---|---|
| `/record/start` | — | Start buffering frames |
| `/record/stop` | `[filename]` | Stop and save. Opens dialog if no filename given |
| `/record/status` | — | Request a status reply |

### Status reply: `/record/status`

```
[is_recording (0/1), frame_count, duration_seconds]
```

### CSV format

```
t, j1, j2, j3, j4, j5, j6, x, y, z, rx, ry, rz
```

All values to 3 decimal places. `t` is seconds from the start of the recording. Joint values are in degrees, TCP values in mm and degrees.

---

## Playback

Loads a recorded CSV and replays it by broadcasting joint positions over OSC. **The robot does not move directly** — playback sends `/j_pos_playback` and Chataigne (or your OSC router) decides what to do with it: route to `/servoj`, send to RoboDK for visualisation, or anything else.

### Typical workflow

1. `/playback/load` — opens a file picker dialog, or pass a filename to skip it
2. Scrub through the recording with `/playback/scrub 0.5` to preview frames
3. Optionally trim: scrub to your desired in-point, then send `/playback/trim_start <value>`. Repeat for the out-point with `/playback/trim_end`. These are destructive and immediately overwrite the file.
4. `/playback/start` — plays back at original speed. Add a float argument for other speeds (e.g. `0.5` for half speed)
5. `/playback/stop` to abort, or it stops automatically at the end

### OSC commands

| Address | Args | Description |
|---|---|---|
| `/playback/load` | `[filename]` | Load a CSV. Opens dialog if no filename |
| `/playback/start` | `[speed]` | Start playback. Speed default 1.0 |
| `/playback/stop` | — | Stop playback |
| `/playback/pause` | — | Pause |
| `/playback/resume` | — | Resume from pause |
| `/playback/scrub` | `0.0–1.0` | Preview frame at position (no robot motion) |
| `/playback/trim_start` | `0.0–1.0` | **Destructive.** Remove frames before this position, re-zero timestamps, overwrite file |
| `/playback/trim_end` | `0.0–1.0` | **Destructive.** Remove frames after this position, overwrite file |
| `/playback/undo_trim` | — | Restore the file from before the last trim (one level deep) |
| `/playback/status` | — | Request a status reply |

### Playback output: `/j_pos_playback`

```
[j1, j2, j3, j4, j5, j6]   (degrees)
```

### Status reply: `/playback/status`

```
[is_playing (0/1), is_paused (0/1), current_frame, total_frames, position (0.0–1.0), duration_seconds]
```

### How playback timing works

The player uses the `t` column (seconds from recording start) to reproduce the original timing exactly. At playback start it records the current wall-clock time (`t0`). For each frame it calculates the deadline — `t0 + frame.t / speed` — and sleeps until that moment arrives, then sends the frame.

**If the player falls behind** (CPU busy, network slow): the deadline for a frame will already have passed, so `sleep_t` is negative and the sleep is skipped. The frame is sent immediately. No frames are ever dropped — they all go out — but they'll arrive in a burst. The player self-corrects automatically because each frame's deadline is calculated from `t0` independently, not from the previous frame, so there is no accumulated drift.

**If there is a gap in the recording** (e.g. a dropout in the telemetry stream, or the robot stood still and you're replaying at high speed): the `t` values in the CSV will reflect the gap. The player reproduces it faithfully — it sleeps through the gap, holding the last-sent joint position. There is no interpolation or gap-filling.

### Notes on trim

- Trim operates on the **normalised position** (same value as the scrub slider), so scrub to the exact frame you want first, then send that value as the trim argument.
- The file is backed up to `filename.bak.csv` before each trim. `/playback/undo_trim` restores it. A second trim overwrites the backup, so undo only goes back one step.
- Loading a new file clears the backup — you can't undo across files.

---

## Files

| File | Purpose |
|---|---|
| `fairino_server.py` | Main entry point. Edit `ROBOT_IP`, `OSC_LISTEN_PORT`, `OSC_SEND_IP`, `OSC_SEND_PORT` at the top to match your network |
| `recorder.py` | `PathRecorder` class and tkinter dialog helpers |
| `player.py` | `PathPlayer` class |
| `fairino/` | Fairino SDK (Python bindings for the robot RPC API) |
| `recordings/` | Default folder for saved CSV files (created automatically) |
