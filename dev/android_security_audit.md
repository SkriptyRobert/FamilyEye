# Android Agent Security Audit

## Audit Target
**Component:** Android Agent (Client)
**Version:** Current (Dev)
**Focus:** Bypass prevention, blocking robustness, "Bulletproof" status.

## 1. Bypass Vectors & Mitigation Status

### A. Notification Shade / Quick Settings
**Vulnerability:** User can pull down status bar (`com.android.systemui`) to access Quick Settings (e.g., disable Wi-Fi/Data) or enter "Settings" via the cog.
**Current Status:** `com.android.systemui` is whitelisted to prevent UI crashes.
**Mitigation Plan:**
- When `isDeviceLocked()` (Brick Mode) is active, detect `com.android.systemui` focus.
- Instead of blocking (overlay), trigger `performGlobalAction(GLOBAL_ACTION_BACK)` or `GLOBAL_ACTION_COLLAPSE_STATUS_BAR` (if permissions allow/API level).
- **Result:** Keeps the shade closed.

### B. Split Screen / Multi-Window
**Vulnerability:** If blocking relies strictly on the "Top Focused App", a smart child might open a trusted app (e.g. Calculator) on top and the blocked app (YouTube) on bottom.
**Current Status:** `AppDetectorService` tracks `event.packageName` (usually focused window).
**Mitigation Plan:**
- Enable `canRetrieveWindowContent` (or `retrieveInteractiveWindows`) in Accessibility Config.
- In `AppDetectorService`, iterate through `accessibilityService.windows`.
- If *ANY* visible window matches a blocked package, trigger the block.

### C. Overlay "Touch Passthrough"
**Vulnerability:** `BlockOverlayManager` currently uses `FLAG_NOT_TOUCH_MODAL`.
- This technically allows touches outside the view bounds (if any) to pass through.
- Even if full screen, it allows the system to treat the window as "non-modal", potentially allowing gestures or status bar interaction.
**Mitigation Plan:**
- **Remove** `FLAG_NOT_TOUCH_MODAL`.
- Ensure `MATCH_PARENT` is strict.
- Add `FLAG_LAYOUT_NO_LIMITS` to draw behind status bars (making it harder to interact).

### D. Safe Mode
**Vulnerability:** Rebooting into Safe Mode disables third-party apps (including Agent).
**Current Status:** Standard Android limitation. Admin apps are usually disabled.
**Mitigation:**
- **Admin Persistence:** Device Admin *should* persist, but Safe Mode disables the *service*.
- **Detection:** Agent can detect if it was just rebooted? Hard to block Safe Mode itself without MDM/Knox.
- **Acceptable Risk:** Safe Mode usually has no network or limited apps. If they play offline games, we can't stop Safe Mode easily without Root/OEM signature.

### E. "Force Stop" Race Condition
**Vulnerability:** Child drags status bar -> Settings -> Apps -> Agent -> Force Stop (very fast).
**Current Status:** `com.android.settings` is whitelisted?
- NO, `com.android.settings` is detected.
- If they open Settings, we block it (unless whitelisted).
- **Wait:** `AppDetectorService.kt` currently whitelists `com.android.settings` in `isWhitelisted`.
- **CRITICAL:** If Settings is whitelisted, they CAN Force Stop the agent!
**Mitigation Plan:**
- **Remove** `com.android.settings` from whitelist!
- OR, block it *unless* "Unlock Settings" is active.
- Currently, `BlockOverlayManager` hides if whitelisted.
- **Fix:** Remove Settings from whitelist. Only allow if `ruleEnforcer.isUnlockSettingsActive()`.

## 2. Recommendation Checklist

1. [ ] **Critical:** Update `AppDetectorService` to **BLOCK Settings** by default (allow only via `isUnlockSettingsActive`).
2. [ ] **High:** Update `AppDetectorService` to auto-close Status Bar (`GLOBAL_ACTION_BACK`) when locked.
3. [ ] **High:** Update `BlockOverlayManager` to remove `FLAG_NOT_TOUCH_MODAL` (make it modal).
4. [ ] **Medium:** Iterate `windows` for split-screen robustness.
