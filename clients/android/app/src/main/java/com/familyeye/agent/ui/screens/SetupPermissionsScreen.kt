package com.familyeye.agent.ui.screens

import android.app.admin.DevicePolicyManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.provider.Settings
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import com.familyeye.agent.ui.viewmodel.SetupWizardViewModel

/**
 * Screen for granting permissions after PIN setup.
 * This is step 3 of the setup flow: Pairing → PIN → Permissions → Dashboard
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SetupPermissionsScreen(
    viewModel: SetupWizardViewModel = hiltViewModel(),
    onPermissionsComplete: () -> Unit
) {
    val context = LocalContext.current
    
    var hasAccessibility by remember { mutableStateOf(false) }
    var hasUsageStats by remember { mutableStateOf(false) }
    var hasOverlay by remember { mutableStateOf(false) }
    var hasDeviceAdmin by remember { mutableStateOf(false) }

    // Check permissions on composition and refresh
    fun refreshPermissions() {
        hasAccessibility = viewModel.checkAccessibilityPermission(context)
        hasUsageStats = viewModel.checkUsageStatsPermission(context)
        hasOverlay = viewModel.checkOverlayPermission(context)
        hasDeviceAdmin = viewModel.checkDeviceAdminPermission(context)
    }

    LaunchedEffect(Unit) {
        refreshPermissions()
    }

    // Refresh when returning from settings
    val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) {
                refreshPermissions()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val allGranted = hasAccessibility && hasUsageStats && hasOverlay && hasDeviceAdmin

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(title = { Text("Oprávnění") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
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
                onClick = {
                    val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                    context.startActivity(intent)
                }
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            PermissionCard(
                title = "Služba přístupnosti",
                description = "Pro monitorování aktivity a detekci obsahu",
                granted = hasAccessibility,
                onClick = {
                    val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    context.startActivity(intent)
                }
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            PermissionCard(
                title = "Zobrazení přes jiné aplikace",
                description = "Pro blokaci nevhodného obsahu",
                granted = hasOverlay,
                onClick = {
                    val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION)
                    context.startActivity(intent)
                }
            )
            
            Spacer(modifier = Modifier.height(12.dp))
            
            PermissionCard(
                title = "Správce zařízení",
                description = "Pro ochranu před odinstalací",
                granted = hasDeviceAdmin,
                onClick = {
                    val componentName = ComponentName(context, FamilyEyeDeviceAdmin::class.java)
                    val intent = Intent(DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                        putExtra(DevicePolicyManager.EXTRA_DEVICE_ADMIN, componentName)
                        putExtra(DevicePolicyManager.EXTRA_ADD_EXPLANATION, 
                            "FamilyEye potřebuje oprávnění správce zařízení pro ochranu před odinstalací.")
                    }
                    context.startActivity(intent)
                }
            )
            
            Spacer(modifier = Modifier.height(16.dp))
            
            TextButton(onClick = { refreshPermissions() }) {
                Icon(Icons.Default.Refresh, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Obnovit stav")
            }
            
            Spacer(modifier = Modifier.weight(1f))
            
            Button(
                onClick = onPermissionsComplete,
                modifier = Modifier.fillMaxWidth(),
                enabled = allGranted
            ) {
                Text("Dokončit nastavení")
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
