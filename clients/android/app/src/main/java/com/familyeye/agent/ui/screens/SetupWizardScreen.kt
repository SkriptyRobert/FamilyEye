package com.familyeye.agent.ui.screens

import android.Manifest
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import com.familyeye.agent.ui.viewmodel.SetupWizardViewModel
import com.familyeye.agent.ui.OemSetupViewModel
import com.familyeye.agent.ui.components.PermissionCard
import com.familyeye.agent.ui.screens.OemSetupWarningCard
import com.familyeye.agent.utils.AccountHelper
import timber.log.Timber

enum class SetupStep {
    WELCOME,
    PIN_SETUP,
    PERMISSIONS,
    OEM_CONFIG,
    DEVICE_OWNER_PREP,  // NOVY: "Odeberte účty"
    DEVICE_OWNER_PC,    // NOVY: "Připojte k PC"
    PAIRING,
    COMPLETE
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SetupWizardScreen(
    viewModel: SetupWizardViewModel = hiltViewModel(),
    oemViewModel: OemSetupViewModel = hiltViewModel(),
    onSetupComplete: () -> Unit
) {
    val context = LocalContext.current
    var currentStep by remember { mutableStateOf(SetupStep.WELCOME) }
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

    // Check permissions on composition
    // Check permissions on composition and ON_RESUME
    val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current
    
    val refreshPermissions = {
        hasAccessibility = viewModel.checkAccessibilityPermission(context)
        hasUsageStats = viewModel.checkUsageStatsPermission(context)
        hasOverlay = viewModel.checkOverlayPermission(context)
        hasDeviceAdmin = viewModel.checkDeviceAdminPermission(context)
        hasBatteryOpt = viewModel.checkBatteryOptimizationPermission(context)
        oemViewModel.refreshStatus()
    }

    LaunchedEffect(currentStep) {
        if (currentStep == SetupStep.PERMISSIONS || currentStep == SetupStep.OEM_CONFIG) {
            refreshPermissions()
        }
    }
    
    DisposableEffect(lifecycleOwner, currentStep) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME && 
                (currentStep == SetupStep.PERMISSIONS || currentStep == SetupStep.OEM_CONFIG)) {
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
                            SetupStep.WELCOME -> "Vítejte"
                            SetupStep.PIN_SETUP -> "Nastavení PIN"
                            SetupStep.PERMISSIONS -> "Oprávnění"
                            SetupStep.OEM_CONFIG -> "Výrobce"
                            SetupStep.DEVICE_OWNER_PREP -> "Příprava Device Owner"
                            SetupStep.DEVICE_OWNER_PC -> "Aktivace Device Owner"
                            SetupStep.PAIRING -> "Párování"
                            SetupStep.COMPLETE -> "Hotovo"
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
                progress = { (SetupStep.entries.indexOf(currentStep) + 1f) / SetupStep.entries.size },
                modifier = Modifier.fillMaxWidth()
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            when (currentStep) {
                SetupStep.WELCOME -> {
                    WelcomeStep(
                        onNext = { currentStep = SetupStep.PIN_SETUP }
                    )
                }
                
                SetupStep.PIN_SETUP -> {
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
                                    currentStep = SetupStep.PERMISSIONS
                                }
                            }
                        },
                        onBack = { currentStep = SetupStep.WELCOME }
                    )
                }
                
                SetupStep.PERMISSIONS -> {
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
                        onNext = { 
                            if (oemState.needsAttention) {
                                currentStep = SetupStep.OEM_CONFIG
                            } else {
                                // Check if Device Owner is already active
                                val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
                                val isDeviceOwner = dpm.isDeviceOwnerApp(context.packageName)
                                if (isDeviceOwner) {
                                    currentStep = SetupStep.PAIRING
                                } else {
                                    currentStep = SetupStep.DEVICE_OWNER_PREP
                                }
                            }
                        },
                        onBack = { currentStep = SetupStep.PIN_SETUP }
                    )
                }

                SetupStep.OEM_CONFIG -> {
                    OemConfigStep(
                        oemViewModel = oemViewModel,
                        onNext = { 
                            // Check if Device Owner is already active
                            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
                            val isDeviceOwner = dpm.isDeviceOwnerApp(context.packageName)
                            if (isDeviceOwner) {
                                currentStep = SetupStep.PAIRING
                            } else {
                                currentStep = SetupStep.DEVICE_OWNER_PREP
                            }
                        },
                        onBack = { currentStep = SetupStep.PERMISSIONS }
                    )
                }
                
                SetupStep.DEVICE_OWNER_PREP -> {
                    DeviceOwnerPrepStep(
                        onNext = { currentStep = SetupStep.DEVICE_OWNER_PC },
                        onBack = { 
                            if (oemState.needsAttention) {
                                currentStep = SetupStep.OEM_CONFIG
                            } else {
                                currentStep = SetupStep.PERMISSIONS
                            }
                        },
                        onSkip = { currentStep = SetupStep.PAIRING }
                    )
                }
                
                SetupStep.DEVICE_OWNER_PC -> {
                    DeviceOwnerPcStep(
                        onNext = { currentStep = SetupStep.PAIRING },
                        onBack = { currentStep = SetupStep.DEVICE_OWNER_PREP }
                    )
                }
                
                SetupStep.PAIRING -> {
                    PairingScreen(
                        onPairingSuccess = { currentStep = SetupStep.COMPLETE }
                    )
                }
                
                SetupStep.COMPLETE -> {
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

@Composable
private fun WelcomeStep(onNext: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // Hero Image
        androidx.compose.foundation.Image(
            painter = androidx.compose.ui.res.painterResource(id = com.familyeye.agent.R.drawable.img_onboarding),
            contentDescription = "FamilyEye Shield",
            modifier = Modifier
                .fillMaxWidth()
                .height(260.dp)
                .padding(bottom = 24.dp),
            contentScale = androidx.compose.ui.layout.ContentScale.Fit
        )
        
        Text(
            text = "Vítejte v FamilyEye",
            style = MaterialTheme.typography.headlineLarge,
            color = MaterialTheme.colorScheme.primary,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Pokročilá ochrana pro digitální bezpečí vašich dětí",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(
            text = "verze 1.0.22 (Zombie Fix)",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            ),
            border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Průvodce nastavením:",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(modifier = Modifier.height(12.dp))
                SetupListItem("Vytvoření rodičovského PINu")
                SetupListItem("Udělení ochranných oprávnění")
                SetupListItem("Aktivace monitoringu")
            }
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Button(
            onClick = onNext,
            modifier = Modifier.fillMaxWidth().height(50.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary
            )
        ) {
            Text("Začít nastavení", style = MaterialTheme.typography.titleMedium)
        }
        
        Spacer(modifier = Modifier.height(24.dp))
    }
}

