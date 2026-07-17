# Block 4.3 — Accessibility (`a11y`), Mobile Keyboard Overlap, & `.HEIC` OOM Leak Hardening

**Parent plan**: [`../imp_part_2.md`](../imp_part_2.md) Section 5 Stage 4 Block 4.3
**Model specced**: Sonnet 5 | **Thinking specced**: Medium
**Status**: ⬜ Not started

---

## 1. Goal

Ensure full screen reader accessibility, WCAG 2.1 AA color contrast compliance, mobile virtual keyboard safety, and iOS Safari memory management across all user-facing flows:
1. Add `aria-live` screen reader notifications to `/results` during real-time diagnostic generation.
2. Trap and restore keyboard focus when opening/closing modals (`ScanModeModal`, `DoorJambScanModal`).
3. Boost selected OBD-II code pill contrast on dark mode (`ObdCodePicker.tsx`).
4. Prevent mobile virtual keyboards from obscuring the `ChatPanel.tsx` input box.
5. Revoke `.HEIC` image `ObjectURL` references on unmount (`app/diagnose/page.tsx`) to prevent iOS Safari out-of-memory (OOM) crashes.
6. Provide clear browser recovery instructions when camera access is denied (`useCameraStream.ts`).

---

## 2. Exactly what to change

### Step 1: Add `aria-live` region in `frontend/src/app/results/page.tsx`

Locate the container for the free diagnosis summary card (`<div className="card" data-testid="free-diagnosis-summary">` around line 430) and add `aria-live="polite"` and `aria-atomic="true"`:

```tsx
<div
  className="card"
  data-testid="free-diagnosis-summary"
  aria-live="polite"
  aria-atomic="true"
>
```

### Step 2: Trap and restore modal focus (`ScanModeModal.tsx` & `DoorJambScanModal.tsx`)

In both `frontend/src/app/ScanModeModal.tsx` and `frontend/src/app/DoorJambScanModal.tsx`, add a `useEffect` hook that stores the element that had focus when the modal mounted and restores focus to it when the modal unmounts or closes:

```typescript
useEffect(() => {
  const previousActiveElement = document.activeElement as HTMLElement | null;
  return () => {
    if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
      previousActiveElement.focus();
    }
  };
}, []);
```

### Step 3: Fix low-contrast selected OBD code pills (`ObdCodePicker.tsx`)

In `frontend/src/app/diagnose/ObdCodePicker.tsx`, update the inline styles or CSS class of selected code buttons so the foreground color is high-contrast `#93c5fd` (`blue-300`) with `fontWeight: 600`:

```diff
   <button
     key={code.code}
     type="button"
     onClick={() => onSelect(code)}
     style={{
       padding: '6px 12px',
       borderRadius: 16,
       border: isSelected ? '1px solid #3b82f6' : '1px solid var(--border-color)',
-      backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--card-bg)',
+      backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.25)' : 'var(--card-bg)',
-      color: isSelected ? '#60a5fa' : 'var(--text-primary)',
+      color: isSelected ? '#93c5fd' : 'var(--text-primary)',
+      fontWeight: isSelected ? 600 : 400,
       cursor: 'pointer',
     }}
   >
```

### Step 4: Fix virtual keyboard overlap on mobile (`ChatPanel.tsx`)

In `frontend/src/app/repair/ChatPanel.tsx`, update `.repair-chat-panel.chat-drawer-open` styling (either inline or in `globals.css`) so the drawer respects iOS `env(safe-area-inset-bottom)` and the visual keyboard viewport height:

If in CSS (`globals.css` or scoped):
```css
.repair-chat-panel.chat-drawer-open {
  bottom: env(keyboard-inset-height, 0px);
  max-height: calc(85vh - env(keyboard-inset-height, 0px));
}
```

Or add a visual viewport listener inside `ChatPanel`:
```typescript
useEffect(() => {
  if (typeof window === 'undefined' || !window.visualViewport) return;
  const handleResize = () => {
    const drawer = document.querySelector('.repair-chat-panel.chat-drawer-open') as HTMLElement | null;
    if (drawer && window.visualViewport) {
      const offset = window.innerHeight - window.visualViewport.height;
      drawer.style.bottom = offset > 0 ? `${offset}px` : '0px';
    }
  };
  window.visualViewport.addEventListener('resize', handleResize);
  return () => window.visualViewport?.removeEventListener('resize', handleResize);
}, [drawerOpen]);
```

### Step 5: Prevent `.HEIC` ObjectURL memory leaks (`app/diagnose/page.tsx`)

In `frontend/src/app/diagnose/page.tsx`, add a cleanup `useEffect` that revokes all active `ObjectURL` strings when `DiagnosePage` unmounts or when `photoPreviews` changes:

```typescript
useEffect(() => {
  return () => {
    photoPreviews.forEach((p) => {
      if (p.url && p.url.startsWith('blob:')) {
        URL.revokeObjectURL(p.url);
      }
    });
  };
}, [photoPreviews]);
```

And when removing a single preview from `photoPreviews`:
```typescript
const removePhotoPreview = (urlToRemove: string) => {
  if (urlToRemove.startsWith('blob:')) URL.revokeObjectURL(urlToRemove);
  setPhotoPreviews((prev) => prev.filter((p) => p.url !== urlToRemove));
};
```

### Step 6: Surface camera `NotAllowedError` recovery instructions (`useCameraStream.ts`)

In `frontend/src/lib/useCameraStream.ts`, when catching `getUserMedia` errors (around line 30-45):

```diff
       } catch (err: unknown) {
         if (!active) return;
         const name = err instanceof Error ? err.name : 'UnknownError';
+        if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
+          setError('Camera access denied. Please tap the lock/aA icon in your browser address bar, enable Camera permissions for this site, and refresh.');
+        } else if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
+          setError('No camera detected on this device.');
+        } else {
-          setError(err instanceof Error ? err.message : 'Could not access camera.');
+          setError('Could not access camera. Please check your browser permissions.');
+        }
         setStatus('error');
       }
```

---

## 3. Verification

Run the exact check below from repository root before committing:

```bash
cd frontend && ./node_modules/.bin/next build
```

**Expected output**:
- `✓ Compiled successfully`
- Zero TypeScript (`TS2304` / `TS2322`) errors and zero ESLint errors.
