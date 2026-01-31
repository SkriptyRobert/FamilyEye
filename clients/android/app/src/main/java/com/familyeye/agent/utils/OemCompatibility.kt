package com.familyeye.agent.utils

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import timber.log.Timber

/**
 * Handles OEM-specific compatibility issues.
 * 
 * Many Chinese OEMs (Xiaomi, Huawei, Oppo, Vivo) and Samsung have aggressive
 * battery management that can kill background apps even with proper foreground
 * services. This utility helps work around these issues.
 */
object OemCompatibility {

    /**
     * List of manufacturers known for aggressive battery management.
     */
    private val AGGRESSIVE_OEMS = listOf(
        "xiaomi", "redmi", "poco",  // Xiaomi group
        "huawei", "honor",          // Huawei group
        "oppo", "realme", "oneplus", // BBK group
        "vivo",
        "samsung",
        "meizu",
        "asus",
        "lenovo"
    )

    /**
     * Check if device is from an OEM known for aggressive battery management.
     */
    fun isAggressiveOem(): Boolean {
        val manufacturer = Build.MANUFACTURER.lowercase()
        return AGGRESSIVE_OEMS.any { manufacturer.contains(it) }
    }
    
    /**
     * Alias for isAggressiveOem() - used by UI components.
     */
    fun isAggressiveBatteryManagement(): Boolean = isAggressiveOem()

    /**
     * Check if the app is already ignoring battery optimizations (whitelisted).
     */
    fun isIgnoringBatteryOptimizations(context: Context): Boolean {
        val powerManager = context.getSystemService(Context.POWER_SERVICE) as? android.os.PowerManager
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            powerManager?.isIgnoringBatteryOptimizations(context.packageName) ?: true
        } else {
            true
        }
    }

    /**
     * Get the manufacturer name for logging/display.
     */
    fun getManufacturer(): String = Build.MANUFACTURER

    /**
     * Attempt to open the AutoStart/Protected Apps settings for the current OEM.
     * This is a best-effort approach - settings locations vary by OEM and ROM version.
     * 
     * @return true if an intent was launched, false if no matching intent found
     */
    fun openAutoStartSettings(context: Context): Boolean {
        val manufacturer = Build.MANUFACTURER.lowercase()
        
        val intents = getAutoStartIntents(manufacturer)
        
        for (intent in intents) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                Timber.i("Opened AutoStart settings for $manufacturer")
                return true
            } catch (e: Exception) {
                Timber.d("Intent failed: ${intent.component}")
                // Try next intent
            }
        }
        
        Timber.w("No AutoStart settings found for $manufacturer")
        return false
    }

    /**
     * Get list of possible AutoStart setting intents for the given manufacturer.
     */
    private fun getAutoStartIntents(manufacturer: String): List<Intent> {
        return when {
            manufacturer.contains("xiaomi") || manufacturer.contains("redmi") || manufacturer.contains("poco") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.permcenter.autostart.AutoStartManagementActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.powercenter.PowerSettings"
                ))
            )
            manufacturer.contains("huawei") || manufacturer.contains("honor") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.huawei.systemmanager",
                    "com.huawei.systemmanager.startupmgr.ui.StartupNormalAppListActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.huawei.systemmanager",
                    "com.huawei.systemmanager.optimize.process.ProtectActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.huawei.systemmanager",
                    "com.huawei.systemmanager.appcontrol.activity.StartupAppControlActivity"
                ))
            )
            manufacturer.contains("oppo") || manufacturer.contains("realme") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.coloros.safecenter",
                    "com.coloros.safecenter.permission.startup.StartupAppListActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.coloros.safecenter",
                    "com.coloros.safecenter.startupapp.StartupAppListActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.oppo.safe",
                    "com.oppo.safe.permission.startup.StartupAppListActivity"
                ))
            )
            manufacturer.contains("vivo") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.vivo.permissionmanager",
                    "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.iqoo.secure",
                    "com.iqoo.secure.ui.phoneoptimize.AddWhiteListActivity"
                ))
            )
            manufacturer.contains("samsung") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.samsung.android.lool",
                    "com.samsung.android.sm.ui.battery.BatteryActivity"
                )),
                Intent().setComponent(ComponentName(
                    "com.samsung.android.sm",
                    "com.samsung.android.sm.ui.battery.BatteryActivity"
                ))
            )
            manufacturer.contains("oneplus") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.oneplus.security",
                    "com.oneplus.security.chainlaunch.view.ChainLaunchAppListActivity"
                ))
            )
            manufacturer.contains("asus") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.asus.mobilemanager",
                    "com.asus.mobilemanager.autostart.AutoStartActivity"
                ))
            )
            manufacturer.contains("lenovo") -> listOf(
                Intent().setComponent(ComponentName(
                    "com.lenovo.security",
                    "com.lenovo.security.purebackground.PureBackgroundActivity"
                ))
            )
            else -> emptyList()
        }
    }

    /**
     * Open battery optimization settings to request exemption.
     * Works on all Android 6.0+ devices.
     */
    fun openBatteryOptimizationSettings(context: Context): Boolean {
        return try {
            val intent = Intent(android.provider.Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS)
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(intent)
            true
        } catch (e: Exception) {
            Timber.e(e, "Failed to open battery optimization settings")
            false
        }
    }

    /**
     * Get a user-friendly message about what settings need to be enabled
     * for the agent to work properly on this device.
     */
    fun getSetupInstructions(): String {
        val manufacturer = Build.MANUFACTURER.lowercase()
        
        return when {
            manufacturer.contains("xiaomi") || manufacturer.contains("redmi") || manufacturer.contains("poco") -> 
                "Xiaomi: Povolte 'Automatické spuštění' a nastavte 'Spořič baterie' na 'Žádné omezení' v aplikaci Optimalizace (Zabezpečení)."
            manufacturer.contains("huawei") || manufacturer.contains("honor") ->
                "Huawei: Přidejte aplikaci do 'Chráněných aplikací' a vypněte optimalizaci baterie."
            manufacturer.contains("samsung") ->
                "Samsung: Přidejte aplikaci do výjimek 'Péče o zařízení' > 'Baterie' (Nezakázané aplikace)."
            manufacturer.contains("oppo") || manufacturer.contains("realme") ->
                "OPPO: Povolte 'Automatické spuštění' a přidejte do seznamu povolených aplikací pro baterii."
            else ->
                "Prosím, vypněte optimalizaci baterie pro tuto aplikaci v nastavení systému."
        }
    }
}
