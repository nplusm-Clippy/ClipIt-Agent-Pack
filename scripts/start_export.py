#!/usr/bin/env python3
"""Start an export rendering job for a clip.

Usage:
  python start_export.py --clip-id <id> [--start 0] [--end 30] [--format mp4] [--wait]
"""

import argparse
import json
import sys
from clipper_client import ClipperClient, print_json, main_wrapper
from export_contract import prepare_export_start_request


def parse_json_object(value):
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must be a JSON object")
    return parsed


@main_wrapper
def main():
    parser = argparse.ArgumentParser(description="Start a ClipIt export rendering job")
    parser.add_argument("--clip-id", required=True, help="Clip ID to export")
    parser.add_argument("--project-id", help="Optional project ID")
    parser.add_argument("--sequence-id", help="Optional sequence ID")
    parser.add_argument("--start", type=float, help="Export start time in seconds")
    parser.add_argument("--end", type=float, help="Export end time in seconds")
    parser.add_argument("--format", default="mp4", choices=["mp4", "mov", "avi", "webm", "mkv"])
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        choices=["original", "16:9", "9:16", "1:1", "4:3", "4:5", "2:3"],
    )
    parser.add_argument("--reframe-mode", default="fill", choices=["fit", "fill", "custom"])
    parser.add_argument("--fit-background", choices=["black", "blur"])
    parser.add_argument("--reframe-x", type=float, help="Custom reframe x position (0-1)")
    parser.add_argument("--reframe-y", type=float, help="Custom reframe y position (0-1)")
    parser.add_argument("--hide-video", action="store_true", help="Export audio/captions without video")
    parser.add_argument("--resolution", default="1080p", choices=["2160p", "1080p", "720p", "480p", "360p", "original"])
    parser.add_argument("--bitrate", type=int, default=8000000, help="Video bitrate")
    parser.add_argument("--framerate", type=int, default=30, help="Frames per second")
    parser.add_argument("--codec", default="h264", choices=["h264", "h265", "vp9", "av1", "prores"])
    parser.add_argument(
        "--quality-preset",
        default="medium",
        choices=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
    )
    parser.add_argument("--hardware-acceleration", dest="hardware_acceleration", action="store_true", default=True)
    parser.add_argument("--no-hardware-acceleration", dest="hardware_acceleration", action="store_false")
    parser.add_argument("--color-space", default="sdr", choices=["sdr", "hdr"])
    parser.add_argument("--audio-codec", default="aac", choices=["aac", "mp3", "opus", "pcm"])
    parser.add_argument("--audio-bitrate", type=int, default=192000)
    parser.add_argument("--audio-sample-rate", type=int, default=48000)
    parser.add_argument("--include-audio", dest="include_audio", action="store_true", default=True)
    parser.add_argument("--no-audio", dest="include_audio", action="store_false")
    parser.add_argument("--audio-volume", type=float, help="Audio volume 0-100")
    parser.add_argument("--audio-muted", action="store_true", help="Mute exported audio")
    parser.add_argument("--playback-rate", type=float, help="Playback speed 0.25-4")
    parser.add_argument("--watermark-text", help="Watermark text")
    parser.add_argument("--watermark-image-url", help="Watermark image URL")
    parser.add_argument(
        "--watermark-position",
        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        default="bottom-right",
    )
    parser.add_argument("--watermark-opacity", type=float, default=0.5)
    parser.add_argument("--watermark-font-size", type=float)
    parser.add_argument("--watermark-color")
    parser.add_argument("--output-filename", help="Output file name")
    parser.add_argument("--title", help="Export metadata title")
    parser.add_argument("--description", help="Export metadata description")
    parser.add_argument("--tags", help="Comma-separated export metadata tags")
    parser.add_argument("--options-json", type=parse_json_object, help="Additional exportStart JSON fields")
    parser.add_argument(
        "--idempotency-key",
        help="Stable key to reuse only when retrying the same export after an unknown outcome",
    )
    parser.add_argument("--wait", action="store_true", help="Wait for export completion")
    parser.add_argument("--timeout", type=float, default=600, help="Max wait in seconds")
    parser.add_argument("--poll-interval", type=float, default=3, help="Poll interval in seconds")
    args = parser.parse_args()

    body = args.options_json.copy() if args.options_json else {}
    body.update(
        {
            "clipId": args.clip_id,
            "qualitySettings": {
                "resolution": args.resolution,
                "bitrate": args.bitrate,
                "framerate": args.framerate,
                "codec": args.codec,
                "qualityPreset": args.quality_preset,
                "hardwareAcceleration": args.hardware_acceleration,
                "colorSpace": args.color_space,
                "audioCodec": args.audio_codec,
                "audioBitrate": args.audio_bitrate,
                "audioSampleRate": args.audio_sample_rate,
            },
            "format": args.format,
            "aspectRatio": args.aspect_ratio,
            "reframeMode": args.reframe_mode,
            "includeAudio": args.include_audio,
        }
    )

    optional_fields = {
        "projectId": args.project_id,
        "sequenceId": args.sequence_id,
        "startTime": args.start,
        "endTime": args.end,
        "fitBackground": args.fit_background,
        "hideVideo": True if args.hide_video else None,
        "audioVolume": args.audio_volume,
        "audioMuted": True if args.audio_muted else None,
        "playbackRate": args.playback_rate,
        "outputFileName": args.output_filename,
    }
    for key, value in optional_fields.items():
        if value is not None:
            body[key] = value

    if args.reframe_x is not None or args.reframe_y is not None:
        body["reframePosition"] = {
            "x": 0.5 if args.reframe_x is None else args.reframe_x,
            "y": 0.5 if args.reframe_y is None else args.reframe_y,
        }

    if args.watermark_text or args.watermark_image_url:
        body["watermark"] = {
            "position": args.watermark_position,
            "opacity": args.watermark_opacity,
        }
        if args.watermark_text:
            body["watermark"]["text"] = args.watermark_text
        if args.watermark_image_url:
            body["watermark"]["imageUrl"] = args.watermark_image_url
        if args.watermark_font_size is not None:
            body["watermark"]["fontSize"] = args.watermark_font_size
        if args.watermark_color:
            body["watermark"]["color"] = args.watermark_color

    metadata = {}
    if args.title:
        metadata["title"] = args.title
    if args.description:
        metadata["description"] = args.description
    if args.tags:
        metadata["tags"] = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    if metadata:
        body["metadata"] = metadata

    client = ClipperClient()
    body, editor_state = prepare_export_start_request(
        client,
        args.clip_id,
        body,
        requested_idempotency_key=args.idempotency_key,
    )
    print(
        f"Export idempotency key: {body['idempotencyKey']}",
        file=sys.stderr,
    )
    response = client.post("/api/v1/exports", body)

    if args.wait and response.get("exportJobId"):
        response = client.wait_for_export(
            response["exportJobId"],
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
    print_json({
        **response,
        "clipId": args.clip_id,
        "snapshotId": editor_state["snapshotId"],
        "expectedEditorVersion": body["expectedEditorVersion"],
        "expectedEditorStateHash": body["expectedEditorStateHash"],
        "idempotencyKey": body["idempotencyKey"],
    })


if __name__ == "__main__":
    main()
