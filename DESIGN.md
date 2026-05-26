---
version: "3.0"
name: MediaDL
description: Media downloader UI. Pure black background with subtle green radial glow, noise texture. Near-black surfaces with #1a1a1a borders. Clean, minimal, dark.
colors:
  primary: "#1DB984"
  primary-hover: "#22d39a"
  primary-glow: "rgba(29, 185, 132, 0.25)"
  primary-muted: "#0a2e1f"
  surface-0: "#050708"
  surface-1: "#0a0c0d"
  surface-2: "#111315"
  surface-3: "#1a1c1e"
  surface-4: "#242628"
  border: "#1a1a1a"
  border-hover: "#2a2a2a"
  border-active: "rgba(29, 185, 132, 0.3)"
  text-primary: "#ffffff"
  text-secondary: "#888888"
  text-tertiary: "#555555"
  youtube: "#FF0000"
  youtube-bg: "#2A1212"
  youtube-border: "#422020"
  instagram: "#E4405F"
  instagram-bg: "#24141E"
  instagram-border: "#33202C"
  success: "#22c55e"
  danger: "#ef4444"
  warning: "#eab308"
typography:
  logo:
    fontFamily: Inter
    fontSize: 2rem
    fontWeight: 800-900
    letterSpacing: "-0.02em"
  h2:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: Inter
    fontSize: 0.9375rem
    fontWeight: 400
    lineHeight: 1.6
  caption:
    fontFamily: Inter
    fontSize: 0.6875rem
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: "JetBrains Mono, SF Mono, Fira Code, monospace"
rounded:
  sm: 8px
  md: 10px
  lg: 16px
  full: 9999px
components:
  input:
    backgroundColor: "transparent"
    rounded: "{rounded.sm}"
    padding: 13px 14px
    border: "1px solid {colors.border}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: 0 24px
  chip:
    rounded: "{rounded.full}"
    padding: 6px 16px
---

## Overview

MediaDL v3 — **pure black** background (#050708) with subtle green radial glow center. Logo is "Media" (white) + "DOWNLOADER" (green, all caps, 900 weight). Near-black surfaces (#111315) with #1a1a1a borders. Minimal, dark, clean.

## Background

Single radial gradient (green, 6% opacity, 60%×50% ellipse at 50% 40%). Fine noise texture overlay at 2.5% opacity. No floating orbs, no animations — static and clean.

## Colors

- **Primary (#1DB984):** Logo accent, fetch button, download buttons, active tabs, focus rings, icon glow.
- **YouTube (#FF0000):** Chip text + icon. Chip bg: #2A1212, border: #422020.
- **Instagram (#E4405F):** Chip text + icon. Chip bg: #24141E, border: #33202C.
- **Borders:** #1a1a1a — very dark, barely visible.

## Typography

Inter for all UI. JetBrains Mono for sizes, stats, durations. Logo: 2rem, 800 weight for "Media", 900 weight for "DOWNLOADER".

## Layout

Single-column, 600px max-width, center-aligned. Header centered with logo + tagline, then input row, then chips. Footer at bottom.

## Components

- **input-shell:** Transparent bg, #1a1a1a border, 8px radius. Paste icon inside right edge.
- **btn-fetch:** Solid green, 8px radius, green glow shadow.
- **chip:** Pill-shaped, colored bg+border per platform. 6px 16px padding.
- **format-item:** Clean row, hover shows bg + border.
- **skeleton:** Shimmer loading placeholder.

## Do's and Don'ts

- **Do** keep pure black (#050708) base — no gray surfaces.
- **Do** keep borders very dark (#1a1a1a).
- **Do** use green glow sparingly (button shadow, icon glow).
- **Don't** use floating orb animations — static background.
- **Don't** auto-download — always require explicit click.
- **Don't** store user data.
