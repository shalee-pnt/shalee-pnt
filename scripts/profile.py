#!/usr/bin/env python3
"""Generates the shalee-pnt GitHub profile.

Trainer card, party, projects dial, 3D activity calendar, Lumiose skyline, wild-bug encounter
and status line, with the standard library only.

    python scripts/profile.py update            hourly: status line, full refresh once per day
    python scripts/profile.py update --force    full refresh now
    python scripts/profile.py encounter         issue handler (env: ISSUE_NUMBER, ISSUE_AUTHOR)

GitHub blocks external resources inside SVG images: fonts are system fonts, animations are
SMIL, and logos / artwork from data/vendor are embedded as data URIs.
"""
from __future__ import annotations

import base64
import datetime as dt
import functools
import json
import math
import os
import random
import re
import sys
import textwrap
import urllib.request
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
VENDOR = ROOT / "data" / "vendor"
STATE_FILE = ROOT / "data" / "state.json"
README = ROOT / "README.md"
LOGIN = "shalee-pnt"
REPO = f"{LOGIN}/{LOGIN}"
TZ = ZoneInfo("Europe/Paris")

SANS = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace"

# X (blue) in dark mode, Y (red) in light mode. Flat colours, no gradients on the cards.
THEMES = {
    "dark": dict(
        bg="#0c1431", panel="#111c3d", panel2="#16244a", line="#25375f", dots="#1d2c54",
        text="#e8eefb", muted="#8ea3c9", primary="#3fa9f5", secondary="#5fd4f5",
        locked="#1b2750", lockedtxt="#4f5f86", sky1="#0b1530", sky2="#15305c",
        grass1="#1d5a52", grass2="#123d3a", outline="#0a0f1f",
        levels=["#17234a", "#1b4a86", "#2672c4", "#3fa9f5", "#9be7ff"],
    ),
    "light": dict(
        bg="#fffafb", panel="#ffffff", panel2="#fff1f4", line="#f0c4ce", dots="#f6dbe1",
        text="#25161c", muted="#8a6470", primary="#d7263d", secondary="#e0457b",
        locked="#f5e4e8", lockedtxt="#c9a7b0", sky1="#fff3f5", sky2="#ffdbe3",
        grass1="#bfe3b0", grass2="#93cc85", outline="#3a2a1a",
        levels=["#f4e3e7", "#f5adbb", "#ea6a82", "#d7263d", "#93112a"],
    ),
}

# Lumiose skyline: neon-blue night for X, dusk with amber windows for Y.
CITY = {
    "dark": dict(
        title="LUMIOSE CITY · BY NIGHT", far="#0f1a3b", bld="#1d2d5a", win="#25386a",
        lit=["#3fa9f5", "#3fa9f5", "#5fd4f5", "#9be7ff"], tower="#1f3062", lattice="#30477f",
        prism="#9be7ff", glow="#3fa9f5", spark="#eaf9ff", star="#c9d6f2", moon="#e8eefb",
        sun=None, beacon="#ff4d5e",
    ),
    "light": dict(
        title="LUMIOSE CITY · AT DUSK", far="#f8dfe5", bld="#4a2c3a", win="#5a3747",
        lit=["#ffcf6e", "#ffcf6e", "#ffe3a3", "#ff8a9a"], tower="#3a2230", lattice="#5a3a4c",
        prism="#ff5a70", glow="#d7263d", spark="#fff1c9", star=None, moon=None,
        sun=("#ffd0d8", "#ffb3c1"), beacon="#d7263d",
    ),
}

TYPE_COLORS = {
    "Normal": "#a8a878", "Electric": "#e8b923", "Steel": "#8aa5b8", "Ground": "#d4a845",
    "Water": "#5b8def", "Psychic": "#f05a8c", "Ghost": "#7c6cf0", "Rock": "#b8a038",
    "Flying": "#8f7ae8", "Poison": "#a24bb5", "Dragon": "#6a3ff0", "Fighting": "#d0402f",
}

PARTY = [
    # name, logo (data/vendor), type, signature move (from real projects)
    ("Python", "python.svg", "Normal", "Full-Text Search"),
    ("JavaScript", "javascript.svg", "Psychic", "Guess of the Day"),
    ("Flask", "flask.svg", "Steel", "Waitress Serve"),
    ("MariaDB / MySQL", "mariadb.svg", "Ground", "Stored Procedure"),
    ("C++ / ESP32", "cplusplus.svg", "Electric", "Anti-Cheat Check"),
    ("Docker", "docker.svg", "Water", "Compose Up"),
]

PROJECTS = [
    # project, tags, description, stack
    ("Metacatalogue", "work · private",
     "Reads an entire file server so nobody else has to. Full-text search, Active Directory sign-in, "
     "AI summaries from a local LLM.",
     ["Python", "Flask", "MariaDB", "Whoosh", "Ollama"]),
    ("Document audit tool", "work · private",
     "Scans document trees in read-only mode and grades the mess out of 100. Duplicates are found by "
     "hash, not by name.",
     ["Python", "XML", "JSON", "CSV"]),
    ("Scubanion", "team of 4 · public",
     "A Tamagotchi that grows when you walk outside. I wrote the NFC kiosk firmware and its anti-cheat.",
     ["C++", "ESP32", "MQTT", "Laravel", "Vue"]),
    ("AllRoads", "team · private",
     "Urban mobility app for the Nice area: buses, bikes, real-time routes. I built tables, stored "
     "procedures and the sign-up screen.",
     ["TypeScript", "Node.js", "MySQL", "Docker"]),
    ("Langdle", "personal · private",
     "Guess the programming language of the day. Like a daily word game, but for people who have "
     "opinions about semicolons.",
     ["JavaScript", "Node.js", "CSS"]),
    ("PastaBox Randomizer", "personal · private",
     "Reduces the mental load of picking a PastaBox every day. Comes with a cooking timer. Useless, "
     "but deeply satisfying.",
     ["JavaScript", "LocalStorage"]),
]

SPECIES = [
    # id, name, type, catch rate, Bugdex entry
    ("undefinedeon", "Undefinedeon", "Ghost", 0.45, "Its type is unknown. So is its value."),
    ("off-by-onyx", "Off-by-Onyx", "Rock", 0.55,
     "Always has one segment too many. Or one too few. Nobody has ever counted it right."),
    ("segfaultoise", "Segfaultoise", "Steel", 0.35,
     "Touches memory it doesn't own, then retreats into its shell and takes the whole process with it."),
    ("racecondor", "Racecondor", "Flying", 0.30,
     "Two of them hatched at the same time. Which one came first depends on the weather."),
    ("heisenbuzz", "Heisenbuzz", "Psychic", 0.20,
     "Vanishes the moment you open the debugger. Reappears in production."),
    ("memleech", "Memleech", "Poison", 0.40,
     "Gets a little bigger every hour and never lets go. Restarting only makes it hungrier."),
    ("infiniloop", "Infiniloop", "Dragon", 0.25,
     "Has been chasing its own tail since the first commit. CPU usage: 100%."),
    ("conflictwin", "Conflictwin", "Fighting", 0.50,
     "Two heads, both convinced they are right. Only a human can settle it."),
]
SPECIES_BY_ID = {s[0]: s for s in SPECIES}

NATURES = [
    ("Lax", "+Naps", "-Meetings"), ("Calm", "+Code review", "-Hotfixes"),
    ("Careful", "+Tests", "-Deadlines"), ("Jolly", "+Commits", "-Docs"),
    ("Modest", "+Docs", "-Commits"), ("Quiet", "+Focus", "-Notifications"),
    ("Hasty", "+Shipping", "-Tests"), ("Relaxed", "+Coffee breaks", "-Sprints"),
    ("Timid", "+Read-only mode", "-Force push"), ("Serious", "+Prod access", "-Jokes"),
    ("Sassy", "+Commit messages", "-Diplomacy"), ("Quirky", "+Side projects", "-Focus"),
    ("Gentle", "+Pair programming", "-Blame"), ("Bold", "+Refactors", "-Backups"),
]

