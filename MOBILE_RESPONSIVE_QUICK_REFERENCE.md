# Mobile Responsive Quick Reference

## Quick Start for Developers

### Understanding the Mobile-First Approach
Write mobile CSS first, then enhance for larger screens using media queries.

```css
/* Mobile (default) */
.component {
    font-size: 14px;
    padding: 1rem;
    width: 100%;
}

/* Tablet and up */
@media (min-width: 768px) {
    .component {
        font-size: 16px;
        padding: 2rem;
        width: 50%;
    }
}
```

---

## Key Breakpoints

```css
/* Ultra-small (280px - 319px) */
@media (max-width: 319px) { }

/* Small phones (320px - 479px) - PRIMARY */
@media (max-width: 479px) { }

/* Medium phones (480px - 639px) */
@media (min-width: 480px) and (max-width: 639px) { }

/* Tablets/Large phones (640px - 767px) */
@media (min-width: 640px) and (max-width: 767px) { }

/* Tablets (768px - 1024px) */
@media (min-width: 768px) and (max-width: 1024px) { }

/* Desktops (1025px+) */
@media (min-width: 1025px) { }

/* Landscape mode */
@media (max-height: 500px) and (orientation: landscape) { }

/* Touch devices */
@media (hover: none) and (pointer: coarse) { }

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) { }
```

---

## Common Components - Mobile Solutions

### Forms
```html
<!-- DO: Full-width input on mobile -->
<input type="text" class="form-control" style="width: 100%; min-height: 44px;">

<!-- DON'T: Small inline inputs -->
<input type="text" style="width: 200px;">
```

### Buttons
```css
/* DO: Full-width buttons on mobile */
.btn {
    width: 100%;
    min-height: 44px;
    padding: 0.5rem 1rem;
}

/* DON'T: Fixed width buttons */
.btn {
    width: 200px;
}
```

### Tables
```html
<!-- DO: Wrap in responsive container -->
<div class="table-responsive">
    <table class="table">
        <!-- table content -->
    </table>
</div>

<!-- DON'T: Raw table that overflows -->
<table>
    <!-- table content -->
</table>
```

### Navigation
```html
<!-- DO: Collapsible navbar on mobile -->
<nav class="navbar navbar-expand-lg">
    <button class="navbar-toggler">☰</button>
    <div class="collapse navbar-collapse">
        <!-- nav items -->
    </div>
</nav>

<!-- DON'T: Always visible horizontal nav -->
<nav>
    <a href="#">Item 1</a>
    <a href="#">Item 2</a>
</nav>
```

### Modals
```html
<!-- DO: Full-screen on mobile, centered on desktop -->
<div class="modal-dialog">
    <div class="modal-content">
        <!-- modal content -->
    </div>
</div>

<!-- DON'T: Fixed width modal -->
<div style="width: 500px; margin: 0 auto;">
    <!-- modal content -->
</div>
```

---

## Touch Target Sizes

```css
/* WCAG 2.1 Level AAA: 44x44px minimum */
.btn, button, a, [role="button"] {
    min-height: 44px;
    min-width: 44px;
}

/* 44px is standard. 48px is better. Never below 40px */
```

---

## Responsive Images

```html
<!-- DO: Use max-width and auto height -->
<img src="image.jpg" alt="Description" 
     style="max-width: 100%; height: auto;">

<!-- DON'T: Fixed dimensions -->
<img src="image.jpg" width="600" height="400">
```

```css
/* CSS approach */
img {
    max-width: 100%;
    height: auto;
    display: block;
}
```

---

## Font Sizes for Mobile

```css
/* Mobile-first sizing */
:root {
    --font-size-h1: 1.5rem;
    --font-size-h2: 1.3rem;
    --font-size-h3: 1.1rem;
    --font-size-p: 1rem;
    --font-size-small: 0.875rem;
}

/* Scale up on larger screens */
@media (min-width: 768px) {
    :root {
        --font-size-h1: 2.5rem;
        --font-size-h2: 2rem;
        --font-size-h3: 1.5rem;
    }
}
```

---

## Spacing System

```css
/* Responsive spacing */
.spacing-unit {
    --spacing-xs: 0.25rem;  /* 4px */
    --spacing-sm: 0.5rem;   /* 8px */
    --spacing-md: 1rem;     /* 16px */
    --spacing-lg: 1.5rem;   /* 24px */
    --spacing-xl: 2rem;     /* 32px */
}

/* On mobile, reduce spacing */
@media (max-width: 479px) {
    .spacing-unit {
        --spacing-lg: 1rem;
        --spacing-xl: 1.5rem;
    }
}
```

---

## Input Optimization

