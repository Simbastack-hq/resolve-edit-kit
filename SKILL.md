---
name: resolve-edit-kit
description: Edit talking-head and screen-recording videos (YouTube, and vertical reels) end to end in DaVinci Resolve Studio 21.1+ through its AI-assistant scripting connection. Transcribe, paper edit, tighten pauses and pace, A/B take picks, build and patch timelines, HTML motion graphics, music bed, captions, thumbnails, 4K render and export QA. Use when asked to edit, cut, re-cut, tighten, add graphics, music or captions to, make a thumbnail for, or render a video in Resolve.
---

# Editing a video in DaVinci Resolve as an agent

This is a runbook plus tools. It was built while editing a series of real, published YouTube videos (raw talking
head and screen recordings to a finished 7-11 minute cut, graphics, music, captions and thumbnails, usually in a day).
Everything below is something that worked, or a mistake that cost an hour.

The tools: `scripts/` (transcribe, paper edit, tighten, join checks, music, captions, QA), `scripts/resolve/resolve_kit.py`
(build, review, patch, place graphics, stills, render inside Resolve), `motion/` (HTML motion graphics and thumbnails).

## What Resolve gives you

Resolve Studio 21.1 added File > Setup AI Assistants. It connects an assistant (Claude, Codex, and others) to
Resolve's scripting API: you get a tool that runs Python inside Resolve with `resolve` and `project` defined. Some
setups also need Preferences > System > General > External scripting using = Local. It is Studio-only.