@Composable
private fun SetupListItem(text: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier.padding(vertical = 4.dp)
    ) {
        Icon(
            Icons.Default.CheckCircle,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(20.dp)
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun PinSetupStep(
    pin: String,
    confirmPin: String,
    error: String?,
    onPinChange: (String) -> Unit,
    onConfirmPinChange: (String) -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Default.Lock,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Vytvořte rodičovský PIN",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "PIN chrání nastavení aplikace před dítětem",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        OutlinedTextField(
            value = pin,
            onValueChange = { if (it.length <= 6 && it.all { c -> c.isDigit() }) onPinChange(it) },
            label = { Text("PIN (4-6 číslic)") },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            isError = error != null
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        OutlinedTextField(
            value = confirmPin,
            onValueChange = { if (it.length <= 6 && it.all { c -> c.isDigit() }) onConfirmPinChange(it) },
            label = { Text("Potvrdit PIN") },
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
            isError = error != null,
            supportingText = error?.let { { Text(it, color = MaterialTheme.colorScheme.error) } }
        )
        
        Spacer(modifier = Modifier.weight(1f))
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Zpět")
            }
            Button(
                onClick = onNext,
                modifier = Modifier.weight(1f),
                enabled = pin.length >= 4 && confirmPin.isNotEmpty()
            ) {
                Text("Pokračovat")
            }
        }
    }
}

