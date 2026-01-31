package com.familyeye.agent.utils

import android.accounts.AccountManager
import android.content.Context
import timber.log.Timber

/**
 * Helper for managing Google accounts on the device.
 * Used during Device Owner provisioning (accounts must be removed first).
 */
object AccountHelper {
    
    /**
     * Get all Google accounts on the device.
     */
    fun getGoogleAccounts(context: Context): List<String> {
        return try {
            val accountManager = AccountManager.get(context)
            accountManager.getAccountsByType("com.google")
                .map { it.name }
        } catch (e: Exception) {
            Timber.e(e, "Failed to get Google accounts")
            emptyList()
        }
    }
    
    /**
     * Check if device has any Google accounts.
     */
    fun hasAccounts(context: Context): Boolean {
        return getGoogleAccounts(context).isNotEmpty()
    }
    
    /**
     * Get count of Google accounts.
     */
    fun getAccountCount(context: Context): Int {
        return getGoogleAccounts(context).size
    }
}
