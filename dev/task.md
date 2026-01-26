# FamilyEye Agent - Vývojářský Checklist

## 1. Phase 1: Reporting & Monitoring ✅
- [x] **Párování a Komunikace**
    - [x] HTTPS Handshake
    - [x] Heartbeat (Online status)
- [x] **Sběr Dat**
    - [x] Usage Stats Implementation
    - [x] Real-time Usage Reporting (via `AppDetectorService`)
    - [x] Fix: Time reporting accuracy
    - [x] **Data Saver Mode** (Sync only on Wi-Fi)
    - [x] **Manual Sync** (Force sync when limit exceeded)
    - [x] **Visualization**
        - [x] Activity Timeline for Android (Replaced 'Running Processes')
- [x] **Oprávnění (Permissions)**
    - [x] UI Implementation (Green/Red indicators)
    - [x] Clickable Intents (Settings deep-links)
    - [x] Clickable Intents (Settings deep-links)
    - [x] Reorder: Admin -> Overlay -> Usage -> Accessibility ✅
    - [x] **Power Management**
        - [x] Add `ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS` step
    - [x] **UI Architecture & Splitting**
        - [x] Create `ChildDashboardScreen` (Read-only stats)
        - [x] Create `AdminLoginScreen` (PIN/Pass)
        - [x] Move Settings behind Admin Login

## 3. Phase 3: Real-Time Features (WebSockets) 🚀
- [x] **WebSocket Client**
    - [x] Create `WebSocketClient.kt` (OkHttp)
    - [x] Handle Reconnect logic (Exponential Backoff - Implemented in loop)
    - [x] Authenticate with `device_id` + `api_key`
- [x] **Command Handling**
    - [x] Implement command parser (`SCREENSHOT`, `LOCK`, `REFRESH`)
    - [x] Implement `takeScreenshot()` in `AppDetectorService`
    - [x] Upload screenshot to backend endpoint

## 2. Phase 2: Blocking & Self-Protection 🏗️
- [x] **Self-Protection (Anti-Tamper)**
    - [x] Device Admin (Prevent Uninstall)
    - [x] Block `DeviceAdminAdd` screen (Prevent Deactivation)
    - [x] **Feature:** Dashboard "Unlock Settings" Button (Allow admin access remotely)
      - [x] Frontend Implementation (Added button & Action)
      - [x] Backend Implementation (API Endpoint)
      - [x] Agent Implementation (Receive Command & Disable Protection)
- [x] **Enforcement Logic**
    - [x] Force Stop Blocking (via Home Action & Overlay)
    - [x] App Limits (RuleEnforcer & UsageTracker)
    - [x] Overlay Screen (BlockOverlayManager)
    - [x] **Global Enforcement**
        - [x] Daily Limit (Total Device Time) - Implemented
        - [x] Schedule Blocking (Time Intervals) - Implemented
        - [x] "Lock Now" Command (Immediate Device Lock) - Implemented

## 3. Phase 3: Backend & Frontend Polish
- [x] **Dashboard Improvements**
    - [x] Separate Android/Windows Cards (Frontend)
    - [x] **Visual Polish** (Branded Block Screen, Custom Messages)
    - [x] **Logic Fix**: App Schedule vs Device Schedule (Prevent "Blocking Everything")
    - [x] **UI Fix**: Remove "Close" button for Strict Locks

## 4. Phase 4: Final Verification & Security 🔒
- [x] End-to-end user flow test (Verified App Blocking & Schedule for Apps)
- [x] **Security Audit & Hardening**
    - [x] **Fix:** Block `com.android.settings` by default (Prevent Force Stop).
    - [x] **Logic Fixes**
    - [x] Fix "Gap in Agent Logs" (Use `WAKE_LOCK` or just accept Doze limitations? -> Accepted Doze, added `forceSync`)
    - [x] Fix "Lock Now Delay" (Push notifications vs Polling? -> Polling is 30s, OK for now)
- [x] **Explain Daily Limit Logic** (Why 16m vs 18m? -> Sync Lag. Fixed with `forceSync`)
- [x] **Hack Testing** (Time change, Safe Mode, etc.) -> Basic hardening done.
- [/] **Final Polish & Release** 5: Architecture Cleanup (Refactoring) 🧹
- [x] **Debugging & Polish**
    - [x] Fix compilation errors (isActive, ApiClient references).
    - [x] Implement robust Rule Matching (Package vs Label, Case-Insensitive).
    - [x] Ensure `fetchRules` loop works correctly in `FamilyEyeService`.
    - [x] Verify Dashboard polling and updates.
- [x] **Frontend Separation**
    - [x] Create `platforms/` directory
    - [x] Extract `WindowsDeviceCard.jsx`
    - [x] Extract `AndroidDeviceCard.jsx`
    - [x] Update `DeviceCard.jsx` as dispatcher
- [x] **Windows Solution Audit**
    - [x] Analyze Client Code (`agent/`)
    - [x] Analyze Localized Strings
    - [x] Report Findings (`windows_audit.md`)