@Composable
private fun PermissionsStep(
    hasAccessibility: Boolean,
    hasUsageStats: Boolean,
    hasOverlay: Boolean,
    hasDeviceAdmin: Boolean,
    hasBatteryOpt: Boolean,
    oemViewModel: OemSetupViewModel,
    onRequestAccessibility: () -> Unit,
    onRequestUsageStats: () -> Unit,
    onRequestOverlay: () -> Unit,
    onRequestDeviceAdmin: () -> Unit,
    onRequestBatteryOpt: () -> Unit,
    onRefresh: () -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit
) {
    val allGranted = hasAccessibility && hasUsageStats && hasOverlay && hasDeviceAdmin && hasBatteryOpt
    
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Oprávnění aplikace",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "Pro správnou funkci potřebuje FamilyEye následující oprávnění:",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        PermissionCard(
            title = "Přístup k použití aplikací",
            description = "Pro sledování času stráveného v aplikacích",
            granted = hasUsageStats,
            onClick = onRequestUsageStats
        )
        
        Spacer(modifier = Modifier.height(12.dp))
        
        PermissionCard(
            title = "Služba přístupnosti",
            description = "Pro monitorování aktivity a detekci obsahu",
            granted = hasAccessibility,
            onClick = onRequestAccessibility
        )
        
        Spacer(modifier = Modifier.height(12.dp))
        
        PermissionCard(
            title = "Ignorovat optimalizaci baterie",
            description = "Pro zajištění běhu na pozadí",
            granted = hasBatteryOpt,
            onClick = onRequestBatteryOpt
        )
        
        Spacer(modifier = Modifier.height(12.dp))
        
        PermissionCard(
            title = "Zobrazení přes jiné aplikace",
            description = "Pro blokaci nevhodného obsahu",
            granted = hasOverlay,
            onClick = onRequestOverlay
        )
        
        Spacer(modifier = Modifier.height(12.dp))
        
        PermissionCard(
            title = "Správce zařízení",
            description = "Pro ochranu před odinstalací",
            granted = hasDeviceAdmin,
            onClick = onRequestDeviceAdmin
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Spacer(modifier = Modifier.height(16.dp))
        
        
        TextButton(onClick = onRefresh) {
            Icon(Icons.Default.Refresh, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Obnovit stav")
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Zpět")
            }
            Button(
                onClick = onNext,
                modifier = Modifier.weight(1f),
                enabled = allGranted
            ) {
                Text("Pokračovat")
            }
        }
        
        if (!allGranted) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Udělte všechna oprávnění pro pokračování",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}



@Composable
private fun CompleteStep(onFinish: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            Icons.Default.CheckCircle,
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "Nastavení dokončeno!",
            style = MaterialTheme.typography.headlineMedium
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "FamilyEye je nyní aktivní a chrání toto zařízení.",
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        
        Spacer(modifier = Modifier.weight(1f))
        
        Button(
            onClick = onFinish,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Dokončit")
        }
    }
}