```html
<!-- IMPORTANT: Set font-size to 16px to prevent iOS zoom -->
<input type="text" style="font-size: 16px;">
<input type="email" style="font-size: 16px;">
<input type="tel" style="font-size: 16px;">

<!-- Use type attribute correctly -->
<input type="email">    <!-- Shows email keyboard -->
<input type="tel">      <!-- Shows phone keyboard -->
<input type="number">   <!-- Shows number keyboard -->
<input type="search">   <!-- Shows search keyboard -->
```

---

## Preventing Common Mobile Issues

### iOS Zoom on Input Focus
```css
input, textarea, select {
    font-size: 16px !important; /* Prevents auto-zoom */
}
```

### Double-Tap Zoom
```css
button, a, input[type="button"], input[type="submit"] {
    touch-action: manipulation; /* Prevents double-tap zoom */
}
```

### Overflow Issues
```css
html, body {
    width: 100%;
    overflow-x: hidden; /* Prevents horizontal scroll */
}
```

### Modal Body Scroll
```css
body.modal-open {
    overflow: hidden; /* Prevent background scroll */
}
```

---

## Media Query Patterns

### Existing Devices
```css
/* iPhone SE (375px) */
@media (max-width: 479px) { }

/* iPhone 12/13 (390px) */
@media (max-width: 479px) { }

/* iPad Mini (768px) */
@media (min-width: 640px) and (max-width: 1024px) { }

/* iPad Air (820px) */
@media (min-width: 768px) and (max-width: 1024px) { }
```

### Responsive Columns
```css
/* Single column on mobile */
.col {
    flex: 0 0 100%;
    max-width: 100%;
}

/* Two columns on tablet */
@media (min-width: 640px) {
    .col {
        flex: 0 0 50%;
        max-width: 50%;
    }
}

/* Three columns on desktop */
@media (min-width: 1025px) {
    .col {
        flex: 0 0 33.333%;
        max-width: 33.333%;
    }
}
```

---

## Testing Locally

### Chrome DevTools
```
1. Open DevTools (F12)
2. Click device toolbar icon (Ctrl+Shift+M)
3. Select device from dropdown
4. Use network throttling
5. Simulate touch with mouse
```

### Test URLs
```
http://localhost:5000                    (Desktop)
http://localhost:5000?mobile=true        (Force mobile)
```

### Quick Mobile Debug
```javascript
// In DevTools console
console.log('Viewport:', window.innerWidth, window.innerHeight);
console.log('Touch capable:', navigator.maxTouchPoints > 0);
console.log('Device pixel ratio:', window.devicePixelRatio);
```

---

## Files to Know

| File | Purpose |
|------|---------|
| `/static/css/mobile-responsive.css` | Mobile-first responsive styles |
| `/static/js/mobile-optimizations.js` | Mobile interaction handlers |
| `/templates/layout.html` | Base template (includes mobile CSS/JS) |
| `MOBILE_RESPONSIVE_DOCUMENTATION.md` | Full documentation |
| `MOBILE_RESPONSIVE_QUICK_REFERENCE.md` | This file |

---

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Text too small | Font size not responsive | Use media queries to scale fonts |
| Buttons too small | Min-height < 44px | Add `min-height: 44px` |
| Content cut off | Fixed width container | Use `width: 100%; max-width: XXX` |
| Horizontal scroll | Element wider than viewport | Check for overflow, use `overflow-x: hidden` |
| Input zoom | Font size < 16px | Set `font-size: 16px` on inputs |
| Modal off-screen | Fixed positioning | Use viewport-relative positioning |
| Navbar hides content | Sticky positioning issue | Adjust `margin-top` or use `padding-top` |
| Images distorted | No aspect ratio | Use `aspect-ratio` or `max-width: 100%` |
| Touch lag | Too many animations | Reduce animation count, use `will-change` |
| Form validation unclear | No visual feedback | Add focus states and error highlighting |

---

## Performance Tips

```css
/* Good: Uses transform for smooth animation */
.animate {
    transition: transform 0.3s ease;
    transform: translateX(0);
}

.animate:active {
    transform: translateX(-5px);
}

/* Bad: Changes dimensions (causes reflow) */
.animate {
    transition: width 0.3s ease;
    width: 100px;
}

.animate:active {
    width: 95px;
}
```

---

## Accessibility Reminders

```html
<!-- DO: Semantic HTML with proper contrast -->
<button class="btn">Click me</button>
<label for="email">Email:</label>
<input id="email" type="email">

<!-- DON'T: Non-semantic divs without labels -->
<div onclick="doSomething()">Click me</div>
<input type="text" placeholder="Email">
```

---

## Getting Help

1. Check `MOBILE_RESPONSIVE_DOCUMENTATION.md` for detailed info
2. Test with Chrome DevTools mobile emulation
3. Test on actual device if possible
4. Check breakpoint-specific CSS
5. Verify touch targets are 44x44px minimum
6. Confirm font sizes are responsive

---

## Version: 1.0
Last Updated: 2025-12-26