That tool can do everything the scripting API can: media pool, timelines, items, markers, speed, properties, render.
It cannot see the screen. Look at the work with `resolve_kit.export_stills()` (Resolve's real composite), not with
screenshots of the window, which are often stale or on another desktop. Use the tool variant with filesystem access
to read your EDL and JSON files. Scripts time out around 60 seconds; long waits (renders) are polled in short calls.

## Working with the person

You are the editor; they are the talent. They record, choose, and give notes.

- **Talk in video time and quote the words:** "at 3:39, where you say 'and that's when it broke'", not "01:03:40;26".
  Many creators are new to Resolve: name the key or button (Space plays, J/K/L, up/down arrows jump between cuts,
  Shift+Z fits the timeline, Cmd+S saves).
- **Never rebuild a timeline they've watched or touched.** Duplicate their latest (`resolve_kit.duplicate`), patch
  the copy, and check every other track is unchanged. A rebuild once silently wiped a creator's own trims. Name
  versions "Rough cut v1, v2…" and keep the old ones.
- **Never delete Media Pool clips** to tidy bins. Older timelines still use them and go offline.
- **Decisions as A/B, not essays.** When there are two good takes, or a content choice, build an "A-B picks (review)"
  timeline (`resolve_kit.ab_review_timeline`: A, 1 s of black, B) and ask for a one-line answer like "1A 2B 3A".
  People invent merges ("4B+4A"); that's fine.
- **Keep write-ups short.** Decision first, then the thing to paste, then two lines of why. Long reasoning goes in a
  notes file.
- **Never silently drop something they chose.** If an element they picked hurts, fix its size or position, or show
  both versions.
- **Check their notes against the audio.** Notes come in Resolve timecode with frame numbers. A mark can sit a few
  frames inside the next word ("cut to 5:15" would have clipped "I'm"). Stop at the word and say why.
- **Fact-check, kindly.** If they say something wrong on camera (an animal fact, a price), flag it, and offer to cut
  the clause and keep the line. Keep overstatements but flag them.
- **Ask before anything external:** downloading logos, publishing, uploading. Licences for music are their call.

## One-time setup checks

- Create the project's timeline at the footage frame rate (usually 29.97) before importing.
- **Playback frame rate:** a new project defaults to 24 fps *playback* even with a 29.97 timeline, and the audio then
  sounds "crunchy, noisy, like something is wrong" while the cut is fine. The API refuses to set it. Ask the person to
  set Project Settings > Master Settings > Playback frame rate before they watch anything, then confirm with
  `project.GetSetting('timelinePlaybackFrameRate')`.
- A project created or loaded through the API can leave the Project Manager window up; every write then returns
  None. Quit Resolve, relaunch, and work in the project it opens (rename it with `project.SetName`).
- Tools: ffmpeg, Whisper (`mlx-whisper` on Apple silicon, else `openai-whisper`), Python 3 with numpy and Pillow,
  Node 18+ with `playwright-core` and a Chromium for graphics. The cut-out and roto tools use Apple Vision (macOS).

## The workflow

1. **Read what they planned, then cut what they actually said.** Recordings drift from plans. Flag missing
   must-say lines (often the payoff) early, so a pickup can be recorded the same day.
2. **Transcribe every clip** with `scripts/words_from_whisper.py` (word timings in frames, with a prompt of the
   names they say). Resolve's own transcription is fine for reading, but its word timings ran 0.2-0.4 s late and
   merged restarts, so never place cuts from it.
3. **Paper edit** as word-index ranges per section in `paper_edit.json`, then `scripts/edl_builder.py`. Prefer later
   takes (people warm up). Put runner-ups in `alts` for the A/B timeline.
   - **The hook and time to topic.** Open on the strongest line, and say what the viewer gets within 15 seconds.
     Move the introduction up if it was said late. A cold open that flashes forward to a clip from later can feel
     jarring; offer it as an A/B rather than deciding.
   - Cut restarts, asides to the crew and "um/uh", but cut fillers only in real silence. With no silence, never reach
     more than about 80 ms into a neighbouring word, or you clip it ("Handy" became "hand").
4. **Tighten** with `scripts/tighten.py`: real pauses (from the audio) over 0.35 s go to about 0.25 s. Level the pace
   per section to roughly 195-230 words per minute with small speed-ups (1.10x at most, pitch-corrected). Measure,
   don't guess: one warm-up section ran at 136-176 wpm against 225 elsewhere, and the person felt it as "really slow".
   Fix the slow stretches; don't speed the whole video. Protect sections whose graphics are timed to the speech.
5. **Check every join by ear.** `scripts/check_joins.py` plays the pieces the way Resolve will and transcribes them.
   Then transcribe the *whole cut as it plays*: on one video that caught five problems the per-join pass missed (a
   word clipped at a piece end, a stutter left when a filler between two copies of a word was removed).
   - Whisper invents connectives ("so") and doubled words at splices, and drops words at the start of a window that
     begins mid-cut. Before "fixing" a join, transcribe each side on its own and look at the audio envelope.
   - A verbatim pass with a filler prompt ("um, uh, I, I…") finds hidden restarts but also hallucinates repeats.
6. **Build** the first timeline with `resolve_kit.build_timeline` (V1/A1, sped pieces, a marker per section), and the
   A/B review timeline if there are choices. Tell the person what to watch and what to answer.
7. **Graphics** with `motion/` (see its README): overlays on tracks above the footage, full-screen scenes with the
   speaker in a picture-in-picture, all timed to the words through `tlwords.py` + `cues.py`. Place them with
   `resolve_kit.place_graphics` on a duplicate timeline, then check handoffs and collisions on `export_stills` frames.
8. **Music** with `scripts/music_bed_loop.py`: a bed at the exact length that loops the song musically (beat-tracked,
   seams in phase), silent under the hook, ending on the last frame, sitting about 20 dB under the voice. Put it on
   its own track named MUSIC. Check how the song ends first: one song ended on a 2 s fade, not a chord, and the bed
   went silent under the end card.
9. **Notes and patches** on a duplicate (see "Patching" below). Re-check the joins you touched with Whisper.
10. **Render** with `resolve_kit.start_render` + `wait_render` (H.264 4K at 40 Mbps, 24-bit PCM), then
    `scripts/limit_audio.sh` (true-peak limiter, AAC once) and `scripts/export_qa.sh` (format, loudness, full
    transcript for chapters, 9 frames). A 10-minute 4K render took about 3 minutes on an M1 Max.
11. **Captions** with `scripts/make_srt.py` from a Whisper pass on the final export, with the names in the prompt and a
    fixes file for the ones it still mishears. Upload the SRT rather than burning it in, except on Shorts and reels.
12. **Thumbnails** with `motion/thumbs/` (see its README).

## Patching a timeline after notes

Duplicate first, then patch in place, from the end of the timeline backwards so earlier record frames stay valid:

```python
import sys; sys.path.insert(0, '/path/to/resolve-edit-kit/scripts/resolve'); import resolve_kit as rk
tl = rk.duplicate(resolve, 'Rough cut v4', 'Rough cut v5'); mp = project.GetMediaPool()
music = rk.lift(tl, 'audio', 4, 0)                        # a long music bed would get a hole from a ripple
card = rk.lift(tl, 'video', 4, 1005, 'card.mov')          # overlays that span a cut aren't trimmed by a ripple
src = rk.clip_index(mp.GetRootFolder())['A001.mp4']
cut = rk.replace_and_close(tl, mp, src, 1026, [1026, 1083], [(1371, 122)], speed=1.03)   # drop a fumble
rk.place(mp, tl, card[0], [(0, 25, 987), (78, 416, 1012)], track=4)                       # same frames removed
result = rk.check_tracks(tl)
```

- Same-length swaps need no ripple: delete the V1+A1 items without ripple and append the replacement at the same
  record frame.
- To remove frames, append a filler into the leftover gap and ripple-delete it; that shifts every later item on every
  track. `replace_and_close` does this.
- Trim lifted overlays by the same frames before you put them back, in a place where the graphic is static, so its
  cues stay on their words.
- Rebuild the music bed for the new length rather than cutting it.
- Then `check_tracks` (no V1 gaps, V1 and A1 aligned), stills at every touched spot, and a Whisper pass on the joins.

## Editorial lessons from published videos

- **Real proof beats illustration.** A friend's real app, a real usage screenshot, a real screen recording of the
  tool: these were the strongest beats and the best thumbnail elements. When someone says "I'll show you on screen",
  get the screen recording.
- **Graphics: about one every 15-20 seconds was liked, wall-to-wall wasn't.** Leave stretches of just the person.
  A recurring element (a mock product that evolves through the video) makes the graphics a story.
- **Keep the outro short** (30 s or less). Retention is lowest there.
- **When the speaker talks to the agent instead of the audience** ("put that overlay here"), viewers can't tell. Shrink
  the frame and drain it to black and white for the aside, and snap back on the line that turns to the audience
  (`motion/g/aside-scene.html`). The idea came from the creator, and it worked.
- **Vertical phone clips** inside a 16:9 video: a full-screen takeover with a blurred copy filling the sides beat a
  phone-shaped card.
- **Pickups:** get audio only, build the line from the best words across 2-3 rough takes, match loudness, and cover
  it with a full-screen scene or screenshot.

## Resolve API facts

These are encoded in `resolve_kit.py`; here so you know why.

- Always pass `trackIndex` to `AppendToTimeline`; without it the audio half lands on the next free audio track. With a
  clip that has video and audio on track 1 you get one linked item back. Set audio properties (volume, fades) by
  iterating `GetItemListInTrack('audio', 1)`.
- `endFrame` is exclusive. For speed changes, append N timeline frames, then `SetSpeed(..., RippleTimeline False)`:
  without ripple, SetSpeed keeps the item's length and stretches its source range.
- `GetSourceStartFrame()` can be off by one; for 1.0x pieces `GetLeftOffset()` is the true source frame.
- `DeleteClips(items, True)` ripples every track; items on other tracks that span the cut are not trimmed.
- Resolve stills (photos) cap at 150 frames and ignore `endFrame`, and later appends overwrite them. Render photos and
  screenshots to video clips with camera moves (`scripts/kenburns.py`) and place those.
- A re-rendered file with the same name can keep showing cached frames. Render to a new name (`--suffix -v2`) and swap.
- `SetRenderSettings` fails as a whole if one key is refused, and Resolve then reuses the last settings. Check the
  return value. There's no `DeleteAllRenderJobs`; loop `GetRenderJobList()` + `DeleteRenderJob`. `StartRendering`
  takes a list of job ids. Set `VideoQuality` (kbps): the automatic setting gave about 10 Mbps at 4K.
- Resolve crashed once after hours of scripted edits. Save after every step; set preset, settings and job in
  separate calls.
- Scripts time out while Resolve is playing back. Ask the person to pause.
- `Timeline.SetVoiceIsolationState(track, {'isEnabled': True, 'amount': 70})` works from the API and removes most wind,
  but it can eat quiet words on audio the phone already gated. Check each clip's noise floor first.

## Audio

- **Leave headroom in the mix.** Phone audio can arrive at -0.5 dBFS peaks; clip gains, effects and music on top made
  Resolve's mix clip, and the person heard it at once ("the audio is crumpled"). Mix about 6 dB low, render 24-bit
  PCM, and set loudness once afterwards (`limit_audio.sh`).
- **Re-measure every export.** The same limiter setting gave -1.3 dBTP on one render and +0.4 dBTP on the next,
  because AAC overshot where the music landed differently. A lower ceiling (0.72) fixed it. alimiter needs
  `level=false`, or it adds gain.
- Find pauses on the voice-isolated audio, not the raw clip: wind hid real pauses from silence detection.
- Python's `round(172.5)` is 172 and JavaScript's `Math.round` is 173. Compute placement frames in one language.

## Screen recordings

- Record with a tool that keeps the raw capture (full screen, no baked zoom, cursor as data). Then you can re-frame
  each section later: eased 16:9 views, a redrawn cursor, a webcam bubble, highlight rings.
- Raw screen captures are often variable frame rate: a static screen writes no frames for seconds, and `ffmpeg -ss t`
  lands on the next change. Seek to the last real frame at or before t (list packet times once with ffprobe), hold it
  with `fps`, then `trim`.
- **Privacy pass, every time:** session lists, inbox and PR panels, file-browser sidebars, tab lists. Blur or frame
  them out, and check every frame sheet.
- Highlight rings drift when a chat window scrolls. Check every callout at its start and its end.
- While the screen is static (the person dictating), a full-screen scene with their webcam big and their words typed
  out beat any zoom.
- Footage for a scene must match the cut exactly, or the hand-off jumps. `ffmpeg -ss` returns the first frame with
  pts >= t, so seek to (frame - 0.25) / fps. Start and end scenes on existing cuts.

## Shooting notes to pass back

- Look into the lens (a beam-splitter teleprompter, or 3-4 word cues taped under the lens).
- Say the payoff and must-say lines on the day and tick them off.
- On a fumble, pause and restart the whole sentence: it cuts cleanly.
- Record 30 seconds of thumbnail faces at the end (laugh, point to the side, surprised), no sunglasses.
- If you say "I'll show you", record the screen. Grab phone clips of the moment as it happens.
