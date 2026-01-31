package com.familyeye.agent

import android.app.Application
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import dagger.hilt.android.HiltAndroidApp
import timber.log.Timber
import javax.inject.Inject

/**
 * Main Application class for FamilyEye Android Agent.
 * Initializes Hilt dependency injection and Timber logging.
 */
@HiltAndroidApp
class FamilyEyeApp : Application(), Configuration.Provider {

    @Inject
    lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        
        // Initialize Timber for logging
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        } else {
            // In production, could plant a crash reporting tree
            Timber.plant(ReleaseTree())
        }
        
        Timber.d("FamilyEye Agent initialized")
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .setMinimumLoggingLevel(if (BuildConfig.DEBUG) android.util.Log.DEBUG else android.util.Log.INFO)
            .build()

    /**
     * Release tree that filters out debug/verbose logs
     */
    private class ReleaseTree : Timber.Tree() {
        override fun log(priority: Int, tag: String?, message: String, t: Throwable?) {
            if (priority >= android.util.Log.INFO) {
                // Here you could send to Crashlytics or other crash reporting
                android.util.Log.println(priority, tag ?: "FamilyEye", message)
            }
        }
    }
}
