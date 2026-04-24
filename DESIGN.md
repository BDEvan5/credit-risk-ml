---
name: Midnight Mustard
colors:
  surface: '#031523'
  surface-dim: '#031523'
  surface-bright: '#2a3b4b'
  surface-container-lowest: '#000f1e'
  surface-container-low: '#0b1d2c'
  surface-container: '#102130'
  surface-container-high: '#1b2b3b'
  surface-container-highest: '#263646'
  on-surface: '#d3e4f9'
  on-surface-variant: '#d4c5ab'
  inverse-surface: '#d3e4f9'
  inverse-on-surface: '#213242'
  outline: '#9c8f78'
  outline-variant: '#4f4632'
  surface-tint: '#fabd00'
  primary: '#ffe4af'
  on-primary: '#3f2e00'
  primary-container: '#ffc107'
  on-primary-container: '#6d5100'
  inverse-primary: '#785900'
  secondary: '#ffb4a9'
  on-secondary: '#690002'
  secondary-container: '#a40308'
  on-secondary-container: '#ffaea3'
  tertiary: '#d9e8fe'
  on-tertiary: '#233242'
  tertiary-container: '#bdcce1'
  on-tertiary-container: '#485669'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdf9e'
  primary-fixed-dim: '#fabd00'
  on-primary-fixed: '#261a00'
  on-primary-fixed-variant: '#5b4300'
  secondary-fixed: '#ffdad5'
  secondary-fixed-dim: '#ffb4a9'
  on-secondary-fixed: '#410001'
  on-secondary-fixed-variant: '#930005'
  tertiary-fixed: '#d4e4fa'
  tertiary-fixed-dim: '#b8c8dd'
  on-tertiary-fixed: '#0d1d2c'
  on-tertiary-fixed-variant: '#394859'
  background: '#031523'
  on-background: '#d3e4f9'
  surface-variant: '#263646'
typography:
  display-lg:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Work Sans
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Work Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-bold:
    fontFamily: Work Sans
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Work Sans
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.5rem
  DEFAULT: 1rem
  md: 1.5rem
  lg: 2rem
  xl: 3rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 16px
  margin: 24px
---

## Brand & Style

This design system is built on a "Sophisticated Friendly" aesthetic, bridging the gap between playful accessibility and professional financial services. It draws inspiration from Monzo’s approachable character but matures the execution for a high-end dark mode experience.

The style is characterized by **Modern Minimalist** principles with a hint of **Tactile Softness**. By combining deep, atmospheric backgrounds with hyper-rounded corners and vibrant, high-energy accents, the system evokes a sense of security and optimism. The interface should feel like a premium physical wallet—substantial, smooth to the touch, and meticulously organized.

## Colors

The palette is centered around a sophisticated dark mode. The core background uses a custom deep charcoal-navy to provide better depth than pure black, while the primary mustard yellow serves as a high-contrast beacon for calls to action.

- **Primary (Mustard):** A vibrant yellow (#FFC107) used for primary buttons and critical data points.
- **Secondary (Coral):** Sourced from the brand profile (#FF4F40), used sparingly for alerts or secondary accents.
- **Neutral/Surface:** A range of deep blues (#142333 and #112231) are used to create layers of depth.
- **Text:** High-legibility off-white (#EBEBEB) ensures comfortable reading against the dark canvas without the harshness of pure white.

## Typography

The typography strategy uses **Manrope** for headlines to provide a modern, geometric feel that remains friendly and open. **Work Sans** is utilized for body text and labels to ensure maximum legibility and a grounded, professional tone for financial data.

- **Headlines:** Feature tight letter-spacing and bold weights to create a strong visual anchor.
- **Body:** Utilizes a generous line height (1.6) to prevent the dark background from feeling claustrophobic.
- **Numbers:** In financial contexts, use tabular figures from the Work Sans family to ensure vertical alignment in transaction lists.

## Layout & Spacing

This design system employs a **Fluid-Fixed Hybrid** grid. On mobile, it follows a 4-column system with 24px outer margins. On desktop, it scales to a 12-column grid with a maximum content width of 1200px.

The spacing rhythm is based on an 8px baseline, but emphasizes large, airy margins (24px+) to complement the highly rounded corners of the components. Consistency in "inner padding" vs "outer padding" is crucial: container padding should always be at least 24px to ensure content doesn't feel cramped by the aggressive corner radii.

## Elevation & Depth

Depth is achieved through **Tonal Layering** rather than traditional heavy shadows. Because the background is dark, we use subtle luminosity shifts to indicate elevation.

1.  **Level 0 (Background):** The deepest charcoal-navy.
2.  **Level 1 (Cards/Surface):** A slightly lighter navy (#142333).
3.  **Level 2 (Modals/Overlays):** A subtle blue-gray with a soft, 10% opacity white inner-border (stroke) to simulate light catching the edge.

When shadows are used, they are "Ambient Glows"—ultra-diffused, using a darker version of the surface color rather than black, creating a naturalistic "lift."

## Shapes

The defining characteristic of this system is its extreme roundedness. Following the "Pill-shaped" philosophy, primary containers and buttons use a minimum radius of 24px. 

- **Primary Cards:** 32px corner radius.
- **Buttons and Inputs:** Fully pill-shaped (50vh) or a minimum of 24px.
- **Nested Elements:** Must follow the "Radius - Padding = Inner Radius" rule to maintain concentric visual harmony.

This softness offsets the "coldness" typically associated with dark-mode fintech apps, making the experience feel more inviting and human.

## Components

### Buttons
- **Primary:** Mustard yellow background with #000000 text. High-contrast, fully pill-shaped.
- **Secondary:** Ghost style with a 2px Mustard stroke and Mustard text.
- **Tertiary:** Transparent background with off-white text and a subtle underline on hover.

### Cards
- **Transaction Cards:** 32px radius, #142333 background. No border. Use a 48px circular icon slot for merchant logos.
- **Credit Card Visuals:** Uses a subtle gradient blend of the Primary Mustard and Secondary Coral, with 24px rounded corners.

### Form Inputs
- **Fields:** Deep navy background (#0A141D) with a 1px border (#142333). Upon focus, the border transitions to Mustard yellow.
- **Labels:** Always positioned above the input field in `label-bold` style for clarity.

### Feedback Elements
- **Chips/Tags:** Small, highly rounded (16px) badges. Use low-opacity versions of the status color (e.g., 10% Mustard for "Pending") with full-saturation text.
- **Progress Bars:** Thick (12px) pill-shaped tracks. The background track should be a dark neutral, while the progress indicator is a vibrant Mustard glow.

### Specialized Fintech Components
- **Balance Display:** Large `display-lg` typography with the currency symbol in a slightly lighter weight.
- **Quick Actions:** A horizontal scroll of 64px circular buttons with Mustard icons for "Send," "Request," and "Top Up."