---
name: Couture
description: An archive for a maison's designs, sealed on Solana.
colors:
  paper: "#f4efe6"
  vellum: "#faf7f1"
  sunk-linen: "#ebe4d8"
  rule: "#d4c9b8"
  rule-soft: "#e3dbcd"
  ink: "#1c1915"
  ink-soft: "#6b6256"
  ink-mute: "#756a5d"
  saddle-bronze: "#8b6b43"
  saddle-bronze-text: "#7a5d39"
  saddle-bronze-deep: "#6c5332"
  sage-success: "#5b7650"
  terracotta-danger: "#8e4433"
typography:
  display:
    fontFamily: "'Cormorant Garamond', 'Times New Roman', serif"
    fontSize: "clamp(44px, 7.4vw, 104px)"
    fontWeight: 300
    lineHeight: 1.02
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "'Cormorant Garamond', 'Times New Roman', serif"
    fontSize: "clamp(34px, 4.2vw, 54px)"
    fontWeight: 300
    lineHeight: 1.08
  title:
    fontFamily: "'Cormorant Garamond', 'Times New Roman', serif"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.2
  lede:
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 300
    lineHeight: 1.65
  body:
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 300
    lineHeight: 1.65
    letterSpacing: "0.01em"
  body-small:
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 300
    lineHeight: 1.6
  label:
    fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.28em"
  mono:
    fontFamily: "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    lineHeight: 1.6
rounded:
  none: "0px"
  dot: "50%"
spacing:
  gutter: "clamp(16px, 5vw, 72px)"
  field-gap: "26px"
  card: "clamp(24px, 4vw, 52px)"
  section: "clamp(48px, 9vw, 120px)"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.vellum}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "19px 28px"
    width: "100%"
  button-primary-hover:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "14px 22px"
  button-quiet-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.vellum}"
  input-text:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "10px 0 12px"
  card:
    backgroundColor: "{colors.vellum}"
    rounded: "{rounded.none}"
    padding: "{spacing.card}"
  seal:
    backgroundColor: "{colors.vellum}"
    rounded: "{rounded.none}"
    padding: "32px"
---

# Design System: Couture

## Overview

**Creative North Star: "The Maison Archive"**

Couture looks and behaves like the archive of a couture house. Designs are
catalogued, framed and kept with care, never merchandised. The ground is warm
paper. Type is a light, high-contrast serif set large and loose. Structure
comes from 1px rules, not boxes or shadows. One bronze accent marks what
matters: a seal, an active step, a link to proof. The pages read like an
exhibition catalogue rather than a dashboard.

Every interaction is editorial and ceremonial. Sealing a design or issuing a
certificate should feel like signing an entry into a register, deliberate and
unhurried. Motion is slow and eased: things rise into place and lines draw
across. Nothing bounces. Density is low, whitespace is generous, and one idea
sits on screen at a time.

**Key Characteristics:**
- Warm paper ground with a faint grain, never pure white.
- A light serif for every headline and a tracked uppercase sans for labels.
- Hairline 1px rules carry the structure. Corners are square.
- One accent (Saddle Bronze), used sparingly.
- A hairline monogram "C" as the house mark.

## Colors

Paper and ink, with a single bronze accent; status colors are muted earth tones, not signal colors.

### Primary
- **Saddle Bronze**: the house accent. Use it for eyebrows, links to proof
  (explorer, certificate), active and done timeline steps, the "Sealed" mark
  on pieces, the focus outline and the underline of the current nav item.
- **Saddle Bronze Deep**: the border of the seal panel and the drop-zone hover
  border. It is bronze with more authority.

### Neutral
- **Paper**: the page ground, also the masthead backdrop at 88% opacity.
- **Vellum**: raised surfaces such as cards, piece frames and timeline nodes,
  and the text on ink buttons.
- **Sunk Linen**: the backdrop of the protected viewer, a recessed room for
  the work.
- **Rule / Rule Soft**: hairlines. Rule is for inputs, dashed drop zones and
  the monogram stroke. Rule Soft is for section dividers and card borders.
