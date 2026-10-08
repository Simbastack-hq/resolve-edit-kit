"""Helpers for driving DaVinci Resolve Studio from an agent, through Resolve's scripting API.

Resolve 21.1's AI-assistant connection (File > Setup AI Assistants) gives the agent a tool that runs Python
inside Resolve with `resolve` and `project` already defined. Load this module there:

    import sys; sys.path.insert(0, '/path/to/resolve-edit-kit/scripts/resolve')
    import resolve_kit as rk
    result = rk.build_timeline(resolve, '/path/edl.json', '/path/footage', 'Rough cut v1')

Use the variant of the tool that allows filesystem access (it has to read the EDL). Every function returns a small
dict you can hand back as `result`. Each one saves the project at the end: Resolve can crash after hours of
scripted edits, and saving after every step is what makes that a non-event.

API facts these helpers encode (found the hard way, Resolve Studio 21.1):
- AppendToTimeline: always pass trackIndex. Without it the audio half lands on the next free audio track.
  With a clip that has video and audio and trackIndex 1, you get ONE linked item back that covers V1 and A1.
- endFrame is exclusive. A 1.0x piece [s, e] is startFrame=s, endFrame=e+1.
- Sped pieces: append N *timeline* frames, then SetSpeed with RippleTimeline False. SetSpeed without ripple keeps
  the item's length and stretches its source range, so appending the source range first leaves an overlap.
- GetSourceStartFrame() can be off by one; for 1.0x pieces GetLeftOffset() is the true source start frame.
- DeleteClips(items, True) ripples every track by the same amount. An item on another track that spans the removed
  range is not trimmed, so lift spanning overlays (and a long music bed) first and put them back afterwards.
- Never delete Media Pool clips to tidy up: older timelines still use them and go offline.
- New projects default to 24 fps *playback* even when the timeline is 29.97, which makes the audio sound crunchy.
  The API refuses to set timelinePlaybackFrameRate; the human sets it in Project Settings > Master Settings.
- A project created or loaded from the API can leave the Project Manager open, and then every write returns None.
  If that happens: quit Resolve, relaunch, and work in the project it opens.
- The project has no DeleteAllRenderJobs; loop GetRenderJobList() + DeleteRenderJob. StartRendering takes a list.
"""
import json, os, time


# ---------- lookups ----------

def project_of(resolve):
    return resolve.GetProjectManager().GetCurrentProject()


def timelines(project):
    return {project.GetTimelineByIndex(i).GetName(): project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)}


def folders(folder):
    yield folder
    for sub in folder.GetSubFolderList():
        yield from folders(sub)


def clip_index(root):
    """name -> MediaPoolItem across every bin."""
    out = {}
    for f in folders(root):
        for c in f.GetClipList():
            out.setdefault(c.GetName(), c)
    return out


def bin_named(mp, name):
    root = mp.GetRootFolder()
    return next((f for f in root.GetSubFolderList() if f.GetName() == name), None) or mp.AddSubFolder(root, name)


def import_missing(mp, bin_name, paths):
    """Import files that aren't in the Media Pool yet (by file name) into a bin. Returns name -> item for all paths."""
    have = clip_index(mp.GetRootFolder())
    missing = [p for p in paths if os.path.basename(p) not in have]
    if missing:
        mp.SetCurrentFolder(bin_named(mp, bin_name))
        for it in mp.ImportMedia(missing) or []:
            have[it.GetName()] = it
        mp.SetCurrentFolder(mp.GetRootFolder())
    return {os.path.basename(p): have[os.path.basename(p)] for p in paths}


def items_at(tl, kind, track, rec):
    """Items on a track that start at timeline frame `rec` (relative to the timeline start)."""
    st = tl.GetStartFrame()
    return [it for it in tl.GetItemListInTrack(kind, track) if it.GetStart() - st == rec]


