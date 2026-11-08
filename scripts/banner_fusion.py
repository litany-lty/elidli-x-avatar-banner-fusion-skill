#!/usr/bin/env python3
"""Offline geometry/preview utilities for X avatar + 3:1 banner fusion.

No network or model dependency. Requires Pillow. The generated preview is never
an uploadable X banner: only the source banner is an uploadable artifact.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Dict, Tuple, Optional

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
except ImportError as exc:
    raise SystemExit('Requires Pillow. Install with: python3 -m pip install Pillow') from exc

SCHEMA = "x-avatar-banner-fusion/layout-v1"
LANCZOS = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS


def load_config(path: str) -> Dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"Invalid schema; expected {SCHEMA}")
    for key in ("banner", "avatar"):
        if key not in payload:
            raise ValueError(f"Config missing {key}")
    return payload


def validate_geometry(w: float, h: float, cx: float, cy: float, r: float) -> None:
    if min(w, h, r) <= 0 or not all(math.isfinite(x) for x in (w, h, cx, cy, r)):
        raise ValueError("Banner dimensions and avatar radius must be positive finite values")
    ratio = w / h
    if abs(ratio - 3.0) > 0.025:
        raise ValueError(f"Banner must be 3:1, got {w}x{h} ratio={ratio:.4f}")


def geometry_report(payload: Dict) -> Dict:
    bw = float(payload["banner"]["width"])
    bh = float(payload["banner"]["height"])
    cx = float(payload["avatar"]["cx"])
    cy = float(payload["avatar"]["cy"])
    r = float(payload["avatar"]["radius"])
    validate_geometry(bw, bh, cx, cy, r)
    top = cy - r
    overlap = max(0.0, min(bh, bh - top))
    chord = None
    if abs(bh - cy) < r:
        half = math.sqrt(max(0.0, r * r - (bh - cy) ** 2))
        chord = {"left_x": round(cx - half, 2), "right_x": round(cx + half, 2)}
    notes = []
    if cy <= bh:
        notes.append("Avatar center is inside the banner: verify whether this is a different UI layout")
    if top >= bh:
        notes.append("Avatar does not overlap the banner: verify screenshot geometry")
    if cx + r < 0 or cx - r > bw:
        notes.append("Avatar is completely outside the banner horizontally")
    if overlap > 0.5 * 2 * r:
        notes.append("Unusually deep avatar overlap; verify measurement and scroll state")
    if not notes:
        notes.append("Geometry is consistent with a bottom-overlapping avatar; visually verify in X")
    return {
        "schema": SCHEMA,
        "banner": {"width": round(bw, 2), "height": round(bh, 2)},
        "avatar": {"cx": round(cx, 2), "cy": round(cy, 2), "radius": round(r, 2),
                   "top_y": round(top, 2)},
        "overlap": {"height_px": round(overlap, 2),
                    "fraction_of_avatar_diameter": round(overlap / (2.0 * r), 4),
                    "chord_at_banner_bottom": chord},
        "initial_design_region": {
            "x_min": round(max(0, cx - r - 0.3 * r), 2),
            "x_max": round(min(bw, cx + r + 0.3 * r), 2),
            "y_min": round(max(0, top - 0.12 * r), 2),
            "y_max": round(bh, 2),
            "meaning": "soft glow/flow field, not a literal full circle"
        },
        "notes": notes
    }


def calculate_from_screenshot(box: Tuple[float, ...], avatar: Tuple[float, ...],
                              target: Tuple[int, int], align=(0.5, 0.5)) -> Dict:
    left, top, view_w, view_h = [float(x) for x in box]
    scx, scy, sr = [float(x) for x in avatar]
    bw, bh = map(int, target)
    if min(view_w, view_h, sr) <= 0:
        raise ValueError("Screenshot viewport and avatar radius must be positive")
    if not (0 <= align[0] <= 1 and 0 <= align[1] <= 1):
        raise ValueError("Cover alignment must be within [0,1]")
    validate_geometry(bw, bh, 1.0, bh + 20, 1.0)
    scale = max(view_w / bw, view_h / bh)   # cover (no image stretch)
    crop_x = (bw * scale - view_w) * align[0]
    crop_y = (bh * scale - view_h) * align[1]
    icx = (scx - left + crop_x) / scale
    icy = (scy - top + crop_y) / scale
    ir = sr / scale
    result = {
        "schema": SCHEMA,
        "banner": {"width": bw, "height": bh},
        "avatar": {"cx": round(icx, 5), "cy": round(icy, 5), "radius": round(ir, 5)},
        "measurement": {
            "viewport": {"left": left, "top": top, "width": view_w, "height": view_h},
            "screen_avatar": {"cx": scx, "cy": scy, "radius": sr},
            "fit": "cover", "align": [align[0], align[1]],
            "scale": round(scale, 8), "crop_offset": [round(crop_x, 5), round(crop_y, 5)],
            "source": "manual measurement from an expanded X profile screenshot"
        }
    }
    validate_geometry(bw, bh, icx, icy, ir)
    return result


def save_image(img: Image.Image, out: str) -> None:
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in (".jpeg", ".jpg"):
        img.convert("RGB").save(path, quality=94, subsampling=0, optimize=True)
    else:
        img.save(path)


def _render_avatar_on_canvas(canvas: Image.Image, source_avatar: Optional[str],
                             cx: float, cy: float, radius: float, border_px: float) -> None:
    r = max(1, int(round(radius)))
    b = max(1, int(round(border_px)))
    icx, icy = int(round(cx)), int(round(cy))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((icx - r - b, icy - r - b, icx + r + b, icy + r + b), fill=(1, 1, 1))
    size = 2 * r
    if source_avatar:
        with Image.open(source_avatar) as raw:
            avatar = ImageOps.fit(raw.convert("RGB"), (size, size), method=LANCZOS)
    else:
        avatar = Image.new("RGB", (size, size), (62, 67, 88))
        d = ImageDraw.Draw(avatar)
        for yy in range(0, size * 2, max(14, size // 14)):
            d.line((0, yy, size, yy - size), fill=(90, 98, 137), width=max(2, r // 18))
        # English label is compatible with PIL's bundled default bitmap font.
        d.text((size // 2, size // 2), "AVATAR", fill=(230, 232, 250), anchor="mm")
        d.text((size // 2, size // 2 + 18), "PREVIEW ONLY", fill=(200, 203, 220), anchor="mm")
    oversample = 4
    mask = Image.new("L", (size * oversample, size * oversample), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((1, 1, size * oversample - 2, size * oversample - 2), fill=255)
    mask = mask.resize((size, size), LANCZOS)
    canvas.paste(avatar, (icx - r, icy - r), mask)


def preview(background: str, config: Dict, outfile: str,
            source_avatar: Optional[str] = None, guide: bool = False, extra: int = 80) -> Dict:
    with Image.open(background) as raw:
        banner = raw.convert("RGB")
    w, h = banner.size
    cfg_w, cfg_h = int(config["banner"]["width"]), int(config["banner"]["height"])
    if (w, h) != (cfg_w, cfg_h):
        # The target must match the layout, avoiding silent drift from a new crop.
        raise ValueError(f"Banner is {w}x{h}, layout expects {cfg_w}x{cfg_h}; resize/layout recalibration required")
    a = config["avatar"]
    cx, cy, r = float(a["cx"]), float(a["cy"]), float(a["radius"])
    validate_geometry(w, h, cx, cy, r)
    total_h = max(h + 10, int(math.ceil(cy + r + max(0, extra))))
    canvas = Image.new("RGB", (w, total_h), (0, 0, 0))
    canvas.paste(banner, (0, 0))
    border = max(3.0, r * 0.04)
    _render_avatar_on_canvas(canvas, source_avatar, cx, cy, r, border)
    if guide:
        over = Image.new("RGBA", (w, total_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(over)
        d.line((0, h, w, h), fill=(84, 235, 225, 195), width=max(2, w // 600))
        d.ellipse((int(cx - r), int(cy - r), int(cx + r), int(cy + r)),
                  outline=(125, 230, 248, 200), width=max(2, w // 480))
        d.ellipse((int(cx - 4), int(cy - 4), int(cx + 4), int(cy + 4)), fill=(230, 254, 255, 240))
        d.text((10, min(total_h - 35, h + 12)), "PREVIEW / GUIDE ONLY - DO NOT UPLOAD", fill=(250, 240, 90, 255))
        d.text((10, min(total_h - 18, h + 32)),
               f"avatar center: ({cx:.0f}, {cy:.0f}); radius: {r:.0f}; banner bottom: {h}",
               fill=(150, 234, 230, 255))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), over).convert("RGB")
    save_image(canvas, outfile)
    return {"path": str(outfile), "size": canvas.size, "geometry": geometry_report(config)}


def grid(image_file: str, outfile: str, step: int = 100) -> Dict:
    if step <= 0:
        raise ValueError("Step must be positive")
    with Image.open(image_file) as source:
        img = source.convert("RGBA")
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=(0, 255, 255, 110), width=1)
        d.text((x + 2, 2), f"x={x}", fill=(255, 240, 50, 255))
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=(0, 255, 255, 110), width=1)
        d.text((2, y + 3), f"y={y}", fill=(255, 240, 50, 255))
    merged = Image.alpha_composite(img, overlay).convert("RGB")
    save_image(merged, outfile)
    return {"path": str(outfile), "size": merged.size, "step": step}


def screenshot_preview(banner_path: str, screenshot_path: str,
                       viewport: Tuple[int, ...], avatar_geom: Tuple[float, ...],
                       outfile: str, keep_boxes=(), keep_circles=()) -> Dict:
    left, top, vw, vh = map(int, viewport)
    acx, acy, ar = avatar_geom
    if min(vw, vh, ar) <= 0:
        raise ValueError("Viewport and avatar radius must be positive")
    with Image.open(banner_path) as b_im, Image.open(screenshot_path) as s_im:
        banner, screen = b_im.convert("RGB"), s_im.convert("RGB")
    sw, sh = screen.size
    if left < 0 or top < 0 or left + vw > sw or top + vh > sh:
        raise ValueError("Banner viewport must be inside screenshot bounds")
    canvas = screen.copy()
    resized = ImageOps.fit(banner, (vw, vh), method=LANCZOS, centering=(0.5, 0.5))
    canvas.paste(resized, (left, top))
    # Put back exactly the REAL screenshot avatar, including immutable black edge.
    # The rest of the profile (below the banner) was never changed.
    mask = Image.new("L", screen.size, 0)
    md = ImageDraw.Draw(mask)
    pad = max(2, int(ar * 0.055))
    md.ellipse((acx - ar - pad, acy - ar - pad, acx + ar + pad, acy + ar + pad), fill=255)
    for rect in keep_boxes:
        md.rectangle(tuple(rect), fill=255)
    for circ in keep_circles:
        x, y, rad = circ
        md.ellipse((x-rad, y-rad, x+rad, y+rad), fill=255)
    canvas.paste(screen, (0, 0), mask)
    save_image(canvas, outfile)
    return {"path": str(outfile), "size": canvas.size,
            "note": "Compositing preview. UI overlays are only retained if explicitly marked using --keep-box/--keep-circle; actual X screenshot is authoritative."}


def shift_image(image_path: str, outfile: str, dx: int, dy: int) -> Dict:
    with Image.open(image_path) as raw:
        original = raw.convert("RGB")
    w, h = original.size
    if abs(dx) > int(w * 0.3) or abs(dy) > int(h * 0.3):
        raise ValueError("Shift exceeds 30% of width/height; regenerate instead of clipping important content")
    # Edge-extension avoids obvious solid-black fill lines; translation clips image.
    edge = original.getpixel((0, 0))
    canvas = Image.new("RGB", original.size, edge)
    if dy > 0:
        line = original.crop((0, 0, w, 1)).resize((w, dy))
        canvas.paste(line, (0, 0))
    elif dy < 0:
        line = original.crop((0, h - 1, w, h)).resize((w, -dy))
        canvas.paste(line, (0, h + dy))
    if dx > 0:
        line = original.crop((0, 0, 1, h)).resize((dx, h))
        canvas.paste(line, (0, 0))
    elif dx < 0:
        line = original.crop((w - 1, 0, w, h)).resize((-dx, h))
        canvas.paste(line, (w + dx, 0))
    canvas.paste(original, (dx, dy))
    save_image(canvas, outfile)
    return {"path": str(outfile), "size": canvas.size, "dx": dx, "dy": dy,
            "note": "Pure translation with edge extension and cropping, not content-aware regeneration"}


def cli() -> None:
    ap = argparse.ArgumentParser(description="X/Twitter avatar-banner alignment tools (offline)")
    sub = ap.add_subparsers(dest="command", required=True)
    m = sub.add_parser("measure", help="Convert screenshot avatar geometry into 3:1 source banner coordinates")
    m.add_argument("--banner-box", type=float, nargs=4, required=True,
                   metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"))
    m.add_argument("--avatar", type=float, nargs=3, required=True, metavar=("CX", "CY", "R"))
    m.add_argument("--target", type=int, nargs=2, default=[1536, 512], metavar=("W", "H"))
    m.add_argument("--align", type=float, nargs=2, default=[0.5, 0.5], metavar=("X", "Y"))
    m.add_argument("--out", required=True)
    r = sub.add_parser("report", help="Print geometry, overlap, and suggested arc design area as JSON")
    r.add_argument("--config", required=True)
    p = sub.add_parser("preview", help="Preview final banner with an independent overlaid avatar")
    p.add_argument("--banner", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--avatar-image", help="Square avatar, optional; never added to output banner")
    p.add_argument("--guide", action="store_true", help="Overlay calibration markings; preview is not uploadable")
    p.add_argument("--out", required=True)
    g = sub.add_parser("grid", help="Overlay pixel grid on a screenshot for manual measurement")
    g.add_argument("--image", required=True)
    g.add_argument("--step", type=int, default=100)
    g.add_argument("--out", required=True)
    s = sub.add_parser("shift", help="Translate existing banner artwork (down: positive dy)")
    s.add_argument("--input", required=True)
    s.add_argument("--dx", type=int, default=0)
    s.add_argument("--dy", type=int, default=0)
    s.add_argument("--out", required=True)
    z = sub.add_parser("screenshot-preview", help="Replace banner region in an old screenshot, preserve actual avatar")
    z.add_argument("--banner", required=True)
    z.add_argument("--screenshot", required=True)
    z.add_argument("--banner-box", type=int, nargs=4, required=True,
                   metavar=("LEFT", "TOP", "WIDTH", "HEIGHT"))
    z.add_argument("--avatar", type=float, nargs=3, required=True, metavar=("CX", "CY", "R"))
    z.add_argument("--keep-box", type=int, nargs=4, action="append", default=[],
                   metavar=("X0", "Y0", "X1", "Y1"), help="Restore a screenshot UI rectangle")
    z.add_argument("--keep-circle", type=float, nargs=3, action="append", default=[],
                   metavar=("CX", "CY", "R"), help="Restore a screenshot UI circle/button")
    z.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        if args.command == "measure":
            data = calculate_from_screenshot(args.banner_box, args.avatar, args.target, args.align)
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            result = {"saved_config": args.out, "report": geometry_report(data)}
        elif args.command == "report":
            result = geometry_report(load_config(args.config))
        elif args.command == "preview":
            result = preview(args.banner, load_config(args.config), args.out,
                             source_avatar=args.avatar_image, guide=args.guide)
        elif args.command == "grid":
            result = grid(args.image, args.out, args.step)
        elif args.command == "screenshot-preview":
            result = screenshot_preview(args.banner, args.screenshot, args.banner_box,
                                        args.avatar, args.out, args.keep_box, args.keep_circle)
        elif args.command == "shift":
            result = shift_image(args.input, args.out, args.dx, args.dy)
        else:
            raise AssertionError(args.command)
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
