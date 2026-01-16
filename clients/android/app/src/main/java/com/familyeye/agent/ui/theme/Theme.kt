package com.familyeye.agent.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = FamilyEyePurpleLight, // Use lighter purple for better contrast against dark bg
    onPrimary = Color.Black,
    secondary = FamilyEyeTeal,
    tertiary = Pink80,
    background = FamilyEyeBackground,
    surface = FamilyEyeSurface,
    surfaceVariant = FamilyEyeSurfaceVariant,
    onBackground = FamilyEyeOnSurface,
    onSurface = FamilyEyeOnSurface,
    onSurfaceVariant = FamilyEyeOnSurfaceVariant
)

// We only define Dark scheme as the app is Enterprise-Dark branded
// Light scheme is not used but kept for structure if needed later

@Composable
fun FamilyEyeTheme(
    darkTheme: Boolean = true, // Force Dark Theme
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false, // Force brand colors
    content: @Composable () -> Unit
) {
    val colorScheme = DarkColorScheme // Always use Dark Scheme

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = FamilyEyeBackground.toArgb() // Match background
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = false // White text icons
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