def frames_to_tc(frame, fps=29.97, drop=True):
    """Timeline frame (absolute, i.e. including the start frame) -> timecode string for SetCurrentTimecode."""
    nominal = round(fps)
    if drop and nominal == 30:
        d, m = divmod(frame, 17982)
        frame += 18 * d + (2 * ((m - 2) // 1798) if m > 1 else 0)
    f = frame % nominal; s = frame // nominal
    sep = ';' if drop and nominal == 30 else ':'
    return f'{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}{sep}{f:02d}'


# ---------- build ----------

def append_piece(mp, item, s, e, rec, st, speed=None, track=1, media_type=None):
    """Put source frames [s, e] (inclusive) at timeline frame rec. Returns the timeline item."""
    n = round((e + 1 - s) / (speed or 1.0))
    info = {'mediaPoolItem': item, 'startFrame': s, 'endFrame': s + n, 'trackIndex': track, 'recordFrame': st + rec}
    if media_type: info['mediaType'] = media_type
    its = mp.AppendToTimeline([info])
    assert its, ('append failed', item.GetName(), s, e, rec)
    if speed and speed != 1.0:
        for it in its:
            it.SetSpeed({'Percentage': speed * 100.0, 'PitchCorrection': True, 'RippleTimeline': False})
    return its[0]


def check_tracks(tl):
    """Gaps on V1, V1/A1 misalignment and item counts: run after every build or patch."""
    st = tl.GetStartFrame()
    v1, a1 = tl.GetItemListInTrack('video', 1), tl.GetItemListInTrack('audio', 1)
    gaps = [(x.GetEnd() - st, y.GetStart() - st) for x, y in zip(v1, v1[1:]) if y.GetStart() != x.GetEnd()]
    mis = [x.GetStart() - st for x, y in zip(v1, a1) if (x.GetStart(), x.GetEnd()) != (y.GetStart(), y.GetEnd())]
    counts = {f'{k[0]}{i}': len(tl.GetItemListInTrack(k, i)) for k in ('video', 'audio') for i in range(1, tl.GetTrackCount(k) + 1)}
    return {'end': tl.GetEndFrame() - st, 'v1_gaps': gaps[:10], 'v1_a1_mismatch': mis[:10], 'counts': counts}


def build_timeline(resolve, edl_path, footage_dir, name, bin_name='Footage', markers=True):
    """First build from an EDL: V1/A1 pieces in order, sped pieces handled, a blue marker at each section start.
    Only for a NEW timeline. Once a person has watched or touched it, never rebuild: duplicate() and patch."""
    project = project_of(resolve); mp = project.GetMediaPool()
    assert name not in timelines(project), f'{name} exists: duplicate and patch instead of rebuilding'
    E = json.load(open(edl_path))
    names = sorted({p['clip'] for p in E['main'] if 'clip' in p})
    clips = import_missing(mp, bin_name, [os.path.join(footage_dir, n) for n in names])
    tl = mp.CreateEmptyTimeline(name); project.SetCurrentTimeline(tl); st = tl.GetStartFrame()
    drift, seen = [], set()
    for p in E['main']:
        if 'clip' not in p: continue
        it = append_piece(mp, clips[p['clip']], p['s'], p['e'], p['rec'], st, p.get('speed'))
        drift.append(it.GetStart() - st - p['rec'])
        if markers and p.get('label') not in seen:
            seen.add(p['label']); tl.AddMarker(p['rec'], 'Blue', p['label'], '', 1)
    tl.SetTrackName('video', 1, 'MAIN'); tl.SetTrackName('audio', 1, 'MAIN')
    resolve.GetProjectManager().SaveProject()
    return dict(check_tracks(tl), timeline=name, drift=(min(drift), max(drift)) if drift else None,
                playback_fps=project.GetSetting('timelinePlaybackFrameRate'))


def ab_review_timeline(resolve, edl_path, footage_dir, decisions, name='A-B picks (review)'):
    """Decisions, each played as A, 1 s of black, B, then 2 s before the next, with markers.
    decisions: [{"name": "1 Hook", "a": "Hook", "b": "ALT hook"}]  (labels from the EDL's main and alts)
    The person answers "1A 2B 3A" instead of reading a wall of text."""
    project = project_of(resolve); mp = project.GetMediaPool()
    E = json.load(open(edl_path)); fps = E['fps']; sec = round(fps)
    by = lambda lab: [p for p in E['main'] + E.get('alts', []) if p.get('label') == lab and 'clip' in p]
    clips = import_missing(mp, 'Footage', [os.path.join(footage_dir, n) for n in sorted({p['clip'] for p in E['main'] + E.get('alts', []) if 'clip' in p})])
    old = timelines(project).get(name)
    if old: mp.DeleteTimelines([old])                      # the review timeline is disposable; real cuts never are
    tl = mp.CreateEmptyTimeline(name); project.SetCurrentTimeline(tl); st = tl.GetStartFrame()
    pos = 0
    for d in decisions:
        for tag, lab, col in (('A', d['a'], 'Blue'), ('B', d['b'], 'Yellow')):
            tl.AddMarker(pos, col, f"{d['name']}: {tag}", lab, 1)
            for p in by(lab):
                append_piece(mp, clips[p['clip']], p['s'], p['e'], pos, st, p.get('speed'))
                pos += round((p['e'] + 1 - p['s']) / p.get('speed', 1.0))
            pos += sec
        pos += sec
    resolve.GetProjectManager().SaveProject()
    return {'timeline': name, 'decisions': len(decisions), 'length_s': round(pos / fps, 1)}


# ---------- patch a timeline someone has already watched ----------

def duplicate(resolve, src_name, new_name):
    """Copy the latest version and work on the copy. Old versions stay as they are."""
    project = project_of(resolve); tls = timelines(project)
    assert new_name not in tls, f'{new_name} exists'
    project.SetCurrentTimeline(tls[src_name])
    tl = tls[src_name].DuplicateTimeline(new_name); project.SetCurrentTimeline(tl)
    return tl


def lift(tl, kind, track, rec, name=None):
    """Remove one item (no ripple) and return what's needed to put it back: (MediaPoolItem, left offset, duration, volume)."""
    its = [it for it in items_at(tl, kind, track, rec) if name is None or it.GetName() == name]
    assert len(its) == 1, (kind, track, rec, name, len(its))
    it = its[0]; info = (it.GetMediaPoolItem(), it.GetLeftOffset(), it.GetDuration(), it.GetProperty('AudioVolume'))
    tl.DeleteClips([it], False)
    return info


def replace_and_close(tl, mp, source, rec, old_recs, pieces, speed=None):
    """Replace the V1+A1 pieces that start at old_recs with new source ranges, starting at rec, then ripple-close any
    leftover gap (a filler clip goes in the gap and is ripple-deleted, which shifts every later item on every track).
    pieces: [(source_start_frame, timeline_frames), ...]. Returns the number of frames removed.
    Lift overlays that span this range, and any long music item, BEFORE calling; work from the end of the timeline
    backwards so earlier record frames stay valid."""
    st = tl.GetStartFrame(); old_end, vol = None, None
    for r in old_recs:
        v, a = items_at(tl, 'video', 1, r), items_at(tl, 'audio', 1, r)
        assert len(v) == 1 and len(a) == 1, ('no single V1/A1 item at', r)
        old_end = v[0].GetEnd() - st; vol = a[0].GetProperty('AudioVolume'); tl.DeleteClips(v + a, False)
    r = rec
    for s0, n in pieces:
        its = mp.AppendToTimeline([{'mediaPoolItem': source, 'startFrame': s0, 'endFrame': s0 + n, 'recordFrame': r + st, 'trackIndex': 1}])
        assert its, ('append failed', s0)
        if speed and speed != 1.0:
            for it in its: it.SetSpeed({'Percentage': speed * 100.0, 'PitchCorrection': True, 'RippleTimeline': False})
        a = items_at(tl, 'audio', 1, r)
        if a and vol is not None: a[0].SetProperty('AudioVolume', vol)
        r += n
    gap = old_end - r
    if gap > 0:
        mp.AppendToTimeline([{'mediaPoolItem': source, 'startFrame': 0, 'endFrame': gap, 'recordFrame': r + st, 'trackIndex': 1}])
        tl.DeleteClips(items_at(tl, 'video', 1, r) + items_at(tl, 'audio', 1, r), True)
    return max(gap, 0)


def place(mp, tl, item, ranges, track, media_type=1):
    """Put pieces of a clip (e.g. a graphic you lifted) back: ranges = [(src_start, src_end_exclusive, rec)]."""
    st = tl.GetStartFrame()
    for s0, s1, rec in ranges:
        its = mp.AppendToTimeline([{'mediaPoolItem': item, 'startFrame': s0, 'endFrame': s1, 'recordFrame': st + rec, 'trackIndex': track, 'mediaType': media_type}])
        assert its, ('place failed', item.GetName(), s0, rec)


def place_graphics(resolve, manifest_path, timeline_name, scene_track=2, overlay_tracks=(3, 4, 5), bin_name='Motion', only=None):
    """Put rendered graphics (motion/out/manifest.json) on a timeline: opaque scenes on scene_track, overlays on the first
    overlay track that is free for their span. Skips files already on the timeline, so it is safe to re-run.
    When a graphic is re-rendered, give the file a NEW name (e.g. -v2) and replace it: Resolve can keep serving cached
    frames for a re-rendered file with the same name."""
    project = project_of(resolve); mp = project.GetMediaPool(); tl = timelines(project)[timeline_name]
    project.SetCurrentTimeline(tl); st = tl.GetStartFrame()
    man = [m for m in json.load(open(manifest_path)) if not only or m['id'] in only]
    while tl.GetTrackCount('video') < max(scene_track, *overlay_tracks): tl.AddTrack('video')
    have = import_missing(mp, bin_name, [m['file'] for m in man])
    used = {}
    for ti in [scene_track, *overlay_tracks]:
        for it in tl.GetItemListInTrack('video', ti): used.setdefault(ti, []).append((it.GetStart() - st, it.GetEnd() - st, it.GetName()))
    res = []
    for m in sorted(man, key=lambda m: m['start']):
        fn = os.path.basename(m['file'])
        if any(fn == nm for v in used.values() for _, _, nm in v): res.append((m['id'], 'already')); continue
        a, b = m['start'], m['start'] + m['n']
        tracks = [scene_track] if m['opaque'] else list(overlay_tracks)
        ti = next((t for t in tracks if all(b <= s0 or a >= e0 for s0, e0, _ in used.get(t, []))), None)
        if ti is None: res.append((m['id'], 'NO FREE TRACK')); continue
        ok = bool(mp.AppendToTimeline([{'mediaPoolItem': have[fn], 'startFrame': 0, 'endFrame': m['n'], 'trackIndex': ti, 'recordFrame': st + a, 'mediaType': 1}]))
        if ok: used.setdefault(ti, []).append((a, b, fn))
        res.append((m['id'], ti, ok))
    resolve.GetProjectManager().SaveProject()
    return {'timeline': timeline_name, 'placed': res}


# ---------- look and render ----------

def export_stills(resolve, seconds, out_dir, tag='still'):
    """Resolve's real composite (every track, grades, alpha) at timeline seconds, as PNGs. Look at these, not at a
    screenshot of the Resolve window (often stale, or on another desktop)."""
    project = project_of(resolve); tl = project.GetCurrentTimeline(); os.makedirs(out_dir, exist_ok=True)
    fps = float(tl.GetSetting('timelineFrameRate')); drop = tl.GetSetting('timelineDropFrameTimecode') == '1'
    files = []
    for s in seconds:
        tl.SetCurrentTimecode(frames_to_tc(tl.GetStartFrame() + round(s * fps), fps, drop))
        fn = os.path.join(out_dir, f'{tag}_{s:08.3f}.png'); project.ExportCurrentFrameAsStill(fn); files.append(fn)
    return {'files': files}


def start_render(resolve, timeline_name, out_dir, name, width=3840, height=2160, kbps=40000):
    """H.264 .mov with 24-bit PCM audio, whole timeline. Limit and encode the audio afterwards (limit_audio.sh).
    Set the bitrate: the automatic setting came out around 10 Mbps for 4K, which is bad for foliage."""
    project = project_of(resolve); project.SetCurrentTimeline(timelines(project)[timeline_name])
    for j in project.GetRenderJobList() or []: project.DeleteRenderJob(j['JobId'])
    project.SetCurrentRenderFormatAndCodec('mov', 'H264')
    project.SetRenderSettings({'SelectAllFrames': True, 'TargetDir': out_dir, 'CustomName': name, 'FormatWidth': width, 'FormatHeight': height, 'VideoQuality': kbps})
    project.SetRenderSettings({'ExportAudio': True, 'AudioCodec': 'lpcm', 'AudioBitDepth': 24, 'AudioSampleRate': 48000})
    job = project.AddRenderJob(); ok = project.StartRendering([job]) if job else False
    return {'job': job, 'started': ok}


def wait_render(resolve, job, max_s=55):
    """Poll for up to max_s seconds (scripts time out around 60 s; call again until it says Complete)."""
    project = project_of(resolve); t0 = time.time(); st = {}
    while time.time() - t0 < max_s:
        st = project.GetRenderJobStatus(job)
        if st.get('JobStatus') in ('Complete', 'Failed', 'Cancelled'): break
        time.sleep(3)
    return st
