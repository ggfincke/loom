# src/ui/theming/theme_definitions.py
# Theme color palette definitions for Loom CLI

from __future__ import annotations


# theme definitions w/ gradient color palettes for CLI styling
THEMES = {
    "pink_purple": [
        "#ff69b4",  # hot pink
        "#ff1493",  # deep pink
        "#da70d6",  # orchid
        "#ba55d3",  # medium orchid
        "#9932cc",  # dark orchid
        "#8a2be2",  # blue violet
    ],
    "deep_blue": [
        "#4a90e2",  # sky blue
        "#357abd",  # medium blue
        "#2563eb",  # royal blue
        "#1d4ed8",  # deep blue
        "#1e40af",  # dark blue
        "#0891b2",  # teal
    ],
    "cyber_neon": [
        "#00ffff",  # pure cyan (electric)
        "#00ccff",  # bright sky cyan
        "#0099ff",  # electric blue
        "#6600ff",  # electric purple (cyber contrast)
        "#9933ff",  # bright purple
        "#00ff99",  # electric mint/green aqua
    ],
    "sunset_coral": [
        "#FF7F50",  # coral
        "#FF8C69",  # salmon
        "#FFA500",  # orange
        "#FFB347",  # peach
        "#FFD700",  # gold
        "#FFDC00",  # bright gold
    ],
    "teal_lime": [
        "#00CED1",  # dark turquoise
        "#20B2AA",  # light sea green
        "#3CB371",  # medium sea green
        "#66CDAA",  # medium aquamarine
        "#90EE90",  # light green
        "#ADFF2F",  # green yellow/lime
    ],
    "volcanic_fire": [
        "#FFD700",  # gold
        "#FFA500",  # orange
        "#FF6347",  # tomato
        "#FF4500",  # orange red
        "#DC143C",  # crimson
        "#8B0000",  # dark red
    ],
    "arctic_ice": [
        "#F0F8FF",  # alice blue
        "#E6F3FF",  # light blue
        "#B0E0E6",  # powder blue
        "#87CEEB",  # sky blue
        "#4682B4",  # steel blue
        "#2F4F4F",  # dark slate gray
    ],
    "synthwave_retro": [
        "#FF00FF",  # magenta
        "#FF0080",  # deep pink
        "#8000FF",  # electric violet
        "#4000FF",  # electric indigo
        "#0080FF",  # electric blue
        "#00FFFF",  # cyan
    ],
    "autumn_harvest": [
        "#FFE4B5",  # moccasin
        "#DEB887",  # burlywood
        "#D2691E",  # chocolate
        "#CD853F",  # peru
        "#A0522D",  # sienna
        "#8B4513",  # saddle brown
    ],
    "galaxy_nebula": [
        "#E6E6FA",  # lavender
        "#DDA0DD",  # plum
        "#DA70D6",  # orchid
        "#9370DB",  # medium purple
        "#6A5ACD",  # slate blue
        "#483D8B",  # dark slate blue
    ],
    "desert_sand": [
        "#FFF8DC",  # cornsilk
        "#F5DEB3",  # wheat
        "#DEB887",  # burlywood
        "#D2B48C",  # tan
        "#BC8F8F",  # rosy brown
        "#A0522D",  # sienna
    ],
    "midnight_purple": [
        "#E6E6FA",  # lavender
        "#C8A2C8",  # lilac
        "#9966CC",  # amethyst
        "#6A0DAD",  # blue violet
        "#4B0082",  # indigo
        "#2E0054",  # dark indigo
    ],
    "ruby_crimson": [
        "#FFB6C1",  # light pink
        "#FF69B4",  # hot pink
        "#FF1493",  # deep pink
        "#DC143C",  # crimson
        "#B22222",  # fire brick
        "#8B0000",  # dark red
    ],
    "emerald_mint": [
        "#98FB98",  # pale green
        "#00FA9A",  # medium spring green
        "#00FF7F",  # spring green
        "#00CED1",  # dark turquoise
        "#20B2AA",  # light sea green
        "#008B8B",  # dark cyan
    ],
    "steel_silver": [
        "#F8F8FF",  # ghost white
        "#E6E6FA",  # lavender
        "#D3D3D3",  # light gray
        "#A9A9A9",  # dark gray
        "#708090",  # slate gray
        "#2F4F4F",  # dark slate gray
    ],
    "copper_bronze": [
        "#FFDAB9",  # peach puff
        "#DEB887",  # burlywood
        "#CD853F",  # peru
        "#B8860B",  # dark goldenrod
        "#A0522D",  # sienna
        "#8B4513",  # saddle brown
    ],
    "lavender_mist": [
        "#F8F8FF",  # ghost white
        "#E6E6FA",  # lavender
        "#DDA0DD",  # plum
        "#BA55D3",  # medium orchid
        "#9370DB",  # medium purple
        "#663399",  # rebecca purple
    ],
    "cobalt_wave": [
        "#93c5fd",  # light blue
        "#60a5fa",  # blue
        "#3b82f6",  # vivid blue
        "#2563eb",  # royal blue
        "#1d4ed8",  # deep blue
        "#1e3a8a",  # navy
    ],
    "forest_night": [
        "#bbf7d0",  # pale mint
        "#86efac",  # light green
        "#22c55e",  # emerald
        "#16a34a",  # green
        "#166534",  # deep green
        "#052e16",  # near black green
    ],
    "twilight_orchid": [
        "#ede9fe",  # pale lavender
        "#c4b5fd",  # soft violet
        "#a78bfa",  # light purple
        "#8b5cf6",  # violet
        "#7c3aed",  # deep violet
        "#4c1d95",  # indigo
    ],
    "graphite_cyan": [
        "#e5e7eb",  # light slate
        "#9ca3af",  # slate
        "#64748b",  # slate gray
        "#22d3ee",  # cyan
        "#06b6d4",  # teal cyan
        "#0e7490",  # deep cyan
    ],
    "peach_sorbet": [
        "#fff1e6",  # cream
        "#ffe0c2",  # soft peach
        "#ffcc99",  # peach
        "#ffb380",  # warm peach
        "#ff9966",  # coral peach
        "#ff7f66",  # coral
    ],
    "dune_sepia": [
        "#f5f5dc",  # beige
        "#ede0c8",  # sand
        "#d2b48c",  # tan
        "#c19a6b",  # camel
        "#8b6b3f",  # brown
        "#5c4033",  # dark brown
    ],
    "neon_tropic": [
        "#f8ff00",  # neon yellow
        "#00ff85",  # neon green
        "#00f5ff",  # aqua
        "#00a1ff",  # bright blue
        "#8a2be2",  # blue violet
        "#ff00e6",  # neon magenta
    ],
    "paper_ink": [
        "#ffffff",  # white
        "#f2f2f2",  # very light gray
        "#d9d9d9",  # light gray
        "#a6a6a6",  # medium gray
        "#595959",  # dark gray
        "#0a0a0a",  # near black
    ],
    "storm_cloud": [
        "#f8fafc",  # off white
        "#e2e8f0",  # light slate
        "#94a3b8",  # slate
        "#64748b",  # slate gray
        "#334155",  # dark slate
        "#0f172a",  # near-black blue
    ],
    "tropical_lagoon": [
        "#e0fff9",  # mint white
        "#a7f3d0",  # soft mint
        "#34d399",  # jade
        "#10b981",  # emerald
        "#14b8a6",  # teal
        "#0d9488",  # deep teal
    ],
    "berry_soda": [
        "#ffe4f1",  # pale rose
        "#ffb1d8",  # light berry
        "#ff74c6",  # berry pink
        "#ff58a7",  # hot pink
        "#ff2e88",  # magenta
        "#d10068",  # deep magenta
    ],
    "obsidian_gold": [
        "#fff7cc",  # pale gold
        "#ffdf80",  # soft gold
        "#ffc933",  # bright gold
        "#b8860b",  # goldenrod
        "#4b5563",  # slate
        "#111827",  # near black
    ],
}
