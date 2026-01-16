package com.familyeye.agent.ui.screens

import android.Manifest
import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
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
import timber.log.Timber

enum class SetupStep {
    WELCOME,
    PIN_SETUP,
    PERMISSIONS,
    PAIRING,
    COMPLETE
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SetupWizardScreen(
    viewModel: SetupWizardViewModel = hiltViewModel(),
    onSetupComplete: () -> Unit
) {
    val context = LocalContext.current
    var currentStep by remember { mutableStateOf(SetupStep.WELCOME) }
    var pin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var pinError by remember { mutableStateOf<String?>(null) }
    
    // Permission states
    var hasAccessibility by remember { mutableStateOf(false) }
    var hasUsageStats by remember { mutableStateOf(false) }
    var hasOverlay by remember { mutableStateOf(false) }
    var hasDeviceAdmin by remember { mutableStateOf(false) }

    // Check permissions on composition
    LaunchedEffect(currentStep) {
        if (currentStep == SetupStep.PERMISSIONS) {
            hasAccessibility = viewModel.checkAccessibilityPermission(context)
            hasUsageStats = viewModel.checkUsageStatsPermission(context)
            hasOverlay = viewModel.checkOverlayPermission(context)
            hasDeviceAdmin = viewModel.checkDeviceAdminPermission(context)
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
                        onRefresh = {
                            hasAccessibility = viewModel.checkAccessibilityPermission(context)
                            hasUsageStats = viewModel.checkUsageStatsPermission(context)
                            hasOverlay = viewModel.checkOverlayPermission(context)
                            hasDeviceAdmin = viewModel.checkDeviceAdminPermission(context)
                        },
                        onNext = { currentStep = SetupStep.PAIRING },
                        onBack = { currentStep = SetupStep.PIN_SETUP }
                    )
                }
                
                SetupStep.PAIRING -> {
                    // Embed existing PairingScreen or simplified version
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
        modifier = Modifier.fillMaxWidth(),
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
        
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
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
        
        Spacer(modifier = Modifier.weight(1f))
        
        Button(
            onClick = onNext,
            modifier = Modifier.fillMaxWidth().height(50.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary
            )
        ) {
            Text("Začít nastavení", style = MaterialTheme.typography.titleMedium)
        }
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
    onRequestAccessibility: () -> Unit,
    onRequestUsageStats: () -> Unit,
    onRequestOverlay: () -> Unit,
    onRequestDeviceAdmin: () -> Unit,
    onRefresh: () -> Unit,
    onNext: () -> Unit,
    onBack: () -> Unit
) {
    val allGranted = hasAccessibility && hasUsageStats && hasOverlay && hasDeviceAdmin
    
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
private fun PermissionCard(
    title: String,
    description: String,
    granted: Boolean,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (granted) 
                MaterialTheme.colorScheme.primaryContainer 
            else 
                MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleSmall)
                Text(
                    description, 
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            
            if (granted) {
                Icon(
                    Icons.Default.CheckCircle,
                    contentDescription = "Uděleno",
                    tint = MaterialTheme.colorScheme.primary
                )
            } else {
                TextButton(onClick = onClick) {
                    Text("Udělit")
                }
            }
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
