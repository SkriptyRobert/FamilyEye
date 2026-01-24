# Walkthrough - v1.0.13: Ultimate Restart Reliability

## Problem
On aggressive custom Android skins (like MIUI, EMUI), the system kills apps and blocks standard `AlarmManager` intents when the user swipes the app away from recents. The previous "Dual Alarm" strategy was insufficient because the OS cancelled the alarms immediately.

## Solution: The "Triple Threat" Strategy
We introduced a third, system-managed layer of persistence: **WorkManager**.

### Strategy Layers
1.  **Primary Alarm (100ms)**: Fast restart via `RestartReceiver`. (Often blocked by MIUI)
2.  **Backup Alarm (3000ms)**: Delayed restart via `KeepAliveActivity`. (Often blocked by MIUI)
3.  **WorkManager (Expedited)**: **[NEW]** A high-priority system job that the OS schedule manager is obligated to run. Even if the app process is killed, the WorkManager job persists and will restart the service as soon as the system allows (usually within seconds or minutes).

```kotlin
// FamilyEyeService.kt - onTaskRemoved
val restartWork = OneTimeWorkRequest.Builder(RestartWorker::class.java)
    .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
    .addTag("restart_service")
    .build()

WorkManager.getInstance(applicationContext).enqueue(restartWork)
```

## Files Changed
| File | Change |
|------|--------|
| [RestartWorker.kt](file:///c:/Users/Administrator/Documents/Cursor/Parential-Control_Enterprise/clients/android/app/src/main/java/com/familyeye/agent/service/RestartWorker.kt) | New worker to start the service from background. |
| [FamilyEyeService.kt](file:///c:/Users/Administrator/Documents/Cursor/Parential-Control_Enterprise/clients/android/app/src/main/java/com/familyeye/agent/service/FamilyEyeService.kt) | Added WorkManager scheduling to `onTaskRemoved`. |
| [AndroidManifest.xml](file:///c:/Users/Administrator/Documents/Cursor/Parential-Control_Enterprise/clients/android/app/src/main/AndroidManifest.xml) | Verified receiver registrations. |

## Expected Behavior
- When swiped away, the app may seem "dead" for a few seconds if alarms fail.
- **BUT**, shortly after, the WorkManager job will kick in and revive the service.
- The persistent notification should reappear automatically.
