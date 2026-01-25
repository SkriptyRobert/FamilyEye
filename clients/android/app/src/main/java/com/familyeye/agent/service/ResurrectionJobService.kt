package com.familyeye.agent.service

import android.app.job.JobInfo
import android.app.job.JobParameters
import android.app.job.JobScheduler
import android.app.job.JobService
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import timber.log.Timber

/**
 * A JobService that acts as a "Third Layer" of persistence.
 * 
 * Unlike standard Services, JobServices are managed by the system job scheduler (system_server).
 * Even if the app process is killed by "Clear All", the scheduled job remains in the system registry
 * and will be executed by the system when constraints are met.
 * 
 * This is crucial for Chinese ROMs (Xiaomi/Huawei) where background services are aggressively killed.
 */
class ResurrectionJobService : JobService() {

    companion object {
        private const val JOB_ID = 777
        
        fun schedule(context: Context) {
            val componentName = ComponentName(context, ResurrectionJobService::class.java)
            val scheduler = context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler

            // Check if already scheduled
             if (isJobScheduled(scheduler, JOB_ID)) {
                Timber.d("ResurrectionJob already scheduled")
                return
            }

            val builder = JobInfo.Builder(JOB_ID, componentName)
                .setPersisted(true) // Survives reboot
                .setRequiresCharging(false)
                .setRequiresDeviceIdle(false)
                
            // Android N+ forces a minimum period of 15 minutes.
            // But checking every 15 mins is better than dead forever.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                builder.setPeriodic(15 * 60 * 1000L) // 15 minutes
            } else {
                builder.setPeriodic(5 * 60 * 1000L) // 5 minutes on older OS
            }

            val result = scheduler.schedule(builder.build())
            if (result == JobScheduler.RESULT_SUCCESS) {
                Timber.i("ResurrectionJob scheduled successfully")
            } else {
                Timber.e("Failed to schedule ResurrectionJob")
            }
        }
        
        private fun isJobScheduled(scheduler: JobScheduler, id: Int): Boolean {
            return try {
                scheduler.getPendingJob(id) != null
            } catch (e: Exception) {
                false
            }
        }
    }

    override fun onStartJob(params: JobParameters?): Boolean {
        Timber.i("ResurrectionJob triggered - Checking generic health")
        
        // Attempt to start the main service
        try {
            FamilyEyeService.start(applicationContext)
        } catch (e: Exception) {
            Timber.e(e, "Job failed to restart service")
        }
        
        // Return false because we don't have any async work (service start is fire-and-forget)
        return false 
    }

    override fun onStopJob(params: JobParameters?): Boolean {
        // Return true to reschedule if we were interrupted
        return true
    }
}
