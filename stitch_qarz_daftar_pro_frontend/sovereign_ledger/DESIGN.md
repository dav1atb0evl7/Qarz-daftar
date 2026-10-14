---
name: Sovereign Ledger
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#0051d5'
  on-secondary: '#ffffff'
  secondary-container: '#316bf3'
  on-secondary-container: '#fefcff'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002113'
  on-tertiary-container: '#009668'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  title-md:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  label-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  currency-display:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  currency-tabular:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-lg: 1.5rem
  margin: 1rem
  margin-md: 1.5rem
  margin-lg: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system is engineered for debt tracking, credit line auditing, and customer ledger management. It establishes an atmosphere of absolute fiscal clarity, precision, and structural authority. The experience balances an authoritative dark navigation core with an ultra-clean, daylight workspace designed to minimize visual fatigue during high-volume data reconciliation.

The design movement combines **Precision Modernism** with subtle **Tonal Architectural Layering**:
- Utilitarian efficiency dominates layout logic: zero unnecessary decoration, dense yet breathable information architecture, and immediate numerical legibility.
- Strict visual hierarchy enforces fast scanning of counterparty balances, aging buckets, settled ledgers, and overdue exposure.
- Tone is institutional yet agile—combining the gravitas of a tier-one core banking terminal with the fluidity and low-friction workflows of modern enterprise software.
- Critical fiscal indicators—surpluses, delinquent loans, settlement states—are treated with high-visibility chromatic coding that leaves no room for ambiguity.

## Colors

The palette employs a dual-realm architecture: deep, focused slate tones for system controls and structure, paired with a pristine, low-strain neutral canvas for financial processing.

### Primary Canvas & Shell
- **Canvas Base**: `#F8FAFC` (workspace background)
- **Surface Elevation 0 (Flat)**: `#FFFFFF` (data tables, card containers, dialog interiors)
- **Surface Elevation 1 (Muted)**: `#F1F5F9` (table headers, input fills, subtle grouping panels)
- **Primary Text**: `#0F172A` (deepest slate navy for high-contrast tabular figures and headlines)
- **Secondary Text**: `#475569` (supporting metadata, balance timestamps, audit labels)
- **Muted Text / Placeholder**: `#94A3B8` (inactive states, placeholder strings, counter labels)
- **Structural Outlines**: `#E2E8F0` (table rules, panel borders, card seams)
- **Subtle Dividers**: `#F1F5F9`

### Dark Navigation Shell (Sidebar & Global Command)
- **Sidebar Surface**: `#0B132B`
- **Sidebar Surface Hover / Active**: `#1C2541`
- **Sidebar Border**: `#1E293B`
- **Sidebar Text Active**: `#FFFFFF`
- **Sidebar Text Inactive**: `#94A3B8`

### Functional Accents & Semantic Roles
- **Action & Interactive Primary**: `#2563EB` (selection states, primary buttons, active links, focused tabs)
- **Action Hover**: `#1D4ED8`
- **Action Subtle Surface**: `#EFF6FF`
- **Settlement & Surplus (Positive)**:
  - Base: `#10B981`
  - Deep / Text: `#059669`
  - Subtle Surface: `#ECFDF5`
  - Border Tint: `#A7F3D0`
- **Arrears & Delinquent Exposure (Alert / Negative)**:
  - Base: `#EF4444`
  - Deep / Text: `#DC2626`
  - Subtle Surface: `#FEF2F2`
  - Border Tint: `#FECACA`
- **Cautionary / Pending Settlement (Warning)**:
  - Base: `#F59E0B`
  - Deep / Text: `#D97706`
  - Subtle Surface: `#FFFBEB`
  - Border Tint: `#FDE68A`

## Typography

The type system relies on **Plus Jakarta Sans** for structural anchoring, titles, and high-impact numerical balance displays, paired with **Inter** for dense transactional tables, data sheets, forms, and audit trails.

