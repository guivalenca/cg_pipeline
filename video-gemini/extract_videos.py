from __future__ import annotations

from cg_pipeline.video import extract_videos as _impl
from cg_pipeline.video.extract_videos import *  # noqa: F401,F403


def resolve_playlist_video_ref(video):
    if not is_youtube_playlist_url(video.url):
        return video
    first_url = resolve_first_playlist_video_url(video.url)
    if first_url == video.url:
        return video
    return VideoRef(
        id=video.id,
        title=video.title,
        url=first_url,
        original_url=video.original_url or video.url,
    )


resolve_first_playlist_video_url = _impl.resolve_first_playlist_video_url
