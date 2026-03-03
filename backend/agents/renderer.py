from pathlib import Path
import math
from utils.json_utils import read_json, write_json
from utils.ffmpeg_utils import run, extract_audio_wav, mux_audio_to_video

def renderer_node(state: dict) -> dict:
    job_dir = Path(state["job_dir"])
    input_video = state["input_video_path"]

    analysis = read_json(state["artifacts"]["analysis_json"])
    music_plan = read_json(state["artifacts"]["music_plan_json"])
    ducking = read_json(state["artifacts"]["ducking_json"])
    sfx_plan = read_json(state["artifacts"]["sfx_plan_json"])

    state["progress_log"].append("Renderer: preparing sources")

    # Paths
    voice_wav = job_dir / "voice.wav"
    extract_audio_wav(input_video, str(voice_wav))

    # Music file(s)
    music_index_path = Path(__file__).resolve().parents[1] / "media" / "music_library" / "index.json"
    music_index = read_json(str(music_index_path))
    music_map = {t["id"]: t["path"] for t in music_index["tracks"]}

    sfx_index_path = Path(__file__).resolve().parents[1] / "media" / "sfx_library" / "index.json"
    sfx_index = read_json(str(sfx_index_path))
    sfx_map = {s["id"]: s["path"] for s in sfx_index["sfx"]}  # { "id": "sfx/file.mp3", ... }

    # Build ffmpeg filtergraph:
    # Inputs:
    # 0: voice.wav
    # 1..N: music tracks
    # N+1..M: sfx
    #
    # Strategy:
    # - Build a single BGM track with fades/crossfade
    # - Duck BGM using sidechaincompress (voice sidechain)
    # - Place SFX using adelay, then mix all
    #
    inputs = ["ffmpeg", "-y", "-i", str(voice_wav)]

    # music inputs
    music_inputs = []
    for tr in music_plan.get("tracks", []):
        p = music_map.get(tr["id"])
        if not p:
            raise RuntimeError(f"Music track id not found in library: {tr['id']}")
        full = str((Path(__file__).resolve().parents[1] / "media" / "music_library" / p).resolve())
        inputs += ["-i", full]
        music_inputs.append(tr)

    # sfx inputs
    sfx_events = sfx_plan.get("events", [])
    valid_sfx_events = []
    for ev in sfx_events:
        sfx_id = ev.get("id") or ev.get("type", "")
        if sfx_id not in sfx_map:
            continue
        full = str((Path(__file__).resolve().parents[1] / "media" / "sfx_library" / sfx_map[sfx_id]).resolve())
        inputs += ["-i", full]
        valid_sfx_events.append(ev)
    sfx_events = valid_sfx_events

    # Filter building
    fc = []
    # Normalize voice a bit (optional)
    fc.append("[0:a]aresample=48000,volume=1.0[voice];")

    # Build BGM timeline:
    # For MVP:
    # - If 1 track: loop/trim to duration, apply global fade in/out, set gain
    # - If 2 tracks: trim to each segment, crossfade at switch
    duration = analysis["duration"]
    global_fi = float(music_plan.get("global_fade_in_s", 1.0))
    global_fo = float(music_plan.get("global_fade_out_s", 1.2))

    if len(music_inputs) == 0:
        # No music: use silence
        fc.append(f"anullsrc=r=48000:cl=mono,atrim=0:{duration}[bgm];")
        bgm_label = "bgm"
        music_start_index = 1
    elif len(music_inputs) == 1:
        tr = music_inputs[0]
        gain_db = float(tr.get("gain_db", -12.0))
        # loop to cover duration
        fc.append(
            f"[1:a]aresample=48000,aloop=loop=-1:size=2e+09,"
            f"atrim=0:{duration},"
            f"volume={db_to_lin(gain_db)},"
            f"afade=t=in:st=0:d={global_fi},"
            f"afade=t=out:st={max(0.0, duration-global_fo):.3f}:d={global_fo}"
            f"[bgm];"
        )
        bgm_label = "bgm"
        music_start_index = 1
    else:
        # Two-track crossfade
        t1 = music_inputs[0]
        t2 = music_inputs[1]
        switch_t = float(t2.get("from", duration/2))
        xfade = float(t2.get("crossfade_s", 2.2))
        gain1 = float(t1.get("gain_db", -12.0))
        gain2 = float(t2.get("gain_db", -12.0))

        # Track 1: loop, trim to switch+xfade
        fc.append(
            f"[1:a]aresample=48000,aloop=loop=-1:size=2e+09,"
            f"atrim=0:{min(duration, switch_t+xfade):.3f},"
            f"volume={db_to_lin(gain1)}[m1];"
        )
        # Track 2: loop, trim full duration, then delay to switch-xfade (so it starts before switch for xfade)
        pre_start = max(0.0, switch_t - xfade)
        fc.append(
            f"[2:a]aresample=48000,aloop=loop=-1:size=2e+09,"
            f"atrim=0:{duration:.3f},"
            f"volume={db_to_lin(gain2)},"
            f"adelay={int(pre_start*1000)}|{int(pre_start*1000)}[m2d];"
        )
        # Crossfade at switch time (approx) using acrossfade between m1 and delayed m2
        # acrossfade acts when both present; we keep it simple.
        fc.append(f"[m1][m2d]acrossfade=d={xfade}:c1=tri:c2=tri[bgm_raw];")
        # Apply global fade in/out
        fc.append(
            f"[bgm_raw]afade=t=in:st=0:d={global_fi},"
            f"afade=t=out:st={max(0.0, duration-global_fo):.3f}:d={global_fo}[bgm];"
        )
        bgm_label = "bgm"
        music_start_index = 1

    # === DUCKING: Reduce music when voice is present ===
    # Get ducking parameters
    threshold = float(ducking.get("threshold", 0.015))
    ratio = float(ducking.get("ratio", 10))
    attack = float(ducking.get("attack_ms", 50)) / 1000.0
    release = float(ducking.get("release_ms", 400)) / 1000.0

    # Sidechain compress: music ducks when voice is detected
    # threshold: voice level to trigger ducking (lower = more sensitive)
    # ratio: how much to compress (higher = more ducking)
    fc.append(
        f"[{bgm_label}][voice]sidechaincompress="
        f"threshold={threshold}:ratio={ratio}:attack={attack}:release={release}:"
        f"makeup=1:link=average[bgm_duck];"
    )

    # SFX placement
    sfx_start_index = 1 + len(music_inputs)
    sfx_labels = []
    for i, ev in enumerate(sfx_events):
        inp_idx = sfx_start_index + i
        t = float(ev.get("t", 0.0))
        gain_db = float(ev.get("gain_db", -14.0))
        delay_ms = int(max(0.0, t) * 1000)
        lbl = f"sfx{i}"
        fc.append(
            f"[{inp_idx}:a]aresample=48000,volume={db_to_lin(gain_db)},"
            f"adelay={delay_ms}|{delay_ms}[{lbl}];"
        )
        sfx_labels.append(lbl)

    # Mix voice + ducked music + sfx
    mix_inputs = "[voice][bgm_duck]" + "".join([f"[{l}]" for l in sfx_labels])
    n = 2 + len(sfx_labels)
    fc.append(f"{mix_inputs}amix=inputs={n}:normalize=0[mix];")

    # Loudness normalize to -14 LUFS (web)
    fc.append("[mix]loudnorm=I=-14:TP=-1.0:LRA=11[outa]")

    mixed_wav = job_dir / "mixed.wav"
    cmd = inputs + [
        "-filter_complex", "".join(fc),
        "-map", "[outa]",
        "-ar", "48000",
        str(mixed_wav)
    ]

    state["progress_log"].append("Renderer: mixing audio layers (FFmpeg)")
    run(cmd)

    enhanced_video = job_dir / "enhanced.mp4"
    state["progress_log"].append("Renderer: muxing audio back to video")
    mux_audio_to_video(input_video, str(mixed_wav), str(enhanced_video))

    # timeline for UI
    timeline = {
        "duration": duration,
        "speech_segments": analysis["speech_segments"],
        "music_tracks": music_plan.get("tracks", []),
        "sfx_events": sfx_events,
    }
    timeline_path = job_dir / "timeline.json"
    write_json(str(timeline_path), timeline)

    state["output_video_path"] = str(enhanced_video)
    state["artifacts"]["timeline_json"] = str(timeline_path)
    return state

def db_to_lin(db: float) -> float:
    return float(10 ** (db / 20.0))