BADGES = [
    # label, glyph, condition on stats
    ("REPO", "R", lambda s: s["repos"] >= 1),
    ("MERGE", "M", lambda s: s["merged_prs"] >= 1),
    ("TEAM", "T", lambda s: s["orgs"] >= 1),
    ("100", "100", lambda s: s["contributions"] >= 100),
    ("STAR", "★", lambda s: s["stars"] >= 1),
    ("1 YEAR", "1Y", lambda s: s["days"] >= 365),
    ("500", "500", lambda s: s["contributions"] >= 500),
    ("1K", "1K", lambda s: s["contributions"] >= 1000),
]

WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# --------------------------------------------------------------------------- helpers

def esc(s) -> str:
    return escape(str(s), {'"': "&quot;"})


def now_paris() -> dt.datetime:
    return dt.datetime.now(TZ)


@functools.lru_cache(maxsize=None)
def data_uri(name: str) -> str:
    path = VENDOR / name
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def shade(color: str, factor: float) -> str:
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, round(c * factor))) for c in (r, g, b)))


def hexagon(cx, cy, r) -> str:
    return " ".join(f"{cx + r * math.cos(math.radians(a)):.1f},{cy + r * math.sin(math.radians(a)):.1f}"
                    for a in range(-90, 270, 60))


def pill(x, y, text, color, size=11, fg="#ffffff", h=20, stroke=None) -> tuple[str, float]:
    w = len(text) * size * 0.62 + 18
    st = f' stroke="{stroke}"' if stroke else ""
    svg = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{color}"{st}/>'
           f'<text x="{x + w / 2:.1f}" y="{y + h / 2 + size * 0.36:.1f}" text-anchor="middle" '
           f'class="b" font-size="{size}" fill="{fg}" letter-spacing=".6">{esc(text)}</text>')
    return svg, w


def frame(w, h, t, dotted=True) -> str:
    fill = "url(#dots)" if dotted else t["bg"]
    out = f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="24" fill="{t["bg"]}"/>'
    if dotted:
        out += f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="24" fill="{fill}"/>'
    return out + f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="24" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>'


