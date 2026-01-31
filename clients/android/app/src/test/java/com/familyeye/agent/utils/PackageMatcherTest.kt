package com.familyeye.agent.utils

import org.junit.Assert.*
import org.junit.Test

class PackageMatcherTest {

    @Test
    fun testExactPackageMatch() {
        // Matches should be case-insensitive
        assertTrue(PackageMatcher.matches("com.android.settings", "com.android.settings", "Settings"))
        assertTrue(PackageMatcher.matches("com.android.settings", "COM.ANDROID.SETTINGS", "Settings"))
    }

    @Test
    fun testPartialPackageMatch() {
        // Rule can be a substring of the package
        assertTrue(PackageMatcher.matches("com.facebook.katana", "facebook", "Facebook"))
        assertTrue(PackageMatcher.matches("com.google.android.youtube", "youtube", "YouTube"))
    }

    @Test
    fun testAppLabelMatchWithAccents() {
        // Test normalization (removing diacritics)
        // Rule: "Poznamky" (no accent) vs Label: "Poznámky" (accent)
        assertTrue(PackageMatcher.matches("com.android.notes", "Poznamky", "Poznámky"))
        
        // Rule: "Poznámky" (accent) vs Label: "Poznamky" (no accent)
        assertTrue(PackageMatcher.matches("com.android.notes", "Poznámky", "Poznamky"))
        
        // Case with both having accents but maybe different
        assertTrue(PackageMatcher.matches("com.android.notes", "POZNAMKY", "poznámky"))
    }

    @Test
    fun testIsLauncher() {
        // Common launchers
        assertTrue(PackageMatcher.isLauncher("com.google.android.apps.nexuslauncher"))
        assertTrue(PackageMatcher.isLauncher("com.sec.android.app.launcher"))
        assertTrue(PackageMatcher.isLauncher("com.huawei.android.launcher"))
        
        // Not a launcher
        assertFalse(PackageMatcher.isLauncher("com.android.settings"))
        assertFalse(PackageMatcher.isLauncher("com.facebook.katana"))
    }

    @Test
    fun testNormalizationHelper() {
        // Since normalize is private, we test it indirectly via matches
        // But we can check edge cases like nulls or empty strings if we wanted to be thorough
        assertTrue(PackageMatcher.matches("pkg", "", "")) 
    }
}
