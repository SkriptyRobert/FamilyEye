package com.familyeye.agent.ui.screens

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import com.familyeye.agent.ui.viewmodel.SetupWizardViewModel
import com.familyeye.agent.ui.OemSetupViewModel
import com.familyeye.agent.ui.screens.setup.*

@OptIn(ExperimentalMaterial3Api::class, androidx.compose.animation.ExperimentalAnimationApi::class)
@Composable
fun SetupWizardScreen(
    viewModel: SetupWizardViewModel = hiltViewModel(),
    oemViewModel: OemSetupViewModel = hiltViewModel(),
    onSetupComplete: () -> Unit
) {
    val context = LocalContext.current
    val currentStep by viewModel.currentStep.collectAsState()
    var pin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var pinError by remember { mutableStateOf<String?>(null) }
    
    val oemState by oemViewModel.uiState.collectAsState()
    
    // Permission states
    var hasAccessibility by remember { mutableStateOf(false) }
    var hasUsageStats by remember { mutableStateOf(false) }
    var hasOverlay by remember { mutableStateOf(false) }
    var hasDeviceAdmin by remember { mutableStateOf(false) }
    var hasBatteryOpt by remember { mutableStateOf(false) }

    val refreshPermissions = {
        hasAccessibility = viewModel.checkAccessibilityPermission(context)
        hasUsageStats = viewModel.checkUsageStatsPermission(context)
        hasOverlay = viewModel.checkOverlayPermission(context)
        hasDeviceAdmin = viewModel.checkDeviceAdminPermission(context)
        hasBatteryOpt = viewModel.checkBatteryOptimizationPermission(context)
        oemViewModel.refreshStatus()
    }
    
    val checkDeviceOwner: () -> Boolean = {
        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        dpm.isDeviceOwnerApp(context.packageName)
    }

    LaunchedEffect(currentStep) {
        if (currentStep == SetupWizardViewModel.SetupStep.PERMISSIONS || currentStep == SetupWizardViewModel.SetupStep.OEM_CONFIG) {
            refreshPermissions()
        }
    }
    
    val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner, currentStep) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME && 
                (currentStep == SetupWizardViewModel.SetupStep.PERMISSIONS || currentStep == SetupWizardViewModel.SetupStep.OEM_CONFIG)) {
                refreshPermissions()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { 
                    Text(
                        when (currentStep) {
                            SetupWizardViewModel.SetupStep.WELCOME -> "Vítejte"
                            SetupWizardViewModel.SetupStep.PIN_SETUP -> "Nastavení PIN"
                            SetupWizardViewModel.SetupStep.PERMISSIONS -> "Oprávnění"
                            SetupWizardViewModel.SetupStep.OEM_CONFIG -> "Výrobce"
                            SetupWizardViewModel.SetupStep.DEVICE_OWNER_PREP -> "Příprava Device Owner"
                            SetupWizardViewModel.SetupStep.DEVICE_OWNER_PC -> "Aktivace Device Owner"
                            SetupWizardViewModel.SetupStep.PAIRING -> "Párování"
                            SetupWizardViewModel.SetupStep.COMPLETE -> "Hotovo"
                        }
                    )
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Progress Indicator
            LinearProgressIndicator(
                progress = { (SetupWizardViewModel.SetupStep.entries.indexOf(currentStep) + 1f) / SetupWizardViewModel.SetupStep.entries.size },
                modifier = Modifier.fillMaxWidth()
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            androidx.compose.animation.AnimatedContent(
                targetState = currentStep,
                transitionSpec = {
                    if (targetState.ordinal > initialState.ordinal) {
                        androidx.compose.animation.slideInHorizontally { width -> width } + androidx.compose.animation.fadeIn() with
                                androidx.compose.animation.slideOutHorizontally { width -> -width } + androidx.compose.animation.fadeOut()
                    } else {
                        androidx.compose.animation.slideInHorizontally { width -> -width } + androidx.compose.animation.fadeIn() with
                                androidx.compose.animation.slideOutHorizontally { width -> width } + androidx.compose.animation.fadeOut()
                    }.using(androidx.compose.animation.SizeTransform(clip = false))
                },
                label = "StepTransition"
            ) { step ->
                Column(modifier = Modifier.fillMaxSize()) {
                    when (step) {
                        SetupWizardViewModel.SetupStep.WELCOME -> {
                            WelcomeStep(
                                onNext = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.PIN_SETUP -> {
                            PinSetupStep(
                                pin = pin,
                                confirmPin = confirmPin,
                                error = pinError,
                                onPinChange = { pin = it; pinError = null },
                                onConfirmPinChange = { confirmPin = it; pinError = null },
                                onNext = {
                                    when {
                                        pin.length < 4 -> pinError = "PIN musí mít alespoň 4 číslice"
                                        pin != confirmPin -> pinError = "PIN se neshoduje"
                                        else -> {
                                            viewModel.savePin(pin)
                                            viewModel.nextStep(oemState.needsAttention, checkDeviceOwner())
                                        }
                                    }
                                },
                                onBack = { viewModel.previousStep(oemState.needsAttention) }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.PERMISSIONS -> {
                            PermissionsStep(
                                hasAccessibility = hasAccessibility,
                                hasUsageStats = hasUsageStats,
                                hasOverlay = hasOverlay,
                                hasDeviceAdmin = hasDeviceAdmin,
                                hasBatteryOpt = hasBatteryOpt,
                                oemViewModel = oemViewModel,
                                onRequestAccessibility = {
                                    val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                                    context.startActivity(intent)
                                },
                                onRequestUsageStats = {
                                    val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                                    context.startActivity(intent)
                                },
                                onRequestOverlay = {
                                    val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                                    context.startActivity(intent)
                                },
                                onRequestDeviceAdmin = {
                                    val componentName = ComponentName(context, FamilyEyeDeviceAdmin::class.java)
                                    val intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                                        putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, componentName)
                                        putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION, 
                                            "FamilyEye potřebuje oprávnění správce zařízení pro ochranu před odinstalací.")
                                    }
                                    context.startActivity(intent)
                                },
                                onRequestBatteryOpt = {
                                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                                        val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                                            data = android.net.Uri.parse("package:${context.packageName}")
                                        }
                                        context.startActivity(intent)
                                    }
                                },
                                onRefresh = { refreshPermissions() },
                                onNext = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) },
                                onBack = { viewModel.previousStep(oemState.needsAttention) }
                            )
                        }
        
                        SetupWizardViewModel.SetupStep.OEM_CONFIG -> {
                            OemConfigStep(
                                oemViewModel = oemViewModel,
                                onNext = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) },
                                onBack = { viewModel.previousStep(oemState.needsAttention) }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.DEVICE_OWNER_PREP -> {
                            DeviceOwnerPrepStep(
                                onNext = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) },
                                onBack = { viewModel.previousStep(oemState.needsAttention) },
                                onSkip = { viewModel.skipDeviceOwner() }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.DEVICE_OWNER_PC -> {
                            DeviceOwnerPcStep(
                                onNext = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) },
                                onBack = { viewModel.previousStep(oemState.needsAttention) }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.PAIRING -> {
                            PairingScreen(
                                onPairingSuccess = { viewModel.nextStep(oemState.needsAttention, checkDeviceOwner()) }
                            )
                        }
                        
                        SetupWizardViewModel.SetupStep.COMPLETE -> {
                            CompleteStep(
                                onFinish = {
                                    viewModel.markSetupComplete()
                                    onSetupComplete()
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