- **Ink**: body text, primary buttons and the text selection background.
- **Ink Soft / Ink Mute**: secondary copy, then metadata, placeholders and
  inactive states.

### Status
- **Sage**: network OK and success.
- **Terracotta**: errors, failed steps and the offline state.

Both are desaturated so status never outshouts the work.

### Contrast (2026-11-03)
The first palette failed WCAG AA for small text. Ink Mute was 2.9:1 and
bronze was 4.3:1 on Paper. The current values pass on Paper and Vellum:

| Token | Contrast | Use |
|---|---|---|
| Ink Mute | 4.6:1 | Small secondary text. |
| Saddle Bronze Text | 5.3:1 | Bronze for any text under 24px, including links. |
| Terracotta | 6.1:1 | Errors and warnings. |

Saddle Bronze itself is for rules, marks and large type only. Never use Ink
Mute on Sunk Linen.

### Named Rules
**The Single Bronze Rule.** Saddle Bronze is the only accent. It marks proof,
progress and the current place, and nothing decorative. If a screen has more
bronze than a few marks and one rule, it is overused.

**The No-White Rule.** Surfaces are Paper or Vellum. Pure `#fff` and pure
black never appear.

## Typography

**Display Font:** Cormorant Garamond (fallback: Times New Roman, serif), weights 300 to 500 plus italic
**Body Font:** Jost (fallback: Helvetica Neue, Arial, sans-serif), weights 300 to 500
**Label/Mono Font:** Jost for labels; the system monospace for hashes, signatures and addresses

**Character:** a fashion-house serif, light and slightly theatrical, over a
geometric sans held to small, widely tracked capitals. The serif speaks and
the sans annotates.

### Hierarchy
- **Display** (300, fluid 44 to 104px, line-height 1.02): hero headlines
  only. Italic words switch to Saddle Bronze for a single emphasis.
- **Headline** (300, fluid 34 to 54px, line-height 1.08): section titles such
  as "Register a design" and "Verify a design".
- **Title** (400, 22px, line-height 1.2): piece titles, file names and
  sub-section heads. Seal and verdict headings run larger at 30 to 32px, 300.
- **Body** (300, 16px, line-height 1.65): running copy. Ledes are capped at
  34em and set in Ink Soft.
- **Label** (400 to 500, 10 to 11px, tracking 0.22 to 0.32em, uppercase): nav,
  eyebrows, field labels, buttons, timeline steps, facts and the colophon.
- **Mono** (12 to 14px): SHA-256 fingerprints, transaction signatures and
  wallet addresses. Always break anywhere, never truncate.

### Named Rules
**The Serif Speaks Rule.** Anything a person reads as a statement (headline,
title, verdict, empty state) is in the serif. Anything that labels or
operates is tracked uppercase Jost. Nothing sits in between.

**The Proof Is Mono Rule.** Cryptographic values are always in monospace and
shown in full, so they can be compared by eye.

## Layout

- **Gutter:** a single fluid side gutter, `clamp(16px, 5vw, 72px)`, on the
  masthead, every view and the colophon.
- **Sections:** vertical padding of `clamp(48px, 9vw, 120px)`.
- **Masthead:** sticky, on a three-column grid (wordmark, centred nav,
  network status).
- **Archive gallery:** a fluid grid with columns of at least 300px. Each piece
  is 3:4 portrait, with meta below and no overlay.
- **Studio and Verify:** an asymmetric split (5fr : 6fr). The intro column
  stays sticky while the form scrolls.
- **Protected viewer:** a full-screen two-pane layout. The stage holds the
  work; a side panel of at most 420px holds facts and certification.
- **Below 900px:** splits stack and the viewer becomes stage over panel.
- **Below 640px:** the nav drops to its own row and inline forms stack.

## Elevation & Depth

The system is flat. Depth comes from tone (Sunk Linen < Paper < Vellum) and
from hairline rules, not from shadows. There are two exceptions, both tied to
meaning.

### Shadow Vocabulary
- **Gallery lift** (`box-shadow: 0 30px 70px rgba(48, 36, 22, .16)`): only on
  the canvas inside the protected viewer, so the work reads as hung on a wall.
