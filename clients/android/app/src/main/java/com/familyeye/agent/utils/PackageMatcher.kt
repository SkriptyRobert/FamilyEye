package com.familyeye.agent.utils

/**
 * Centralized package name matching logic.
 * 
 * This utility eliminates the 3x duplicated matching logic in RuleEnforcer
 * and provides consistent app identification across the codebase.
 */
object PackageMatcher {
    private val SETTINGS_PACKAGES = setOf(
        "com.android.settings",           // AOSP / most OEMs
        "com.miui.securitycenter",         // Xiaomi / MIUI
        "com.huawei.systemmanager",        // Huawei
        "com.samsung.android.lool",        // Samsung Device Care
        "com.oppo.safe",                   // OPPO
        "com.coloros.safecenter",          // ColorOS (OPPO/Realme)
        "com.vivo.permissionmanager",      // Vivo
        "com.iqoo.secure",                 // iQOO
        "com.oneplus.security"             // OnePlus
    )

    /**
     * Check if a package name matches a rule name using multiple strategies:
     * 1. Exact package name match (case-insensitive)
     * 2. Partial package name match (rule name contained in package)
     * 3. App label match (case-insensitive)
     * 
     * @param packageName The actual package name (e.g., "com.android.chrome")
     * @param ruleName The rule's target (can be package name or app label)
     * @param appLabel The display name of the app (e.g., "Chrome")
     * @return true if any matching strategy succeeds
     */
    fun matches(packageName: String, ruleName: String, appLabel: String): Boolean {
        val normRule = normalize(ruleName)
        val normPackage = normalize(packageName)
        val normLabel = normalize(appLabel)

        // 1. Exact package name match (case-insensitive + normalizovaná diakritika)
        if (normRule.equals(normPackage, ignoreCase = true)) {
            return true
        }

        // 2. Partial package name match
        if (normPackage.contains(normRule, ignoreCase = true)) {
            return true
        }

        // 3. App label match
        if (normRule.equals(normLabel, ignoreCase = true)) {
            return true
        }

        return false
    }

    /**
     * Remove accents/diacritics from a string.
     * E.g., "Poznámky" -> "Poznamky"
     */
    private fun normalize(input: String?): String {
        if (input == null) return ""
        val normalized = java.text.Collator.getInstance(java.util.Locale.US).apply {
            strength = java.text.Collator.PRIMARY
        }
        // Simplest way in Kotlin without heavy ICU: Normalizer
        val temp = java.text.Normalizer.normalize(input, java.text.Normalizer.Form.NFD)
        val pattern = java.util.regex.Pattern.compile("\\p{InCombiningDiacriticalMarks}+")
        return pattern.matcher(temp).replaceAll("")
    }

    /**
     * Check if a package name matches any of the provided rule names.
     * 
     * @param packageName The actual package name
     * @param ruleNames List of rule targets to check against
     * @param appLabel The display name of the app
     * @return true if any rule matches
     */
    fun matchesAny(packageName: String, ruleNames: List<String>, appLabel: String): Boolean {
        return ruleNames.any { ruleName ->
            matches(packageName, ruleName, appLabel)
        }
    }

    /**
     * Check if a package belongs to a known launcher.
     * 
     * @param packageName The package name to check
     * @return true if this is a launcher app
     */
    fun isLauncher(packageName: String): Boolean {
        // Common patterns in launcher package names
        if (packageName.contains("launcher", ignoreCase = true)) return true
        if (packageName.contains("home", ignoreCase = true)) return true

        // Well-known launchers by exact package name
        val knownLaunchers = setOf(
            "com.google.android.apps.nexuslauncher",  // Pixel Launcher
            "com.sec.android.app.launcher",            // Samsung One UI
            "com.huawei.android.launcher",             // Huawei
            "com.oppo.launcher",                       // OPPO
            "com.miui.home",                           // Xiaomi MIUI
            "com.android.launcher3",                   // AOSP Launcher
            "com.teslacoilsw.launcher",                // Nova Launcher
            "com.microsoft.launcher"                   // Microsoft Launcher
        )

        return knownLaunchers.contains(packageName)
    }

    /**
     * Check if a package is a system UI component.
     * 
     * @param packageName The package name to check
     * @return true if this is SystemUI
     */
    fun isSystemUI(packageName: String): Boolean {
        return packageName == "com.android.systemui"
    }

    /**
     * Check if a package is a settings app.
     * 
     * @param packageName The package name to check
     * @return true if this is a settings app
     */
    fun isSettings(packageName: String): Boolean {
        return SETTINGS_PACKAGES.contains(packageName)
    }

    /**
     * Get all known Settings-like packages for OEMs.
     */
    fun getSettingsPackages(): Set<String> = SETTINGS_PACKAGES

    /**
     * Check if a package is a package installer.
     * 
     * @param packageName The package name to check
     * @return true if this is a package installer
     */
    fun isPackageInstaller(packageName: String): Boolean {
        return packageName == "com.android.packageinstaller" ||
               packageName == "com.google.android.packageinstaller"
    }

    /**
     * Check if a package is a known browser.
     * 
     * @param packageName The package name to check
     * @return true if this is a browser app
     */
    fun isBrowser(packageName: String): Boolean {
        val knownBrowsers = setOf(
            "com.android.chrome",
            "com.google.android.apps.chrome",
            "com.sec.android.app.sbrowser",      // Samsung Internet
            "org.mozilla.firefox",
            "org.mozilla.fenix",                  // Firefox Nightly
            "com.microsoft.emmx",                 // Edge
            "com.opera.browser",
            "com.brave.browser",
            "com.vivaldi.browser",
            "com.duckduckgo.mobile.android"
        )

        return knownBrowsers.contains(packageName)
    }
}