### Tabular Formatting Rules
- All numeric rows, balance columns, debt aging spans, and UZS currency amounts must render with `font-feature-settings: "tnum" 1, "cv05" 1, "zero" 1` enabled. This guarantees tabular monospaced alignment of numbers across ledgers.
- The UZS currency symbol (`so'm` or `UZS`) must be styled with `label-md` or `currency-tabular` at 70% opacity, either set slightly smaller than the integer portion or tagged in a dedicated prefix/suffix currency badge.
- Never use stylized or cursive forms for numbers. Maintain strict alignment: text left-aligned, monetary metrics right-aligned, status tokens center-aligned.

## Layout & Spacing

The design system implements a persistent split-shell model:
1. **Command Rail (Navigation)**: Fixed-width (260px expanded, 72px collapsed) vertical rail pinned to the left edge with a dark navy ground (`#0B132B`).
2. **Work Surface**: Fluid layout that expands across the remaining screen width with a max-width constrainer of 1600px for extreme widescreen monitors.

### Grid & Breakpoints
- **Desktop (>= 1280px)**: 12-column grid, 24px gutters, 32px canvas margins. Tables support up to 8 core columns without horizontal scrolling.
- **Laptop / Tablet Landscape (1024px - 1279px)**: 12-column grid, 16px gutters, 24px canvas margins. Secondary ledger metrics collapse into detail flyouts.
- **Tablet Portrait (768px - 1023px)**: 8-column grid, 16px gutters, 20px canvas margins. Sidebar collapses to icon drawer.
- **Mobile (< 768px)**: 4-column grid, 12px gutters, 16px canvas margins. The dark navigation relocates to a full-screen drawer or bottom quick-action bar.

### Spacing Scale & Rhythm
Layout strictly adheres to an 8px base rhythm with a 4px sub-grid for dense form elements and table cells:
- Table cell vertical padding: `space-sm` (8px compact) or `space-md` (12px standard).
- Table cell horizontal padding: `space-lg` (16px).
- Internal card padding: `space-xl` (24px) for metric headers; `space-lg` (16px) for embedded tables.

## Elevation & Depth

Visual separation relies on sharp boundary lines (`#E2E8F0`) reinforced by whisper-quiet, low-opacity ambient shadows tinted in navy. This eliminates muddy contrast while retaining layer definition under bright office lighting.

- **Elevation 0 (Flush / Base Canvas)**: 
  - Background: `#F8FAFC`
  - Shadow: None
  - Border: None
- **Elevation 1 (Cards, Metric Tiles, Table Wrappers)**: 
  - Background: `#FFFFFF`
  - Border: 1px solid `#E2E8F0`
  - Shadow: `0px 1px 2px rgba(15, 23, 42, 0.04), 0px 1px 3px rgba(15, 23, 42, 0.02)`
- **Elevation 2 (Dropdowns, Popovers, Active Filters)**: 
  - Background: `#FFFFFF`
  - Border: 1px solid `#CBD5E1`
  - Shadow: `0px 4px 6px -1px rgba(15, 23, 42, 0.07), 0px 2px 4px -2px rgba(15, 23, 42, 0.05)`
- **Elevation 3 (Modals, Action Drawers, Debt Entry Sheets)**: 
  - Background: `#FFFFFF`
  - Border: 1px solid `#94A3B8` (subtle light-bleed)
  - Shadow: `0px 20px 25px -5px rgba(15, 23, 42, 0.12), 0px 8px 10px -6px rgba(15, 23, 42, 0.08)`
- **Elevation Focus Highlight**: 
  - Never blur inputs; apply an offset dual-ring: `box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px #2563EB`.

## Shapes

The design system uses a disciplined **Soft** geometric profile. Crisp edges with calculated micro-radii communicate reliability and avoid the whimsical appearance of heavily rounded consumer apps.

