package com.familyeye.agent.ui

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.familyeye.agent.receiver.BootReceiver
import com.familyeye.agent.service.FamilyEyeService

import com.familyeye.agent.ui.screens.AdminLoginScreen
import com.familyeye.agent.ui.screens.ChildDashboardScreen
import com.familyeye.agent.ui.screens.PairingScreen
import com.familyeye.agent.ui.screens.SettingsScreen
import com.familyeye.agent.ui.screens.SetupWizardScreen
import com.familyeye.agent.ui.viewmodel.MainViewModel
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        permissions.entries.forEach {
            Timber.i("Permission ${it.key} granted: ${it.value}")
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Ensure service is running
        FamilyEyeService.start(this)

        // Request basic permissions on start
        requestPermissions()

        setContent {
            com.familyeye.agent.ui.theme.FamilyEyeTheme (
                darkTheme = true // Force dark theme for "Enterprise" feel
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    FamilyEyeApp()
                    
                    // Xiaomi Logic: Check for Autostart permission
                    val context = androidx.compose.ui.platform.LocalContext.current
                    LaunchedEffect(Unit) {
                        if (isXiaomi()) {
                            checkXiaomiAutostart(context)
                        }
                        checkBatteryOptimization(context)
                    }
                }
            }
        }
    }

    private fun isXiaomi(): Boolean {
        return Build.MANUFACTURER.equals("Xiaomi", ignoreCase = true)
    }

    private fun checkXiaomiAutostart(context: android.content.Context) {
        val prefs = context.getSharedPreferences("agent_prefs", android.content.Context.MODE_PRIVATE)
        val hasAsked = prefs.getBoolean("xiaomi_autostart_asked", false)
        
        if (!hasAsked) {
            val intent = android.content.Intent().apply {
                component = android.content.ComponentName(
                    "com.miui.securitycenter",
                    "com.miui.permcenter.autostart.AutoStartManagementActivity"
                )
            }
            // Verify if intent can be handled
            if (context.packageManager.resolveActivity(intent, 0) != null) {
                // Simplified: Toast + intent (Compose Dialog later).
                android.widget.Toast.makeText(context, "Please enable AUTOSTART for FamilyEye to ensure protection!", android.widget.Toast.LENGTH_LONG).show()
                try {
                    context.startActivity(intent)
                    prefs.edit().putBoolean("xiaomi_autostart_asked", true).apply()
                } catch (e: Exception) {
                    Timber.e(e, "Failed to launch Xiaomi Autostart settings")
                }
            }
        }
    }

    private fun checkBatteryOptimization(context: android.content.Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = context.getSystemService(android.content.Context.POWER_SERVICE) as android.os.PowerManager
            val packageName = context.packageName
            val isIgnoring = powerManager.isIgnoringBatteryOptimizations(packageName)
            
            if (!isIgnoring) {
                Timber.w("Battery Optimization ACTIVE - Requesting exemption")
                android.widget.Toast.makeText(context, "FAMILYEYE: Requesting Battery Exemption to prevent KILL", android.widget.Toast.LENGTH_LONG).show()
                
                try {
                    val intent = android.content.Intent().apply {
                        action = android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
                        data = android.net.Uri.parse("package:$packageName")
                    }
                    context.startActivity(intent)
                } catch (e: Exception) {
                    Timber.e(e, "Failed to launch Battery Optimization settings")
                }
            } else {
                 Timber.i("Battery Optimization already IGNORED (Good)")
            }
        }
    }

    private fun requestPermissions() {
        val permissions = mutableListOf(
            Manifest.permission.CAMERA
        )
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        
        requestPermissionLauncher.launch(permissions.toTypedArray())
    }

    @Composable
    fun FamilyEyeApp() {
        val navController = rememberNavController()
        val isPaired by viewModel.isPaired.collectAsState()

        // Navigation logic based on pairing state
        // Navigation logic based on pairing state
        // Only redirect to setup wizard if device is NOT paired
        LaunchedEffect(isPaired) {
            if (isPaired == true) {
                navController.navigate("dashboard") {
                    popUpTo(0) { inclusive = true }
                }
            } else if (isPaired == false) {
                navController.navigate("setup_wizard") {
                    popUpTo(0) { inclusive = true }
                }
            }
        }

        NavHost(
            navController = navController,
            startDestination = "setup_wizard" // Will be redirected by LaunchedEffect if already paired (to be improved)
        ) {
            composable("setup_wizard") {
                 SetupWizardScreen(
                     onSetupComplete = {
                         navController.navigate("dashboard") {
                             popUpTo("setup_wizard") { inclusive = true }
                         }
                     }
                 )
            }
            
            // Keep standalone pairing route just in case, or for debugging
            composable("pairing") {
                PairingScreen(
                    onPairingSuccess = {
                        // Standalone pairing success -> dashboard (setup_wizard preferred elsewhere).
                        navController.navigate("dashboard")
                    }
                )
            }
            
            composable("dashboard") {
                ChildDashboardScreen(
                    onAdminClick = {
                        navController.navigate("admin_login")
                    }
                )
            }
            
            composable("admin_login") {
                AdminLoginScreen(
                    onLoginSuccess = {
                        navController.navigate("settings") {
                            popUpTo("dashboard") 
                        }
                    },
                    onBack = {
                        navController.popBackStack()
                    }
                )
            }
            
            composable("settings") {
                SettingsScreen(
                    onLogout = {
                        navController.navigate("dashboard") {
                            popUpTo("dashboard") { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}
