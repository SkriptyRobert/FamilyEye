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
        setContent {
            com.familyeye.agent.ui.theme.FamilyEyeTheme (
                darkTheme = true // Force dark theme for "Enterprise" feel
            ) {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    FamilyEyeApp()
                }
            }
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
                        // In standalone mode, maybe go to dashboard? 
                        // But we prefer setup_wizard flow.
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
