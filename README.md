# 3D Image Ring

A draggable 3D image carousel built with React, TypeScript, Framer Motion, and CSS 3D transforms.

## Features

- Circular 3D image layout
- Mouse and touch dragging
- Inertia-based snapping
- Responsive mobile scaling
- Hover focus effect
- Customizable sizing, perspective, spacing, and animation timing

## Installation

```bash
npm install framer-motion clsx tailwind-merge
```

## Usage

```tsx
import { ThreeDImageRing } from "./src";

const images = [
  "https://images.pexels.com/photos/1704120/pexels-photo-1704120.jpeg?auto=compress&cs=tinysrgb&w=1200",
  "https://images.pexels.com/photos/1103970/pexels-photo-1103970.jpeg?auto=compress&cs=tinysrgb&w=1200",
  "https://images.pexels.com/photos/2387873/pexels-photo-2387873.jpeg?auto=compress&cs=tinysrgb&w=1200",
  "https://images.pexels.com/photos/912110/pexels-photo-912110.jpeg?auto=compress&cs=tinysrgb&w=1200",
  "https://images.pexels.com/photos/325185/pexels-photo-325185.jpeg?auto=compress&cs=tinysrgb&w=1200",
];

export function Example() {
  return (
    <div className="h-screen w-full bg-black">
      <ThreeDImageRing images={images} />
    </div>
  );
}
```

## Props

| Prop | Type | Default | Description |
| --- | --- | --- | --- |
| `images` | `string[]` | Default image set | Image URLs displayed in the ring |
| `width` | `number` | `300` | Image panel width in pixels |
| `perspective` | `number` | `2000` | CSS 3D perspective value |
| `imageDistance` | `number` | `500` | Distance from the center of the ring |
| `initialRotation` | `number` | `180` | Initial Y-axis rotation |
| `animationDuration` | `number` | `1.5` | Entrance animation duration |
| `staggerDelay` | `number` | `0.1` | Delay between image entrance animations |
| `hoverOpacity` | `number` | `0.5` | Opacity applied to non-hovered images |
| `containerClassName` | `string` | `undefined` | Extra classes for the outer container |
| `ringClassName` | `string` | `undefined` | Extra classes for the ring element |
| `imageClassName` | `string` | `undefined` | Extra classes for each image panel |
| `backgroundColor` | `string` | `undefined` | Optional container background color |
| `draggable` | `boolean` | `true` | Enables mouse and touch dragging |
| `mobileBreakpoint` | `number` | `768` | Viewport width where mobile scaling starts |
| `mobileScaleFactor` | `number` | `0.8` | Scale used below the mobile breakpoint |
| `inertiaPower` | `number` | `0.8` | Framer Motion inertia power |
| `inertiaTimeConstant` | `number` | `300` | Framer Motion inertia time constant |
| `inertiaVelocityMultiplier` | `number` | `20` | Multiplier applied to drag velocity |

## Development

This repository currently contains the reusable component source. A demo app and automated tests are good next improvements before publishing or showcasing it in a portfolio.

## License

MIT
