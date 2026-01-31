package com.familyeye.agent.utils

import android.content.Context
import android.content.pm.PackageManager
import timber.log.Timber

/**
 * Centralized app information resolver with caching.
 * 
 * This utility provides consistent app name resolution across the codebase
 * and includes an in-memory cache to avoid repeated PackageManager queries.
 */
object AppInfoResolver {

    // Simple LRU-style cache for app names (thread-safe)
    private val appNameCache = LinkedHashMap<String, String>(100, 0.75f, true)
    private const val MAX_CACHE_SIZE = 200

    /**
     * Get the human-readable app name for a package.
     * Results are cached to avoid repeated PackageManager queries.
     * 
     * @param context Android context for accessing PackageManager
     * @param packageName The package name to resolve
     * @return Human-readable app name, or simplified package name as fallback
     */
    @Synchronized
    fun getAppName(context: Context, packageName: String): String {
        // Check cache first
        appNameCache[packageName]?.let { return it }

        val appName = try {
            val packageManager = context.packageManager
            val info = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            Timber.v("Package not found: $packageName, using fallback")
            extractSimpleName(packageName)
        } catch (e: Exception) {
            Timber.w(e, "Error resolving app name for $packageName")
            extractSimpleName(packageName)
        }

        // Add to cache (with size limit)
        if (appNameCache.size >= MAX_CACHE_SIZE) {
            // Remove oldest entry
            val iterator = appNameCache.iterator()
            if (iterator.hasNext()) {
                iterator.next()
                iterator.remove()
            }
        }
        appNameCache[packageName] = appName

        return appName
    }

    /**
     * Extract a simplified name from a package name.
     * Takes the last segment of the package name.
     * 
     * @param packageName The full package name
     * @return Last segment of the package name (e.g., "chrome" from "com.android.chrome")
     */
    fun extractSimpleName(packageName: String): String {
        return packageName.split(".").lastOrNull() ?: packageName
    }

    /**
     * Clear the app name cache.
     * Useful when apps are installed/uninstalled.
     */
    @Synchronized
    fun clearCache() {
        appNameCache.clear()
    }

    /**
     * Remove a specific package from the cache.
     * Useful when a specific app is updated/uninstalled.
     * 
     * @param packageName The package to remove from cache
     */
    @Synchronized
    fun invalidateCache(packageName: String) {
        appNameCache.remove(packageName)
    }

    /**
     * Check if an app is installed on the device.
     * 
     * @param context Android context
     * @param packageName Package name to check
     * @return true if the app is installed
     */
    fun isAppInstalled(context: Context, packageName: String): Boolean {
        return try {
            context.packageManager.getApplicationInfo(packageName, 0)
            true
        } catch (e: PackageManager.NameNotFoundException) {
            false
        }
    }

    /**
     * Get the app icon drawable for a package.
     * 
     * @param context Android context
     * @param packageName Package name
     * @return App icon drawable, or null if not found
     */
    fun getAppIcon(context: Context, packageName: String): android.graphics.drawable.Drawable? {
        return try {
            context.packageManager.getApplicationIcon(packageName)
        } catch (e: PackageManager.NameNotFoundException) {
            null
        }
    }
}
