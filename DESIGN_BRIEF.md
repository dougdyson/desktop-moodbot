# Founder Edition - Design Brief
**Project: Desktop MoodBot Sprites**

This document codifies the art direction and generation rules for the initial "Founder Edition" mascot characters based on our initial prototyping phase.

## 1. Physical Canvas & Borders
- **The canvas IS the face:** The 200x200 image frame represents the absolute boundary of the face. 
- **No drawn perimeter:** Sprites must *not* contain an enclosing stroked circle or square. The physical hardware's circular bezel acts as the natural border for the face.
- **Centering & Scale:** Facial features should be large, bold, and centered to maximize readability from across a desk.

## 2. Technical Art Style
- **Pure 1-Bit:** Images must translate flawlessly to pure black and white. No grayscale, no shading, no anti-aliasing.
- **Line Art constraints:** Lines must be thick, bold, and use high-contrast geometric shapes.
- **White Background:** The background must always remain negative space (pure white) with black line art acting as the active pixel space (e-ink black).

## 3. The "Consistent Eye" Rule (Core Rule)
Our most important learning: **A single character must possess a distinct, mathematically consistent eye style across all 73 animation states.**

In our initial generation pass, we mistakenly allowed the AI to drift between different eye topologies (e.g., solid circles, hollow ovals, "pac-man" shapes, and detached pupils). 

**Founder Edition eyes must adhere to the following:**
- **Base Topology:** The official base eye topology is **"Solid black tall ovals (like classic vintage cartoons with no pupils)"**.
- **State Modifications:** When emotions require eye changes (e.g., squinting, winking, sleeping), they must be *transformations* of the base topology, not entirely new art styles. (e.g., A solid tall oval becomes a flattened oval when squinting).
- **Proportions:** The distance between the eyes and their relative size to the mouth must remain anchored to prevent the character from feeling like a completely different mascot between states.

## 4. Activities via Gestures
Activities should be primarily communicated via simple, thick-lined hands entering the frame, or bold simplistic props near the top/sides of the face.
- **Thinking:** Hand on chin, thought bubbles, lightbulbs.
- **Conversing:** Open mouths, outward hand gestures, speech bubbles.
- **Reading:** Squinting focus, hands holding a book edge, glasses.

## Next Steps for Generation
When the AI image generation rate limits reset, we will:
1. Define the *exact* base topology for the Founder Edition character (e.g., Solid Oval Eyes vs. Retro Pac-Man Eyes).
2. Generate all 33 priority sprites anchoring heavily to that specific visual seed.
3. Run them through our Python 1-bit thresholding tool.