- **Status halo** (`box-shadow: 0 0 0 4px rgba(91, 118, 80, .14)`, and a
  bronze 6px pulse on the active timeline step): a soft ring that signals
  live state.

### Named Rules
**The Hung-Work Rule.** Only the design itself casts a shadow. Cards, buttons
and panels never do.

## Shapes

Every corner is square (0px). Inputs explicitly reset `border-radius` to 0.
The only circles are functional dots: the network status dot and the timeline
nodes. Borders are 1px, solid for structure and dashed only for the file drop
zone, which signals "place something here". The house silhouette is the
hairline monogram "C", drawn as a stroke with a transparent fill, which
appears as a giant mark behind the hero and as the initial of the wordmark.

## Components

### Buttons
Ceremonial: a solid ink block that empties into an outline when hovered, like
ink lifting off the page.
- **Shape:** square (0px), 1px ink border.
- **Primary:** an Ink fill with Vellum label text, full width, 19px × 28px
  padding, label type at 500 weight and 0.32em tracking.
- **Hover:** inverts to transparent with Ink text over 0.35s on the house ease.
- **Disabled:** 45% opacity with a `progress` cursor.
- **Quiet:** starts transparent and fills with Ink on hover, at auto width.
  Use it for secondary actions such as "Look up" and "Issue".
- **Link button:** Saddle Bronze label text with no box. Use it for
  in-context actions such as "Replace".

### Inputs / Fields
- **Style:** underline only. A 1px Rule bottom border on a transparent ground
  holds 18px light Jost text. Labels sit above in tracked uppercase.
- **Focus:** the underline shifts to Saddle Bronze. There is no glow and no box.
- **Fingerprint inputs:** switch to monospace at 14px.
- **Error:** a form note below the field turns Terracotta.

### Cards / Containers
- **Corner Style:** square.
- **Background:** Vellum on Paper.
- **Shadow Strategy:** none (see Elevation).
- **Border:** 1px Rule Soft.
- **Internal Padding:** fluid, from 24 to 52px.

### Navigation
Tracked uppercase labels (11px, 0.28em) in Ink Soft. On hover the label turns
to Ink. On the current page it turns to Ink and a 1px bronze underline draws
from left to right (0.45s). On mobile the nav moves to a full-width second
row of the masthead.

### Registration Timeline (signature)
A vertical register of steps (received, fingerprinted, submitted, sealed),
joined by a hairline.
- **Pending:** an open circle on Vellum.
- **Active:** a bronze ring with a slow pulse.
- **Done:** a solid bronze dot.
- **Error:** a solid Terracotta dot.

Step names are labels; details are body with mono values and bronze links.

### The Seal (signature)
The registration result: a panel with a 1px Saddle Bronze Deep border, a faint
bronze wash fading diagonally, a 32px light serif heading and links to the
on-chain proof. It is the system's one moment of ceremony.

### Protected Viewer (signature)
A full-screen room in Sunk Linen. The canvas is the only shadowed element. A
blurred Paper veil with an italic serif note covers the work when the window
loses focus. Close is a light serif "×".

## Do's and Don'ts

### Do:
- **Do** keep every corner square and every border 1px.
- **Do** use Saddle Bronze only for proof, progress and the current location.
- **Do** set statements in light Cormorant Garamond and labels in tracked
  uppercase Jost (10 to 11px, 0.22 to 0.32em).
- **Do** show hashes, signatures and addresses in full, in monospace.
- **Do** animate with the house ease (`cubic-bezier(.2, .7, .1, 1)`), slowly
  (0.3 to 0.8s, 1.4s for image zoom), and respect `prefers-reduced-motion`.
- **Do** give designs a 3:4 frame on Vellum with a Rule Soft hairline.

### Don't:
- **Don't** add rounded corners, pill buttons or card shadows.
- **Don't** introduce a second accent color, saturated status colors, pure
  white or pure black.
- **Don't** use bold weights for headlines. The serif tops out at 400 to 500
  and runs light (300) at display sizes.
- **Don't** put text or badges over the artwork in the gallery. Meta sits
  below the frame.
- **Don't** use bouncy or springy motion.
