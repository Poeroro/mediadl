---
version: alpha
name: MediaDL
description: Media downloader UI. Emerald accent on dark surfaces. Clean, fast, single-purpose. Supports YouTube + Instagram.
colors:
  primary: "#10b981"
  primary-hover: "#34d399"
  primary-muted: "#0a2e1f"
  secondary: "#6ee7b7"
  surface-0: "#09090b"
  surface-1: "#111114"
  surface-2: "#18181b"
  surface-3: "#27272a"
  border: "#2e2e33"
  border-hover: "#3f3f46"
  text-primary: "#fafafa"
  text-secondary: "#a1a1aa"
  text-tertiary: "#52525b"
  success: "#22c55e"
  danger: "#ef4444"
  warning: "#eab308"
  youtube: "#ff0000"
  instagram: "#e1306c"
  light-surface-0: "#fafafa"
  light-surface-1: "#ffffff"
  light-surface-2: "#f4f4f5"
  light-surface-3: "#e4e4e7"
  light-border: "#d4d4d8"
  light-border-hover: "#a1a1aa"
  light-text-primary: "#09090b"
  light-text-secondary: "#52525b"
  light-text-tertiary: "#a1a1aa"
  light-primary-muted: "#ecfdf5"
typography:
  h1:
    fontFamily: Inter
    fontSize: 1.75rem
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  h2:
    fontFamily: Inter
    fontSize: 1.25rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "-0.015em"
  body:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.6
  caption:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: 400
    lineHeight: 1.4
  mono:
    fontFamily: "JetBrains Mono, SF Mono, monospace"
    fontSize: 0.8125rem
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: 8px
  md: 12px
  lg: 16px
  xl: 20px
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  "2xl": 48px
components:
  card:
    backgroundColor: "{colors.surface-2}"
    rounded: "{rounded.lg}"
    padding: 24px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: 12px
  input:
    backgroundColor: "{colors.surface-3}"
    rounded: "{rounded.md}"
    padding: 14px 16px
---

## Overview

MediaDL uses **emerald green** as the accent — fresh, fast, "download" energy. Dark default, light mode via separate token set. Single-page app: paste URL → see metadata → pick format → download. No accounts, no tracking.

## Colors

- **Primary (#10b981):** Emerald — download buttons, active states, progress bars.
- **YouTube (#ff0000):** Brand color for YouTube platform badge.
- **Instagram (#e1306c):** Brand color for Instagram platform badge.
- **Surface hierarchy:** Four levels, same as TempMail ecosystem.

## Typography

Inter UI text. JetBrains Mono for URLs and file sizes.

## Layout

Single-column, 720px max-width. Hero input at top, results card below. Mobile-first.

## Components

- **card:** Rounded 16px, surface-2, 1px border.
- **button-primary:** Solid emerald, white text. Hover brightens.
- **input:** Large surface-3 input with emerald focus ring.

## Do's and Don'ts

- **Do** show platform badges (YouTube red, Instagram pink) for instant recognition.
- **Do** show file size estimates before download.
- **Don't** auto-download — always require user click.
- **Don't** store any user data or URLs.
