package com.familyeye.agent.service

import android.content.Context
import androidx.work.Worker
import androidx.work.WorkerParameters
import timber.log.Timber

/**
 * Worker that restarts the FamilyEyeService.
 * Used as a backup mechanism when AlarmManager fails (e.g. on aggressive battery optimization).
 * WorkManager jobs are persistent and harder for the OS to kill completely.
 */
class RestartWorker(
    context: Context,
    workerParams: WorkerParameters
) : Worker(context, workerParams) {

    override fun doWork(): Result {
        Timber.i("RestartWorker executing - attempting to revive FamilyEyeService")
        
        try {
            FamilyEyeService.start(applicationContext)
            Timber.i("FamilyEyeService restart initiated from Worker")
            return Result.success()
        } catch (e: Exception) {
            Timber.e(e, "RestartWorker failed to start service")
            return Result.retry()
        }
    }
}