- **Micro Radii (`rounded-sm`: 4px)**: Checkboxes, status indicator pips, mini UZS currency badges, table inline tags.
- **Component Radii (`rounded`: 6px / 0.25rem)**: Standard buttons, text inputs, search fields, select dropdowns, icon buttons.
- **Container Radii (`rounded-lg`: 8px / 0.5rem)**: Metric overview cards, data tables, filter toolbars.
- **Structural Radii (`rounded-xl`: 12px / 0.75rem)**: Modal windows, side sheet flyouts, summary ledger modules.
- **Full Radius (`rounded-full`)**: Strictly reserved for counterparty customer avatar portraits, status light dots, and pill-shaped live sync indicators.

## Components

### Buttons & Interactive Triggers
- **Primary Action (New Debt Record / Confirm Payment)**: Filled `#2563EB` background with `#FFFFFF` text. Subtle inner top highlight border (`rgba(255, 255, 255, 0.15)`). Hover transforms to `#1D4ED8`. Active state scales down imperceptibly (`scale(0.99)`).
- **Secondary (Export Ledger / Date Filter)**: Surface `#FFFFFF`, border 1px solid `#E2E8F0`, text `#1E293B`. Hover shifts to `#F8FAFC` background with `#CBD5E1` border.
- **Destructive (Write-off Debt / Void Entry)**: Subtle tinted surface `#FEF2F2`, border 1px solid `#FECACA`, text `#DC2626`. Hover changes to filled `#DC2626` with `#FFFFFF` text.
- **Focus Rule**: All focusable triggers must present the high-contrast dual ring (`#2563EB` over `#FFFFFF`).

### Currency Display Badges & Status Chips
- **UZS Currency Formatter**: Currency values are rendered as structured composite chips or right-aligned blocks. The denomination identifier (`UZS` or `so'm`) sits in a subdued container: background `#F1F5F9`, text `#475569`, border 1px solid `#E2E8F0`, uppercase `label-md`.
- **Settled / Positive Status Chip**: Background `#ECFDF5`, text `#065F46`, border 1px solid `#A7F3D0`. Includes a 6px circular green dot (`#10B981`) preceding the label.
- **Overdue / Arrears Status Chip**: Background `#FEF2F2`, text `#991B1B`, border 1px solid `#FECACA`. Paired with an alert pip (`#EF4444`) and optional days overdue counter (e.g., `+45d`).
- **Partial / Pending Chip**: Background `#FFFBEB`, text `#92400E`, border 1px solid `#FDE68A`.

### Financial Data Tables
- **Table Container**: Encased in an Elevation 1 container with continuous 1px `#E2E8F0` border and `rounded-lg` wrapper.
- **Header Row**: Surface `#F8FAFC`, uppercase `label-md` tracking, text `#475569`, 40px height, bottom rule 1px solid `#E2E8F0`.
- **Data Rows**: Base `#FFFFFF`, hover row state `#F8FAFC`. Alternating zebra striping is omitted in favor of clear 1px horizontal borders (`#F1F5F9`).
- **Numerical Alignment**: Customer identifier and date left-aligned; status and aging bucket center-aligned; principal debt, settled amounts, and net balances right-aligned using tabular figures.

### Form Inputs & Currency Fields
- **Standard Input**: Height 38px, border 1px solid `#CBD5E1`, background `#FFFFFF`, text `#0F172A`, radius 6px.
- **Currency Input (Split-Masked)**: Fixed suffix unit addon box displaying `UZS` pinned to the right edge with a `#F1F5F9` background, while the left input accepts real-time comma-separated integers (`12,500,000`).

### Ledger Metric Cards
- White background (`#FFFFFF`), 1px solid `#E2E8F0` border, Elevation 1.
- Top section: subtle uppercase category descriptor (`label-md`) in `#64748B`.
- Center section: high-contrast value in `currency-display` Plus Jakarta Sans (`#0F172A`).
- Bottom section: contextual trend metric showing net change over the selected cycle with directional emerald or rose indicators.