def svg_doc(w, h, title, desc, body, t) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="title desc">
<title id="title">{esc(title)}</title>
<desc id="desc">{esc(desc)}</desc>
<style>
text{{font-family:{SANS}}}
.m{{font-family:{MONO}}}
.b{{font-weight:700}}
.mu{{fill:{t["muted"]}}}
.lb{{font-size:11px;letter-spacing:2.4px;font-weight:600;fill:{t["muted"]}}}
</style>
<defs>
<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="9" cy="9" r="1.1" fill="{t["dots"]}"/></pattern>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>
<clipPath id="frame"><rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="24"/></clipPath>
</defs>
<g fill="{t["text"]}">
{body}
</g>
</svg>
'''


def bob(dy=4, dur=3.2, begin=0.0) -> str:
    return (f'<animateTransform attributeName="transform" type="translate" additive="sum" '
            f'values="0 0;0 {-dy};0 0" dur="{dur}s" begin="{begin}s" repeatCount="indefinite" '
            f'calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>')


# --------------------------------------------------------------------------- trainer card

def render_card(t, stats, daily) -> str:
    W, H = 880, 420
    nature = NATURES[daily["nature"]]
    b = [frame(W, H, t)]
    b.append(f'<text x="40" y="48" class="lb">TRAINER CARD</text>')
    b.append(f'<text x="{W - 40}" y="48" class="lb m" text-anchor="end">ID No. {stats["trainer_id"]}</text>')
    b.append(f'<text x="40" y="106" class="b" font-size="44" letter-spacing="-.5">shalee-pnt</text>')
    b.append(f'<rect x="40" y="120" width="64" height="4" rx="2" fill="{t["primary"]}"/>')
    b.append(f'<text x="40" y="150" font-size="15" class="mu">Normal-type developer · BUT 3 Computer Science, work-study</text>')
    cells = [
        ("SPECIALTY", "Normal type"), ("EMPLOYER", "City hall"),
        ("PLAY TIME", f'{stats["days"]} days'), ("CONTRIBUTIONS", f'{stats["contributions"]} / year'),
        ("MERGED PRs", str(stats["merged_prs"])), ("TEAMS", f'{stats["orgs"]} orgs · {stats["repos"]} repos'),
    ]
    for i, (label, value) in enumerate(cells):
        cx = 40 + (i % 2) * 250
        cy = 186 + (i // 2) * 50
        b.append(f'<text x="{cx}" y="{cy}" class="lb">{esc(label)}</text>')
        b.append(f'<text x="{cx}" y="{cy + 23}" class="b" font-size="19">{esc(value)}</text>')
        b.append(f'<line x1="{cx}" y1="{cy + 33}" x2="{cx + 220}" y2="{cy + 33}" stroke="{t["line"]}" stroke-dasharray="2 4"/>')
    earned = [cond(stats) for _, _, cond in BADGES]
    b.append(f'<text x="40" y="344" class="lb">BADGES  {sum(earned)}/{len(BADGES)}</text>')
    for i, ((label, glyph, _), ok) in enumerate(zip(BADGES, earned)):
        cx, cy, r = 61 + i * 58, 376, 19
        fs = 12 if len(glyph) < 3 else 10
        if ok:
            b.append(f'<polygon points="{hexagon(cx, cy, r)}" fill="{t["primary"]}"/>')
            b.append(f'<polygon points="{hexagon(cx, cy, r - 4)}" fill="none" stroke="#ffffff" stroke-opacity=".35"/>')
            b.append(f'<text x="{cx}" y="{cy + fs * .36:.1f}" text-anchor="middle" class="b" font-size="{fs}" fill="#ffffff">{esc(glyph)}</text>')
        else:
            b.append(f'<polygon points="{hexagon(cx, cy, r)}" fill="{t["locked"]}" stroke="{t["line"]}" stroke-dasharray="3 3"/>')
            b.append(f'<text x="{cx}" y="{cy + 4.5}" text-anchor="middle" class="b" font-size="13" fill="{t["lockedtxt"]}">?</text>')
        b.append(f'<text x="{cx}" y="{cy + r + 15}" text-anchor="middle" font-size="8.5" letter-spacing="1" '
                 f'class="b" fill="{t["muted"] if ok else t["lockedtxt"]}">{esc(label)}</text>')
    # partner panel
    px, py, pw, ph = 572, 72, 276, 322
    b.append(f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="18" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    b.append(f'<ellipse cx="{px + pw / 2}" cy="{py + 238}" rx="92" ry="12" fill="{t["primary"]}" opacity=".16" filter="url(#soft)"/>')
    b.append(f'<text x="{px + 20}" y="{py + 30}" class="lb">PARTNER</text>')
    ps, pwid = pill(0, 0, f"{nature[0].upper()} NATURE", t["primary"], size=9.5, h=18)
    b.append(f'<g transform="translate({px + pw - 20 - pwid:.1f} {py + 16})">{ps}</g>')
    iw, ih = 176, 200
    b.append(f'<g><image href="{data_uri("dunsparce.png")}" x="{px + (pw - iw) / 2:.1f}" y="{py + 42}" width="{iw}" height="{ih}"/>{bob(4, 3.6)}</g>')
    for k, (zx, zy, fs) in enumerate([(px + 44, py + 196, 12), (px + 34, py + 178, 15), (px + 26, py + 156, 18)]):
        b.append(f'<text x="{zx}" y="{zy}" class="b" font-size="{fs}" fill="{t["secondary"]}" opacity="0">z'
                 f'<animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="{k * .6}s" repeatCount="indefinite"/></text>')
    b.append(f'<text x="{px + 20}" y="{py + 268}" class="b" font-size="20">Dunsparce</text>')
    b.append(f'<text x="{px + 20}" y="{py + 288}" font-size="12.5" class="mu">Insolourdo in French · Normal type</text>')
    b.append(f'<text x="{px + 20}" y="{py + 308}" font-size="11.5" class="m mu">today: {esc(nature[1])}  {esc(nature[2])}</text>')
    desc = (f"Trainer card for shalee-pnt: Normal-type developer, work-study at a city hall. "
            f"{stats['contributions']} contributions this year, {stats['merged_prs']} merged pull requests, "
            f"{sum(earned)} of {len(BADGES)} badges. Partner: Dunsparce.")
    return svg_doc(W, H, "Trainer card · shalee-pnt", desc, "\n".join(b), t)


# --------------------------------------------------------------------------- party

def render_party(t, daily) -> str:
    W, H = 880, 390
    b = []
    for i, (name, logo, typ, move) in enumerate(PARTY):
        lvl, hp = daily["party"][i]
        x = 20 + (i % 2) * 428
        y = 16 + (i // 2) * 116
        w = 412
        col = TYPE_COLORS[typ]
        b.append(f'<g>{bob(1.5, 3 + i * .37, i * .4)}')
        b.append(f'<rect x="{x}" y="{y}" width="{w}" height="100" rx="18" fill="{t["panel"]}" stroke="{t["line"]}"/>')
        b.append(f'<rect x="{x}" y="{y + 18}" width="4" height="64" rx="2" fill="{col}"/>')
        b.append(f'<circle cx="{x + 52}" cy="{y + 50}" r="31" fill="#ffffff" stroke="{col}" stroke-width="3"/>')
        b.append(f'<image href="{data_uri(logo)}" x="{x + 33}" y="{y + 31}" width="38" height="38"/>')
        b.append(f'<text x="{x + 98}" y="{y + 36}" class="b" font-size="18">{esc(name)}</text>')
        b.append(f'<text x="{x + w - 18}" y="{y + 36}" text-anchor="end" class="b m" font-size="15"><tspan class="mu" font-size="11">Lv.</tspan> {lvl}</text>')
        ps, pw = pill(x + 98, y + 46, typ.upper(), col, size=9.5, h=18)
        b.append(ps)
        b.append(f'<text x="{x + 98 + pw + 10:.1f}" y="{y + 59}" font-size="12.5" class="mu">{esc(move)}</text>')
        bx, bw = x + 124, w - 124 - 18
        hpcol = "#4ade80" if hp > 50 else "#facc15" if hp > 20 else "#f87171"
        b.append(f'<text x="{x + 98}" y="{y + 85}" class="b m" font-size="10" fill="{t["primary"]}">HP</text>')
        b.append(f'<rect x="{bx}" y="{y + 77}" width="{bw}" height="9" rx="4.5" fill="{t["locked"]}"/>')
        b.append(f'<rect x="{bx}" y="{y + 77}" width="{bw * hp / 100:.1f}" height="9" rx="4.5" fill="{hpcol}">'
                 f'<animate attributeName="width" from="0" to="{bw * hp / 100:.1f}" dur="1.4s" fill="freeze" '
                 f'calcMode="spline" keySplines=".2 .8 .2 1" keyTimes="0;1"/></rect>')
        b.append('</g>')
    b.append(f'<text x="{W / 2}" y="{H - 14}" text-anchor="middle" font-size="12" class="mu">'
             f'Levels recalibrated daily · {daily["date"]} · metrics: super real™</text>')
    desc = "Tech stack shown as a party of six: " + ", ".join(
        f"{p[0]} ({p[2]} type, level {daily['party'][i][0]})" for i, p in enumerate(PARTY)) + "."
    return svg_doc(W, H, "Party · shalee-pnt", desc, "\n".join(b), t)


# --------------------------------------------------------------------------- projects

def render_projects(t) -> str:
    W, H, n, dur, e = 880, 300, len(PROJECTS), 30, 0.012
    green = "#39ff88"
    b = [frame(W, H, t)]

    def fade(i) -> str:
        a, z = i / n, (i + 1) / n
        if i == 0:
            vals, keys = "1;1;0;0;1", f"0;{z - e:.4f};{z:.4f};{1 - e:.4f};1"
        elif i == n - 1:
            vals, keys = "0;0;1;1;0", f"0;{a - e:.4f};{a:.4f};{1 - e:.4f};1"
        else:
            vals, keys = "0;0;1;1;0;0", f"0;{a - e:.4f};{a:.4f};{z - e:.4f};{z:.4f};1"
        return f'<animate attributeName="opacity" values="{vals}" keyTimes="{keys}" dur="{dur}s" repeatCount="indefinite"/>'

    cx, cy = 160, 150
    rot_vals, rot_keys = [], []
    for i in range(n):
        rot_vals += [i * 60, i * 60]
        rot_keys += [i / n, (i + 1) / n - e]
    rot_vals.append(360)
    rot_keys.append(1)
    b.append(f'<circle cx="{cx}" cy="{cy}" r="122" fill="{green}" opacity=".10" filter="url(#soft)"/>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="116" fill="#1a1f24" stroke="#3a434c" stroke-width="3"/>')
    ticks = "".join(
        f'<rect x="{cx - 3}" y="{cy - 112}" width="6" height="16" rx="2" fill="{"#5c6670" if k % 2 else green}" '
        f'transform="rotate({k * 30} {cx} {cy})"/>' for k in range(12))
    b.append(f'<g>{ticks}<animateTransform attributeName="transform" type="rotate" '
             f'values="{";".join(f"{v} {cx} {cy}" for v in rot_vals)}" keyTimes="{";".join(f"{k:.4f}" for k in rot_keys)}" '
             f'dur="{dur}s" repeatCount="indefinite"/></g>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="88" fill="#0b100d" stroke="#2c343b" stroke-width="4"/>')
    b.append(f'<path d="M {cx - 60} {cy - 62} L {cx + 60} {cy - 62} L {cx + 10} {cy} L {cx + 60} {cy + 62} L {cx - 60} {cy + 62} L {cx - 10} {cy} Z" '
             f'fill="{green}" opacity=".92"><animate attributeName="opacity" values=".92;.65;.92" dur="2.4s" repeatCount="indefinite"/></path>')
    b.append(f'<circle cx="{cx}" cy="{cy}" r="34" fill="#0b100d" stroke="{green}" stroke-width="2"/>')
    for i in range(n):
        b.append(f'<g opacity="{1 if i == 0 else 0}">{fade(i)}'
                 f'<text x="{cx}" y="{cy + 8}" text-anchor="middle" class="b m" font-size="22" fill="{green}">{i + 1:02d}</text></g>')
    for i, (project, tags, desc, stack) in enumerate(PROJECTS):
        x0 = 320
        g = [f'<g opacity="{1 if i == 0 else 0}">{fade(i)}']
        g.append(f'<text x="{x0}" y="62" class="lb">PROJECT {i + 1:02d}/{n:02d}</text>')
        g.append(f'<text x="{x0}" y="108" class="b" font-size="38" letter-spacing="-.5">{esc(project)}</text>')
        g.append(f'<rect x="{x0}" y="120" width="56" height="4" rx="2" fill="{t["primary"]}"/>')
        g.append(f'<text x="{x0}" y="150" class="mu" font-size="13.5">{esc(tags)}</text>')
        for k, line in enumerate(textwrap.wrap(desc, 68)[:3]):
            g.append(f'<text x="{x0}" y="{178 + k * 21}" font-size="14.5" class="mu">{esc(line)}</text>')
        px = x0
        for s in stack:
            ps, pw = pill(px, 238, s, t["panel2"], size=11, fg=t["text"], h=22, stroke=t["line"])
            g.append(ps)
            px += pw + 8
        g.append('</g>')
        b.append("".join(g))
    desc = "Featured projects: " + "; ".join(f"{p[0]} ({p[1]})" for p in PROJECTS) + "."
    return svg_doc(W, H, "Projects of shalee-pnt", desc, "\n".join(b), t)


# --------------------------------------------------------------------------- 3D activity calendar

def activity_stats(weeks) -> dict:
    days = [d for wk in weeks for d in wk]
    best = max(days, key=lambda d: d[1])
    longest = run = 0
    for _, c, _ in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    seq = [c for _, c, _ in days]
    if seq and seq[-1] == 0:  # today isn't over yet
        seq.pop()
    current = 0
    for c in reversed(seq):
        if not c:
            break
        current += 1
    per_weekday = [0] * 7
    for _, c, wd in days:
        per_weekday[wd] += c
    bd = dt.date.fromisoformat(best[0])
    return {
        "best": f"{best[1]} · {MONTHS[bd.month - 1]} {bd.day}",
        "longest": longest, "current": current,
        "weekday": WEEKDAYS[per_weekday.index(max(per_weekday))],
        "active": sum(1 for d in days if d[1]),
    }


def render_activity(t, stats) -> str:
    W, H = 880, 330
    weeks = stats["calendar"]
    a = activity_stats(weeks)
    mx = max((c for wk in weeks for _, c, _ in wk), default=1) or 1
    b = [frame(W, H, t)]
    b.append(f'<text x="32" y="44" class="lb">ACTIVITY · LAST 12 MONTHS</text>')
    b.append(f'<text x="{W - 32}" y="44" class="lb" text-anchor="end">PUBLIC + PRIVATE</text>')
    cols = [("TOTAL", f'{stats["contributions"]}'), ("ACTIVE DAYS", str(a["active"])),
            ("BEST DAY", a["best"]), ("LONGEST STREAK", f'{a["longest"]} d'), ("FAVOURITE DAY", a["weekday"])]
    for i, (label, value) in enumerate(cols):
        x = 32 + i * 166
        b.append(f'<text x="{x}" y="78" class="lb" font-size="10">{esc(label)}</text>')
        b.append(f'<text x="{x}" y="104" class="b" font-size="21">{esc(value)}</text>')
    # cabinet projection: weeks to the right, weekdays receding up-left, bars going up
    ex, ey = (13.2, 0.0), (5.0, 7.0)
    ox = (W - (len(weeks) * ex[0] + 7 * ey[0])) / 2
    oy, maxh, fp = 196, 70, .78
    lv = t["levels"]
    cells = []
    for w, wk in enumerate(weeks):
        for date, c, d in wk:
            cells.append((w, d, c, date))
    cells.sort(key=lambda z: (z[1], -z[0]))  # back rows first, right to left inside a row
    today = weeks[-1][-1][0] if weeks and weeks[-1] else ""
    for w, d, c, date in cells:
        x0 = ox + w * ex[0] + d * ey[0]
        y0 = oy + d * ey[1]
        A = (x0, y0)
        B = (x0 + fp * ex[0], y0)
        C = (x0 + fp * ex[0] + fp * ey[0], y0 + fp * ey[1])
        D = (x0 + fp * ey[0], y0 + fp * ey[1])
        level = 0 if c == 0 else 1 if c <= mx * .25 else 2 if c <= mx * .5 else 3 if c <= mx * .75 else 4
        h = 0 if c == 0 else 4 + maxh * math.sqrt(c / mx)
        up = lambda p: (p[0], p[1] - h)
        poly = lambda pts, fill: f'<polygon points="{" ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)}" fill="{fill}"/>'
        if h:
            b.append(poly([up(A), up(D), D, A], shade(lv[level], .62)))
            b.append(poly([up(D), up(C), C, D], shade(lv[level], .8)))
        b.append(poly([up(A), up(B), up(C), up(D)], lv[level]))
        if date == today:
            tx, ty = (up(A)[0] + up(C)[0]) / 2, (up(A)[1] + up(C)[1]) / 2
            b.append(f'<circle cx="{tx:.1f}" cy="{ty - 10:.1f}" r="3" fill="{t["primary"]}">'
                     f'<animate attributeName="r" values="3;6;3" dur="1.8s" repeatCount="indefinite"/>'
                     f'<animate attributeName="opacity" values="1;.3;1" dur="1.8s" repeatCount="indefinite"/></circle>')
    prev = None
    for w, wk in enumerate(weeks):
        m = int(wk[0][0][5:7])
        if m != prev and w > 0:
            x = ox + w * ex[0] + 7 * ey[0]
            b.append(f'<text x="{x:.1f}" y="{oy + 7 * ey[1] + 22:.1f}" font-size="10.5" class="mu m">{MONTHS[m - 1]}</text>')
        prev = m
    lx = W - 32 - 5 * 14 - 70
    b.append(f'<text x="{lx}" y="{H - 22}" font-size="10.5" class="mu" text-anchor="end">less</text>')
    for k in range(5):
        b.append(f'<rect x="{lx + 8 + k * 14}" y="{H - 32}" width="11" height="11" rx="2.5" fill="{lv[k]}"/>')
    b.append(f'<text x="{lx + 8 + 5 * 14 + 4}" y="{H - 22}" font-size="10.5" class="mu">more</text>')
    b.append(f'<text x="32" y="{H - 22}" font-size="10.5" class="mu">current streak: {a["current"]} d · refreshed daily</text>')
    desc = (f"3D contribution calendar for the last 12 months: {stats['contributions']} contributions over "
            f"{a['active']} active days, best day {a['best']}, longest streak {a['longest']} days.")
    return svg_doc(W, H, "Activity · shalee-pnt", desc, "\n".join(b), t)


# --------------------------------------------------------------------------- Lumiose skyline

def render_skyline(t, stats, theme) -> str:
    """One building per week, one lit window per contribution. The lights come on week by
    week, and the Prism Tower lights up when the sweep reaches the best week."""
    c = CITY[theme]
    W, H, gy, cx = 880, 300, 252, 440
    weeks = stats["calendar"]
    n = len(weeks)
    totals = [sum(d[1] for d in wk) for wk in weeks]
    mx = max(totals, default=0) or 1
    best = max(range(n), key=lambda i: (totals[i], i))
    D, t0, t1 = 14.0, 1.0, 9.0
    at = lambda i: (t0 + (t1 - t0) * i / max(1, n - 1)) / D

    def gate(a) -> str:
        return (f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
                f'keyTimes="0;{a:.4f};{a + .02:.4f};.9;.95;1" dur="{D}s" repeatCount="indefinite"/>')

    rng = random.Random("lumiose")
    b = [frame(W, H, t, dotted=False)]

    # sky: stars and moon at night, low sun at dusk
    if c["sun"]:
        for r, col in ((118, c["sun"][0]), (84, c["sun"][1])):
            b.append(f'<path d="M {cx - r} {gy} A {r} {r} 0 0 1 {cx + r} {gy} Z" fill="{col}"/>')
    else:
        busy = [(20, 20, 430, 76), (590, 20, 860, 100), (296, 80, 344, 128)]
        stars = []
        while len(stars) < 60:
            x, y = rng.uniform(32, 848), rng.uniform(22, 190)
            if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in busy):
                continue
            stars.append((x, y))
            dur, beg = rng.uniform(2.2, 5.5), rng.uniform(0, 5)
            b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rng.uniform(.6, 1.4):.2f}" fill="{c["star"]}">'
                     f'<animate attributeName="opacity" values="1;.2;1" dur="{dur:.2f}s" begin="{beg:.2f}s" repeatCount="indefinite"/></circle>')
        b.append(f'<circle cx="320" cy="104" r="15" fill="{c["moon"]}"/><circle cx="327" cy="99" r="13" fill="{t["bg"]}"/>')

    # far skyline (decoration only, fixed shape)
    x = 28.0
    while x < 852:
        w, h = rng.uniform(16, 38), rng.uniform(18, 58)
        b.append(f'<rect x="{x:.1f}" y="{gy - h:.1f}" width="{min(w, 852 - x):.1f}" height="{h:.1f}" fill="{c["far"]}"/>')
        x += w + rng.uniform(-6, 1)

    # Prism Tower
    tw = c["tower"]
    b.append(f'<path d="M {cx - 46} {gy} L {cx - 15} 176 L {cx + 15} 176 L {cx + 46} {gy} L {cx + 28} {gy} '
             f'Q {cx} {gy - 58} {cx - 28} {gy} Z" fill="{tw}"/>')
    b.append(f'<rect x="{cx - 21}" y="171" width="42" height="5" fill="{tw}"/>')
    b.append(f'<polygon points="{cx - 13},171 {cx - 6},108 {cx + 6},108 {cx + 13},171" fill="{tw}"/>')
    b.append(f'<rect x="{cx - 11}" y="103" width="22" height="5" fill="{tw}"/>')
    b.append(f'<polygon points="{cx - 5},103 {cx - 2},84 {cx + 2},84 {cx + 5},103" fill="{tw}"/>')
    edge = lambda y, s: cx + s * (6 + 7 * (y - 108) / 63)
    zig = " ".join(f"{edge(y, 1 if k % 2 else -1):.1f},{y}" for k, y in enumerate(range(168, 108, -9)))
    b.append(f'<polyline points="{zig}" fill="none" stroke="{c["lattice"]}" stroke-width="1"/>')
    b.append(f'<polygon points="{cx},42 {cx},84 {cx - 10},63" fill="{shade(tw, 1.25)}"/>'
             f'<polygon points="{cx},42 {cx + 10},63 {cx},84" fill="{shade(tw, 1.05)}"/>')
    sparks = [(cx + s * (15 + 31 * k / 5), 176 + (gy - 176) * k / 5) for s in (-1, 1) for k in range(1, 5)]
    sparks += [(edge(y, s), y) for s in (-1, 1) for y in (160, 138, 116)]
    sparks += [(cx + s * 21, 173) for s in (-1, 1)] + [(cx + s * 11, 105) for s in (-1, 1)]
    lit = [f'<circle cx="{cx}" cy="63" r="26" fill="{c["glow"]}" opacity=".55" filter="url(#soft)"/>',
           f'<polygon points="{cx},42 {cx},84 {cx - 10},63" fill="{c["prism"]}"/>',
           f'<polygon points="{cx},42 {cx + 10},63 {cx},84" fill="{shade(c["prism"], .82)}"/>']
    for x, y in sparks:
        lit.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.4" fill="{c["spark"]}">'
                   f'<animate attributeName="opacity" values="1;.1;1" dur="{rng.uniform(.5, 1.3):.2f}s" '
                   f'begin="{rng.uniform(0, 1):.2f}s" repeatCount="indefinite"/></circle>')
    b.append(f'<g>{gate(at(best))}{"".join(lit)}</g>')

    # one building per week
    slot = (W - 56) / n
    bw = slot - 3
    wm = (bw - 2 * 3 - 2.4) / 2
    for i, wk in enumerate(weeks):
        tot = totals[i]
        r = random.Random(f"lumiose/{wk[0][0]}")
        floors = 3 if tot == 0 else min(22, max(3 + round(19 * math.sqrt(tot / mx)), math.ceil(tot / 2)))
        bx = 28 + i * slot + 1.5
        top = gy - floors * 6 - 4
        fill = shade(c["bld"], r.uniform(.9, 1.12))
        b.append(f'<rect x="{bx:.1f}" y="{top}" width="{bw:.1f}" height="{gy - top}" fill="{fill}"/>')
        roof = r.randrange(4)
        if i == n - 1:  # this week: blinking aircraft light
            b.append(f'<line x1="{bx + bw / 2:.1f}" y1="{top}" x2="{bx + bw / 2:.1f}" y2="{top - 10}" stroke="{fill}" stroke-width="1.4"/>'
                     f'<circle cx="{bx + bw / 2:.1f}" cy="{top - 11}" r="2" fill="{c["beacon"]}">'
                     f'<animate attributeName="opacity" values="1;1;.1;.1" keyTimes="0;.5;.55;1" dur="1.6s" repeatCount="indefinite"/></circle>')
        elif roof == 1:
            b.append(f'<line x1="{bx + bw / 2:.1f}" y1="{top}" x2="{bx + bw / 2:.1f}" y2="{top - 8}" stroke="{fill}" stroke-width="1.2"/>')
        elif roof == 2:
            b.append(f'<rect x="{bx + 3:.1f}" y="{top - 5}" width="{bw - 6:.1f}" height="5" fill="{fill}"/>')
        elif roof == 3:
            b.append(f'<rect x="{bx + 2:.1f}" y="{top - 4}" width="4" height="4" fill="{fill}"/>')
        spots = [(bx + wm + col * 5.4, top + 4 + f * 6) for f in range(floors) for col in (0, 1)]
        on = set(r.sample(range(len(spots)), min(tot, len(spots))))
        paths = {}
        for k, (x, y) in enumerate(spots):
            col = r.choice(c["lit"]) if k in on else c["win"]
            paths.setdefault(col, []).append(f"M{x:.1f} {y}h3v3.4h-3z")
        b.append(f'<path d="{"".join(paths.pop(c["win"], []))}" fill="{c["win"]}"/>')
        if paths:
            b.append(f'<g>{gate(at(i))}' + "".join(f'<path d="{"".join(p)}" fill="{col}"/>' for col, p in paths.items()) + '</g>')

    # street and months
    b.append(f'<rect x="24" y="{gy}" width="{W - 48}" height="2" rx="1" fill="{t["line"]}"/>')
    prev = None
    for i, wk in enumerate(weeks):
        m = int(wk[0][0][5:7])
        if m != prev and i > 0:
            b.append(f'<text x="{28 + i * slot + 1.5:.1f}" y="{gy + 22}" font-size="10.5" class="mu m">{MONTHS[m - 1]}</text>')
        prev = m

    # captions
    bw0 = weeks[best]
    d0, d1 = dt.date.fromisoformat(bw0[0][0]), dt.date.fromisoformat(bw0[-1][0])
    span = f"{MONTHS[d0.month - 1]} {d0.day} – {MONTHS[d1.month - 1]} {d1.day}"
    b.append(f'<text x="32" y="44" class="lb">{esc(c["title"])}</text>')
    b.append(f'<text x="32" y="66" class="mu" font-size="12.5">1 building = 1 week · 1 lit window = 1 contribution</text>')
    b.append(f'<text x="{W - 32}" y="44" class="lb" text-anchor="end">PRISM TOWER · BEST WEEK</text>')
    b.append(f'<text x="{W - 32}" y="70" class="b" font-size="19" text-anchor="end">{totals[best]} contributions</text>')
    b.append(f'<text x="{W - 32}" y="90" class="mu" font-size="12.5" text-anchor="end">{esc(span)}</text>')
    desc = (f"Lumiose City skyline built from the last {n} weeks of contributions: one building per week, "
            f"one lit window per contribution. The Prism Tower lights up on the best week, "
            f"{span}, with {totals[best]} contributions.")
    return svg_doc(W, H, "Lumiose skyline · shalee-pnt", desc, "\n".join(b), t)


# --------------------------------------------------------------------------- wild bugs

def sprite(sid, t) -> str:
    ol = t["outline"]
    eye = lambda x, y, r=6: (f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 1.25}" fill="#ffffff" stroke="{ol}" stroke-width="2"/>'
                             f'<circle cx="{x + 1.5}" cy="{y + 1}" r="{r * .5}" fill="#141414"/>')
    if sid == "undefinedeon":
        return (f'<g>{bob(6, 3)}<g opacity=".92"><animate attributeName="opacity" values=".92;.55;.92" dur="4s" repeatCount="indefinite"/>'
                f'<path d="M -50 44 L -50 -10 A 50 50 0 0 1 50 -10 L 50 44 Q 37 30 25 44 Q 12 58 0 44 Q -12 30 -25 44 Q -37 58 -50 44 Z" fill="#8b7cf6" stroke="{ol}" stroke-width="2.5"/>'
                f'{eye(-17, -8, 7)}{eye(17, -8, 7)}<ellipse cx="0" cy="16" rx="6" ry="8" fill="{ol}"/></g>'
                f'<text x="44" y="-50" class="b" font-size="30" fill="#8b7cf6">?</text>'
                f'<text x="-138" y="-24" class="b m" font-size="12" fill="#8b7cf6" opacity=".8">typeof ???</text></g>')
    if sid == "off-by-onyx":
        rocks = []
        pts = [(-58, 40, 13), (-36, 28, 16), (-10, 14, 19), (16, -2, 22), (42, -22, 27)]
        for x, y, r in pts:
            rocks.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#a59d8c" stroke="{ol}" stroke-width="2.5"/>'
                         f'<path d="M {x - r * .4} {y - r * .3} l {r * .3} {r * .25} l {r * .2} {-r * .3}" fill="none" stroke="#7d7566" stroke-width="2"/>')
        return (f'<g>{bob(3, 2.6)}{"".join(rocks)}{eye(36, -28, 6)}{eye(54, -26, 5)}'
                f'<path d="M 34 -8 Q 44 -2 54 -8" fill="none" stroke="{ol}" stroke-width="2.5" stroke-linecap="round"/>'
                f'<g><circle cx="-84" cy="50" r="10" fill="none" stroke="#a59d8c" stroke-width="2.5" stroke-dasharray="4 3"/>'
                f'<text x="-84" y="30" text-anchor="middle" class="b m" font-size="13" fill="#a59d8c">+1</text>'
                f'<animate attributeName="opacity" values="1;.2;1" dur="2s" repeatCount="indefinite"/></g></g>')
    if sid == "segfaultoise":
        return (f'<g>{bob(2, 3.6)}'
                f'<rect x="-44" y="24" width="18" height="22" rx="7" fill="#9ccbd6" stroke="{ol}" stroke-width="2.5"/>'
                f'<rect x="22" y="24" width="18" height="22" rx="7" fill="#9ccbd6" stroke="{ol}" stroke-width="2.5"/>'
                f'<circle cx="70" cy="2" r="20" fill="#9ccbd6" stroke="{ol}" stroke-width="2.5"/>{eye(74, -2, 6)}'
                f'<path d="M 64 -14 L 82 -8" stroke="{ol}" stroke-width="3" stroke-linecap="round"/>'
                f'<path d="M 66 12 Q 74 8 82 12" fill="none" stroke="{ol}" stroke-width="2.5" stroke-linecap="round"/>'
                f'<path d="M -58 26 Q -58 -50 0 -50 Q 58 -50 58 26 Z" fill="#6f8fa6" stroke="{ol}" stroke-width="2.5"/>'
                f'<path d="M -30 -38 Q 0 -20 30 -38 M -52 0 Q 0 16 52 0" fill="none" stroke="#56778f" stroke-width="3"/>'
                f'<path d="M 2 -50 L -8 -30 L 8 -18 L -6 -2 L 6 12 L -2 26" fill="none" stroke="#ffd166" stroke-width="3.5" stroke-linejoin="round">'
                f'<animate attributeName="stroke-opacity" values="1;.3;1" dur="1.2s" repeatCount="indefinite"/></path>'
                f'<rect x="-62" y="22" width="124" height="12" rx="6" fill="#56778f" stroke="{ol}" stroke-width="2.5"/></g>')
    if sid == "racecondor":
        def bird(op):
            return (f'<g opacity="{op}"><path d="M -10 0 C -40 -40 -80 -30 -96 -6 C -70 -10 -50 0 -28 10 Z" fill="#3b3b46" stroke="{ol}" stroke-width="2.5"/>'
                    f'<path d="M 10 0 C 40 -40 80 -30 96 -6 C 70 -10 50 0 28 10 Z" fill="#3b3b46" stroke="{ol}" stroke-width="2.5"/>'
                    f'<ellipse cx="0" cy="14" rx="30" ry="24" fill="#3b3b46" stroke="{ol}" stroke-width="2.5"/>'
                    f'<ellipse cx="0" cy="-6" rx="20" ry="8" fill="#f2f2f2" stroke="{ol}" stroke-width="2"/>'
                    f'<circle cx="0" cy="-22" r="13" fill="#f0a39f" stroke="{ol}" stroke-width="2.5"/>'
                    f'<path d="M 8 -24 Q 22 -22 16 -10 L 10 -16 Z" fill="#e9c46a" stroke="{ol}" stroke-width="2"/>'
                    f'{eye(-3, -25, 4)}</g>')
        return (f'<g>{bob(8, 2.2)}<g transform="translate(-16 -8)">{bird(.35)}'
                f'<animateTransform attributeName="transform" type="translate" values="-16 -8;14 -4;-16 -8" dur="1.3s" repeatCount="indefinite"/></g>'
                f'{bird(1)}</g>')
    if sid == "heisenbuzz":
        return (f'<g>{bob(10, 1.8)}<g><animate attributeName="opacity" values="1;1;.12;1" keyTimes="0;.6;.75;1" dur="2.8s" repeatCount="indefinite"/>'
                f'<ellipse cx="-14" cy="-30" rx="26" ry="16" fill="#ffd6ec" fill-opacity=".7" stroke="{ol}" stroke-width="2" transform="rotate(-25 -14 -30)"/>'
                f'<ellipse cx="18" cy="-32" rx="26" ry="16" fill="#ffd6ec" fill-opacity=".7" stroke="{ol}" stroke-width="2" transform="rotate(25 18 -32)"/>'
                f'<ellipse cx="-30" cy="8" rx="26" ry="18" fill="#f472b6" stroke="{ol}" stroke-width="2.5"/>'
                f'<path d="M -44 -6 L -44 22 M -30 -10 L -30 26" stroke="#9d174d" stroke-width="4"/>'
                f'<circle cx="4" cy="2" r="16" fill="#f472b6" stroke="{ol}" stroke-width="2.5"/>'
                f'<circle cx="30" cy="-4" r="15" fill="#f9a8d4" stroke="{ol}" stroke-width="2.5"/>{eye(34, -7, 5)}'
                f'<path d="M 30 -18 Q 30 -40 44 -46 M 38 -16 Q 46 -34 60 -36" fill="none" stroke="{ol}" stroke-width="2.5" stroke-linecap="round"/>'
                f'</g><text x="-60" y="52" class="b m" font-size="11" fill="#f472b6" opacity=".85">observed? no.</text></g>')
    if sid == "memleech":
        return (f'<g>{bob(2, 4)}<g><animateTransform attributeName="transform" type="scale" values="1;1.12;1" dur="6s" repeatCount="indefinite"/>'
                f'<path d="M -70 30 C -70 -10 -30 -30 10 -24 C 50 -18 70 0 66 22 C 62 44 -70 52 -70 30 Z" fill="#a855f7" stroke="{ol}" stroke-width="2.5"/>'
                f'<path d="M -50 12 Q -40 4 -30 12 M -18 4 Q -8 -4 2 4 M 14 2 Q 24 -6 34 2" fill="none" stroke="#7e22ce" stroke-width="3" stroke-linecap="round"/>'
                f'<circle cx="62" cy="18" r="11" fill="#7e22ce" stroke="{ol}" stroke-width="2.5"/><circle cx="62" cy="18" r="5" fill="#2e1065"/>'
                f'{eye(40, -8, 5)}{eye(52, -6, 4)}</g>'
                f'<text x="20" y="-34" class="b m" font-size="12" fill="#a855f7">+1 MB'
                f'<animate attributeName="y" values="-30;-60" dur="2s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="1;0" dur="2s" repeatCount="indefinite"/></text></g>')
    if sid == "infiniloop":
        return (f'<g>{bob(3, 3)}<g><animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="10s" repeatCount="indefinite"/>'
                f'<circle r="44" fill="none" stroke="{ol}" stroke-width="22"/>'
                f'<circle r="44" fill="none" stroke="#6366f1" stroke-width="17"/>'
                f'<circle r="44" fill="none" stroke="#a5b4fc" stroke-width="4" stroke-dasharray="6 10"/>'
                f'<ellipse cx="6" cy="-46" rx="18" ry="14" fill="#6366f1" stroke="{ol}" stroke-width="2.5"/>'
                f'{eye(12, -50, 4.5)}<path d="M -8 -40 L -16 -46 L -8 -50" fill="none" stroke="{ol}" stroke-width="2.5"/></g>'
                f'<text x="0" y="6" text-anchor="middle" class="b m" font-size="13" fill="#6366f1">100%</text></g>')
    if sid == "conflictwin":
        return (f'<g>{bob(4, 2.4)}'
                f'<rect x="-46" y="-6" width="92" height="56" rx="24" fill="#d6c3a5" stroke="{ol}" stroke-width="2.5"/>'
                f'<text x="0" y="28" text-anchor="middle" class="b m" font-size="13" fill="{ol}">=======</text>'
                f'<circle cx="-28" cy="-24" r="22" fill="#f87171" stroke="{ol}" stroke-width="2.5"/>'
                f'<circle cx="28" cy="-24" r="22" fill="#4ade80" stroke="{ol}" stroke-width="2.5"/>'
                f'{eye(-32, -28, 5)}{eye(24, -28, 5)}'
                f'<path d="M -40 -40 L -24 -34 M 40 -40 L 24 -34" stroke="{ol}" stroke-width="3" stroke-linecap="round"/>'
                f'<text x="-28" y="-54" text-anchor="middle" class="b m" font-size="12" fill="#f87171">&lt;&lt;&lt;</text>'
                f'<text x="28" y="-54" text-anchor="middle" class="b m" font-size="12" fill="#4ade80">&gt;&gt;&gt;</text>'
                f'<rect x="-36" y="46" width="16" height="12" rx="5" fill="#d6c3a5" stroke="{ol}" stroke-width="2.5"/>'
                f'<rect x="20" y="46" width="16" height="12" rx="5" fill="#d6c3a5" stroke="{ol}" stroke-width="2.5"/></g>')
    raise KeyError(sid)


def render_encounter(t, daily, state) -> str:
    W, H = 880, 290
    sid, lvl = daily["bug"], daily["bug_level"]
    _, name, typ, rate, entry = SPECIES_BY_ID[sid]
    dex = state["dex"].get(sid, {"caught": 0, "escaped": 0})
    num = [s[0] for s in SPECIES].index(sid) + 1
    b = [f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["sky1"]}"/>'
         f'<stop offset="1" stop-color="{t["sky2"]}"/></linearGradient>'
         f'<radialGradient id="grass" cx=".5" cy=".4" r=".6"><stop offset="0" stop-color="{t["grass1"]}"/>'
         f'<stop offset="1" stop-color="{t["grass2"]}"/></radialGradient></defs>']
    b.append(f'<g clip-path="url(#frame)"><rect width="{W}" height="{H}" fill="url(#sky)"/>')
    for k in range(7):
        y = 26 + k * 26
        b.append(f'<rect x="-200" y="{y}" width="{120 + k * 13 % 70}" height="2" rx="1" fill="{t["primary"]}" opacity=".18">'
                 f'<animate attributeName="x" values="-200;{W}" dur="{2.4 + k * .3:.1f}s" begin="{k * .35:.2f}s" repeatCount="indefinite"/></rect>')
    b.append(f'<ellipse cx="660" cy="190" rx="176" ry="30" fill="url(#grass)"/>')
    b.append(f'<ellipse cx="660" cy="186" rx="150" ry="20" fill="{t["grass1"]}" opacity=".6"/>')
    b.append(f'<g transform="translate(660 124)">{sprite(sid, t)}</g></g>')
    b.append(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="24" fill="none" stroke="{t["line"]}" stroke-width="1.5"/>')
    b.append(f'<rect x="28" y="26" width="392" height="110" rx="16" fill="{t["panel"]}" stroke="{t["line"]}"/>')
    b.append(f'<text x="48" y="60" class="b" font-size="21">{esc(name.upper())}</text>')
    b.append(f'<text x="400" y="60" text-anchor="end" class="b m" font-size="15"><tspan class="mu" font-size="11">Lv.</tspan> {lvl}</text>')
    ps, pw = pill(48, 72, typ.upper(), TYPE_COLORS[typ], size=9.5, h=18)
    b.append(ps)
    b.append(f'<text x="{48 + pw + 10:.1f}" y="85" font-size="12.5" class="mu m">Bugdex #{num:03d}</text>')
    b.append(f'<text x="48" y="118" font-size="11" class="b m" fill="{t["primary"]}">CATCH</text>')
    b.append(f'<rect x="100" y="110" width="210" height="9" rx="4.5" fill="{t["locked"]}"/>')
    b.append(f'<rect x="100" y="110" width="{210 * rate:.1f}" height="9" rx="4.5" fill="{t["primary"]}"/>')
    b.append(f'<text x="400" y="119" text-anchor="end" font-size="12" class="m mu">{int(rate * 100)}% · {dex["caught"]}✓ {dex["escaped"]}✗</text>')
    b.append(f'<rect x="28" y="214" width="{W - 56}" height="56" rx="14" fill="{t["panel"]}" stroke="{t["primary"]}" stroke-width="2.5"/>')
    b.append(f'<text x="50" y="238" class="b" font-size="16">A wild {esc(name.upper())} appeared!</text>')
    b.append(f'<text x="50" y="259" font-size="13" class="mu">{esc(entry)}</text>')
    b.append(f'<path d="M {W - 56} 252 l 8 0 l -4 6 z" fill="{t["primary"]}"><animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></path>')
    desc = f"A wild {name} ({typ} type, level {lvl}) appeared. Bugdex entry: {entry}"
    return svg_doc(W, H, f"Wild encounter · {name}", desc, "\n".join(b), t)


def render_button(t) -> str:
    W, H = 300, 56
    b = [f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="26.5" fill="{t["panel"]}" stroke="{t["primary"]}" stroke-width="2.5"/>',
         '<g transform="translate(36 28)"><g>'
         '<animateTransform attributeName="transform" type="rotate" values="0;-18;18;-10;0;0" keyTimes="0;.1;.2;.3;.4;1" dur="2.6s" repeatCount="indefinite"/>'
         f'<circle r="16" fill="#ffffff" stroke="{t["outline"]}" stroke-width="2.5"/>'
         f'<path d="M -16 0 A 16 16 0 0 1 16 0 Z" fill="#e5383b" stroke="{t["outline"]}" stroke-width="2.5"/>'
         f'<circle r="5.5" fill="#ffffff" stroke="{t["outline"]}" stroke-width="2.5"/></g></g>',
         f'<text x="66" y="35" class="b" font-size="17">Throw a Poké Ball</text>',
         f'<text x="{W - 24}" y="35" text-anchor="end" class="b" font-size="17" fill="{t["primary"]}">→</text>']
    return svg_doc(W, H, "Throw a Poké Ball", "Opens a pre-filled issue that throws a ball at today's wild bug.", "\n".join(b), t)


# --------------------------------------------------------------------------- data

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"daily": {}, "stats": {}, "log": [], "dex": {}, "throws": {}, "trainers": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


QUERY = """query($login:String!){ user(login:$login){ databaseId createdAt
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount weekday } } } }
  pullRequests(states:MERGED){ totalCount }
  organizations(first:1){ totalCount }
  repositories(ownerAffiliations:OWNER, first:100){ totalCount nodes{ stargazerCount } }
}}"""


def fetch_stats(cached: dict) -> dict:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("no token: keeping cached stats", file=sys.stderr)
        return cached
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": f"{LOGIN}-profile"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            u = json.load(r)["data"]["user"]
    except Exception as exc:  # network or API hiccup: the card keeps yesterday's numbers
        print(f"stats fetch failed ({exc}): keeping cached stats", file=sys.stderr)
        return cached
    created = dt.date.fromisoformat(u["createdAt"][:10])
    cal = u["contributionsCollection"]["contributionCalendar"]
    fresh = {
        "trainer_id": f'{u["databaseId"] % 100000:05d}',
        "days": (now_paris().date() - created).days,
        "contributions": cal["totalContributions"],
        "merged_prs": u["pullRequests"]["totalCount"],
        "orgs": u["organizations"]["totalCount"],
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "calendar": [[[d["date"], d["contributionCount"], d["weekday"]] for d in wk["contributionDays"]]
                     for wk in cal["weeks"]],
    }
    # The Actions token cannot see private repos or private org memberships:
    # milestone counters never go down because of a less privileged token.
    for k in ("merged_prs", "orgs", "repos", "stars"):
        fresh[k] = max(fresh[k], cached.get(k, 0))
    return fresh


def roll_daily(date: str) -> dict:
    rng = random.Random(f"shalee-pnt/{date}")
    return {
        "date": date,
        "party": [[rng.randint(12, 98), rng.randint(8, 100)] for _ in PARTY],
        "nature": rng.randrange(len(NATURES)),
        "bug": rng.choice(SPECIES)[0],
        "bug_level": rng.randint(3, 64),
    }


# --------------------------------------------------------------------------- README blocks

def status_block(now: dt.datetime) -> str:
    h, weekend = now.hour, now.weekday() >= 5
    if 23 <= h or h < 7:
        head, tail = "Asleep.", "Even Dunsparce needs eight hours."
    elif weekend:
        head, tail = "Weekend.", "Napping like a Dunsparce. Back on Monday."
    elif h < 9:
        head, tail = "Booting up.", "Coffee first. Code later. Maybe."
    elif h == 12:
        head, tail = "Lunch break.", "PastaBox in progress. Do not disturb."
    elif h < 17:
        head, tail = "Clocked in.", "At city hall or at school, depending on the week. Replies may be slow."
    else:
        head, tail = "Clocked out.", "Side projects, or doing nothing. Probably nothing."
    return f'<p align="center"><sub><b>{head}</b> {tail} · <i>live status, Paris time</i></sub></p>'


def picture(name: str, alt: str, width: str = "100%") -> str:
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/dark/{name}.svg">'
            f'<img alt="{esc(alt)}" src="assets/light/{name}.svg" width="{width}"></picture>')


def encounter_block(state) -> str:
    title = "catch: throw a Poké Ball"
    body = ("Just press **Create** (or **Submit new issue**).\n\n"
            "A GitHub Action throws the ball at today's wild bug and replies here within a minute or two. "
            "One throw per trainer per day.")
    url = f"https://github.com/{REPO}/issues/new?title={quote(title)}&body={quote(body)}"
    lines = [f'<p align="center"><a href="{url}">{picture("button", "Throw a Poké Ball", "300")}</a></p>', ""]
    caught_species = sum(1 for v in state["dex"].values() if v.get("caught"))
    throws = sum(v.get("caught", 0) + v.get("escaped", 0) for v in state["dex"].values())
    lines.append(f'<p align="center"><sub><b>Bugdex</b> {caught_species}/{len(SPECIES)} species caught by visitors · '
                 f'{throws} throws · {len(state["trainers"])} trainers · a new bug appears every day at midnight (Paris)</sub></p>')
    lines.append("")
    if state["log"]:
        lines += ["| Trainer | Bug | Result | Date |", "|:--|:--|:--|:--|"]
        for e in state["log"][:8]:
            res = "caught" if e["caught"] else "broke free"
            lines.append(f'| [@{e["login"]}](https://github.com/{e["login"]}) | {SPECIES_BY_ID[e["bug"]][1]} | {res} | {e["date"]} |')
    else:
        lines.append('<p align="center"><sub><i>No throws yet. The bugs are getting comfortable.</i></sub></p>')
    return "\n".join(lines)


def replace_block(text: str, name: str, content: str) -> str:
    pat = re.compile(rf"(<!-- {name}:start -->)(.*?)(<!-- {name}:end -->)", re.S)
    if not pat.search(text):
        raise SystemExit(f"README marker '{name}' not found")
    return pat.sub(lambda m: f"{m.group(1)}\n{content}\n{m.group(3)}", text)


def write_readme(state, now):
    text = README.read_text(encoding="utf-8")
    text = replace_block(text, "status", status_block(now))
    text = replace_block(text, "encounter", encounter_block(state))
    README.write_text(text, encoding="utf-8", newline="\n")


def write_assets(state, which=("card", "party", "projects", "activity", "skyline", "encounter", "button")):
    for theme, t in THEMES.items():
        out = ASSETS / theme
        out.mkdir(parents=True, exist_ok=True)
        renders = {
            "card": lambda: render_card(t, state["stats"], state["daily"]),
            "party": lambda: render_party(t, state["daily"]),
            "projects": lambda: render_projects(t),
            "activity": lambda: render_activity(t, state["stats"]),
            "skyline": lambda: render_skyline(t, state["stats"], theme),
            "encounter": lambda: render_encounter(t, state["daily"], state),
            "button": lambda: render_button(t),
        }
        for name in which:
            (out / f"{name}.svg").write_text(renders[name](), encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- commands

def cmd_update(force: bool):
    state = load_state()
    now = now_paris()
    today = now.date().isoformat()
    if force or state["daily"].get("date") != today:
        state["stats"] = fetch_stats(state.get("stats", {}))
        if not state["stats"].get("calendar"):
            raise SystemExit("no stats available yet: run once with GH_TOKEN set")
        state["daily"] = roll_daily(today)
        state["throws"] = {today: state.get("throws", {}).get(today, [])}
        write_assets(state)
        save_state(state)
    write_readme(state, now)


def cmd_encounter():
    number = int(os.environ["ISSUE_NUMBER"])
    login = os.environ["ISSUE_AUTHOR"]
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?", login):
        raise SystemExit("unexpected login format")
    reply = Path(os.environ.get("REPLY_FILE", "reply.md"))
    state = load_state()
    now = now_paris()
    today = now.date().isoformat()
    if state["daily"].get("date") != today:  # first visitor of the day wakes the new bug up
        cmd_update(force=False)
        state = load_state()
    sid = state["daily"]["bug"]
    _, name, typ, rate, entry = SPECIES_BY_ID[sid]
    throws_today = state["throws"].setdefault(today, [])
    if login.lower() in throws_today:
        reply.write_text(
            f"You already threw a ball today, @{login}.\n\n"
            "Larry would tell you to clock out and come back tomorrow. A new bug appears at midnight (Paris time).",
            encoding="utf-8")
        return
    caught = random.Random(f"{number}/{login}/{today}").random() < rate
    throws_today.append(login.lower())
    dex = state["dex"].setdefault(sid, {"caught": 0, "escaped": 0})
    dex["caught" if caught else "escaped"] += 1
    if login.lower() not in state["trainers"]:
        state["trainers"].append(login.lower())
    state["log"].insert(0, {"login": login, "bug": sid, "caught": caught, "date": today})
    state["log"] = state["log"][:20]
    save_state(state)
    write_assets(state, which=("encounter",))
    write_readme(state, now)
    if caught:
        msg = (f"### Gotcha! {name} was caught!\n\n"
               f"Nice throw, @{login}. The bug has been moved to the backlog, where it will be very happy.\n\n"
               f"> **Bugdex · {name}** ({typ}): {entry}")
    else:
        msg = (f"### Oh no! The wild {name} broke free.\n\n"
               f"Good try, @{login}. It is in production now. Come back tomorrow for a new one.\n\n"
               f"> **Bugdex · {name}** ({typ}): {entry}")
    reply.write_text(msg + f"\n\n<sub>Catch rate {int(rate * 100)}% · your throw is logged in the "
                     f"[profile README](https://github.com/{LOGIN}).</sub>\n", encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] not in ("update", "encounter"):
        raise SystemExit(__doc__)
    if args[0] == "update":
        cmd_update(force="--force" in args)
    else:
        cmd_encounter()
