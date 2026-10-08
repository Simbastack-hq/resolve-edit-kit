# resolve-edit-kit

A runbook and tools for letting an AI agent (Claude, Codex, anything that can run tools) edit videos in
**DaVinci Resolve Studio 21.1+**, from raw talking-head and screen-recording footage to a finished cut with graphics,
music, captions and a 4K export.

Resolve 21.1 added **File > Setup AI Assistants**: it connects an assistant to Resolve's scripting API. That gets
you an agent that can make timelines. It doesn't, by itself, get you a good edit. This kit is the rest of it: what to
cut and how to check it, how to give the person choices instead of guessing, how to patch a timeline someone has
already watched, how to make motion graphics an agent can actually build, and the Resolve API traps that each cost
an hour to find.

It came out of editing a series of real YouTube videos this way, at [SimbaStack](https://simbastack.com/). The latest one shows the whole process on screen:
[I think I've solved procrastination](https://youtu.be/3mlRiF-LeMc), and there's a
[write-up with numbers and what broke](https://blog.simbastack.com/claude-edited-my-youtube-videos-davinci-resolve).
To be clear about what to expect: the result is a normal, decent video, not a great one. It saves a person who
doesn't want to learn an editor most of the work, and they still record, choose and give notes.

## What's in it

| Path | What it does |
|---|---|
| `SKILL.md` | The runbook the agent follows: workflow, how to work with the person, editorial lessons, Resolve API facts, audio, screen recordings. Works as a Claude Code skill. |
| `scripts/words_from_whisper.py` | Word-level transcripts in frames for every clip (Whisper, not Resolve's transcription, whose word timings run late). |
| `scripts/edl_builder.py` | Paper edit (word ranges per section, frame fixes, runner-up takes) to a frame-accurate EDL. |
| `scripts/tighten.py` | Cuts real pauses found in the audio, levels the pace per section, prints words per minute. |
| `scripts/check_joins.py` | Plays the cut the way Resolve will and transcribes it, so you can read every join. |
| `scripts/resolve/resolve_kit.py` | Runs inside Resolve: build a timeline from the EDL, an A/B review timeline, duplicate-and-patch after notes, place graphics, export Resolve's real composite as stills, render. |
| `scripts/music_bed_loop.py` | A music bed at the exact length that loops the song on its own repeat, beat-aligned, ending on the last frame. |
| `scripts/limit_audio.sh`, `scripts/export_qa.sh` | Final true-peak limit and AAC encode; QA of the exported file (format, loudness, transcript, frames). |
| `scripts/make_srt.py` | Captions from a Whisper pass on the final export. |
| `scripts/kenburns.py` | Photos and screenshots to video clips with eased camera moves. |
| `scripts/person_cutout.py` | Clean person cut-outs for thumbnails (Apple Vision, macOS). |
| `motion/` | Motion graphics as HTML/SVG pages animated by `render(t)`, rendered in headless Chromium to ProRes with alpha, timed to the spoken words. Overlays, picture-in-picture scenes, a black-and-white "aside" scene, text behind the speaker, thumbnails. |
| `examples/` | Example `paper_edit.json`, `kit.json` and A/B decisions. |

## Setup

1. DaVinci Resolve **Studio** 21.1 or later. File > Setup AI Assistants, pick your assistant, install. If the agent
   can't reach Resolve, check Preferences > System > General > External scripting using = Local.
2. ffmpeg, Python 3 with `pip install -r requirements.txt`, and Whisper (`mlx-whisper` on Apple silicon, or
   `openai-whisper`).
3. For graphics: Node 18+, then `cd motion && npm install && npx playwright install chromium`.
4. Give the agent the runbook. With Claude Code: `ln -s "$PWD" ~/.claude/skills/resolve-edit-kit`. With anything else,
   point it at `SKILL.md`.

Then, from a folder with your footage:

> The footage for my next video is in ./footage. Edit it with the resolve-edit-kit skill: tighten it, find the hook,
> give me A/B options where there are two good takes, and add motion graphics where I'm explaining something,
> but don't overdo it. Make a new Resolve project for it.

One manual step: set Project Settings > Master Settings > Playback frame rate to match the timeline before you watch
anything. New projects default to 24 fps playback, which makes a correct 29.97 cut sound crunchy, and the API can't
change that setting.

## The pipeline

```
footage -> words_from_whisper -> paper edit (edl_builder) -> tighten -> check_joins -> build_timeline (Resolve)
        -> A/B review -> notes -> duplicate + patch -> graphics (motion/) -> music bed -> render -> limit + QA -> captions
```

## Limits

- Parts are macOS-only (Apple Vision cut-outs and mattes). Everything else is plain Python, ffmpeg and Node.
- Tested with English speech, 29.97 fps footage and a 1080p timeline rendered at 4K.
- The scripts are tools for an agent, not a one-click app: the agent reads `SKILL.md` and runs them step by step.
- The graphics look (fonts, colours) is one channel's. Change the tokens in `motion/lib/base.css`.
- No logos are included. Add the ones you have the right to use (see `motion/lib/logos.js`).

## Built by SimbaStack

resolve-edit-kit is an open-source project from **[SimbaStack](https://simbastack.com/)**, an AI consulting and development studio. We build AI agents and the systems they work in: we help businesses figure out where AI actually fits in their operations, then build it, ship it and keep it working in production.

This kit is a small example of how we work: an agent doing a real job end to end, with the human making the calls, and the lessons written down so the next run is faster. If you want something like this built for your company (agents, workflows, automation that removes a real bottleneck), get in touch: **[nj@simbastack.com](mailto:nj@simbastack.com)**.

Issues and pull requests are welcome, especially Resolve API quirks we haven't hit yet.

## License

MIT. See [LICENSE](LICENSE).