@Composable
private fun OemConfigStep(
    oemViewModel: OemSetupViewModel,
    onNext: () -> Unit,
    onBack: () -> Unit
) {
    val state by oemViewModel.uiState.collectAsState()
    
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Default.Build,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Optimalizace pro ${state.manufacturer}",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "Výrobci jako ${state.manufacturer} mají agresivní správu baterie, která může zastavit ochranu.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        OemSetupWarningCard(
            viewModel = oemViewModel
        )
        
        Spacer(modifier = Modifier.weight(1f))
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Zpět")
            }
            Button(
                onClick = onNext,
                modifier = Modifier.weight(1f)
            ) {
                Text("Vše nastaveno")
            }
        }
        
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Pokračujte pouze pokud jste povolili AutoStart",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun DeviceOwnerPrepStep(
    onNext: () -> Unit,
    onBack: () -> Unit,
    onSkip: () -> Unit
) {
    val context = LocalContext.current
    val accounts = remember { AccountHelper.getGoogleAccounts(context) }
    val hasAccounts = accounts.isNotEmpty()
    
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Default.Security,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Příprava Device Owner",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "Device Owner poskytuje maximální ochranu a přežije i agresivní správu baterie.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = if (hasAccounts) 
                    MaterialTheme.colorScheme.errorContainer 
                else 
                    MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = if (hasAccounts) "Účty musí být odebrány" else "Žádné účty nenalezeny",
                    style = MaterialTheme.typography.titleMedium,
                    color = if (hasAccounts) 
                        MaterialTheme.colorScheme.onErrorContainer 
                    else 
                        MaterialTheme.colorScheme.onPrimaryContainer
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                if (hasAccounts) {
                    Text(
                        text = "Nalezené Google účty:",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    accounts.forEach { account ->
                        Text(
                            text = "• $account",
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(start = 8.dp)
                        )
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Odeberte tyto účty v Nastavení → Účty před pokračováním.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onErrorContainer
                    )
                } else {
                    Text(
                        text = "Zařízení je připraveno pro Device Owner aktivaci.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Zpět")
            }
            
            if (hasAccounts) {
                OutlinedButton(
                    onClick = {
                        val intent = Intent(android.provider.Settings.ACTION_SYNC_SETTINGS)
                        context.startActivity(intent)
                    },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Otevřít účty")
                }
            }
            
            Button(
                onClick = onNext,
                modifier = Modifier.weight(1f),
                enabled = !hasAccounts
            ) {
                Text("Pokračovat")
            }
        }
        
        Spacer(modifier = Modifier.height(8.dp))
        
        TextButton(onClick = onSkip) {
            Text("Přeskočit Device Owner")
        }
    }
}

@Composable
private fun DeviceOwnerPcStep(
    onNext: () -> Unit,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val packageName = context.packageName
    val adminReceiver = "${packageName}/com.familyeye.agent.receiver.FamilyEyeDeviceAdmin"
    val adbCommand = "adb shell dpm set-device-owner $adminReceiver"
    
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            Icons.Default.Usb,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Text(
            text = "Aktivace Device Owner",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Spacer(modifier = Modifier.height(8.dp))
        
        Text(
            text = "Připojte telefon k počítači s Chrome a spusťte aktivaci z dashboardu.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Instrukce:",
                    style = MaterialTheme.typography.titleMedium
                )
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Text("1. Připojte telefon k PC pomocí USB kabelu", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text("2. Zapněte USB ladění (Pokud ještě není)", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text("3. Otevřete FamilyEye Dashboard v Chrome", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text("4. Přejděte na stránku Device Owner Setup", style = MaterialTheme.typography.bodyMedium)
                Spacer(modifier = Modifier.height(8.dp))
                Text("5. Klikněte na 'Aktivovat Device Owner'", style = MaterialTheme.typography.bodyMedium)
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            )
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "ADB příkaz (pro ruční aktivaci):",
                    style = MaterialTheme.typography.titleSmall
                )
                Spacer(modifier = Modifier.height(8.dp))
                SelectionContainer {
                    Text(
                        text = adbCommand,
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Check if Device Owner is already active
        val dpm = remember { 
            context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
        }
        val isDeviceOwner = remember { dpm.isDeviceOwnerApp(packageName) }
        
        if (isDeviceOwner) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Device Owner je aktivní!",
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onPrimaryContainer
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Zpět")
            }
            Button(
                onClick = onNext,
                modifier = Modifier.weight(1f),
                enabled = isDeviceOwner
            ) {
                Text(if (isDeviceOwner) "Pokračovat" else "Čekám na aktivaci...")
            }
        }
    }
}
