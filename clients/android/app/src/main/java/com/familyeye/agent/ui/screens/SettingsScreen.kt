package com.familyeye.agent.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.BuildConfig
import com.familyeye.agent.ui.viewmodel.MainViewModel
import com.familyeye.agent.ui.OemSetupViewModel
import com.familyeye.agent.ui.components.PermissionItem
import com.familyeye.agent.ui.screens.OemSetupWarningCard
import timber.log.Timber

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: MainViewModel = hiltViewModel(),
    oemViewModel: OemSetupViewModel = hiltViewModel(),
    onLogout: () -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = androidx.compose.ui.platform.LocalLifecycleOwner.current
    
    // Refresh permissions when coming back to the app (ON_RESUME)
    androidx.compose.runtime.DisposableEffect(lifecycleOwner) {
        val observer = androidx.lifecycle.LifecycleEventObserver { _, event ->
            if (event == androidx.lifecycle.Lifecycle.Event.ON_RESUME) {
                viewModel.refreshPermissions()
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }

    val permissions by viewModel.permissions.collectAsState()
    
    val hasUsage = permissions.hasUsage
    val hasOverlay = permissions.hasOverlay
    val hasAccessibility = permissions.hasAccessibility
    val hasDeviceAdmin = permissions.hasDeviceAdmin
    val hasBatteryOpt = permissions.hasBatteryOpt

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text("Nastavení") },
                actions = {
                    TextButton(onClick = onLogout) {
                        Text("Zpět")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // OEM Setup Warning (Parent-only, after PIN)
            OemSetupWarningCard(viewModel = oemViewModel)
            
            // Permissions Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Oprávnění", 
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    PermissionItem(
                        label = "Správce zařízení", 
                        isGranted = hasDeviceAdmin,
                        onClick = {
                            val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
                            val isDeviceOwner = dpm.isDeviceOwnerApp(context.packageName)

                            if (isDeviceOwner) {
                                // Device Owner is active - special handling
                                android.widget.Toast.makeText(context, "Aplikace je Správce zařízení (Device Owner)", android.widget.Toast.LENGTH_SHORT).show()
                                // DO active: open settings (Remove DO would require programmatic clear).
                                try {
                                    val intent = Intent(Settings.ACTION_SECURITY_SETTINGS)
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    // Ignore
                                }
                            } else if (hasDeviceAdmin) {
                                // Already granted as standard Admin - open Device Admin list
                                val intent = Intent().apply {
                                    component = android.content.ComponentName(
                                        "com.android.settings",
                                        "com.android.settings.DeviceAdminSettings"
                                    )
                                }
                                try {
                                    context.startActivity(intent)
                                } catch (e: Exception) {
                                    val fallbackIntent = Intent(Settings.ACTION_SECURITY_SETTINGS)
                                    context.startActivity(fallbackIntent)
                                }
                            } else {
                                // Not granted - open ADD dialog
                                val componentName = android.content.ComponentName(context, com.familyeye.agent.receiver.FamilyEyeDeviceAdmin::class.java)
                                val intent = Intent(android.app.admin.DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                                    putExtra(android.app.admin.DevicePolicyManager.EXTRA_DEVICE_ADMIN, componentName)
                                    putExtra(android.app.admin.DevicePolicyManager.EXTRA_ADD_EXPLANATION, "Potřebné pro prevenci odinstalace aplikace dítětem.")
                                }
                                context.startActivity(intent)
                            }
                        }
                    )
                    PermissionItem(
                        label = "Ignorovat optimalizaci baterie",
                        isGranted = hasBatteryOpt,
                        onClick = {
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                                val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                                    data = Uri.parse("package:${context.packageName}")
                                }
                                context.startActivity(intent)
                            }
                        }
                    )
                    PermissionItem(
                        label = "Zobrazení přes aplikace", 
                        isGranted = hasOverlay,
                        onClick = {
                            val intent = Intent(
                                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                                Uri.parse("package:${context.packageName}")
                            )
                            context.startActivity(intent)
                        }
                    )
                    PermissionItem(
                        label = "Využití aplikací", 
                        isGranted = hasUsage,
                        onClick = {
                            val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
                            context.startActivity(intent)
                        }
                    )
                    PermissionItem(
                        label = "Přístupnost", 
                        isGranted = hasAccessibility,
                        onClick = {
                            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                            context.startActivity(intent)
                        }
                    )
                }
            }
            
            // Settings Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Data", 
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    val dataSaverEnabled = viewModel.dataSaverEnabled.collectAsState().value
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Šetřič dat", style = MaterialTheme.typography.bodyLarge)
                            Text(
                                "Synchronizovat pouze přes Wi-Fi", 
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            checked = dataSaverEnabled,
                            onCheckedChange = { viewModel.setDataSaver(it) }
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Unpair & Deactivate Button
            OutlinedButton(
                onClick = { 
                    // 1. Remove Device Admin if active
                    try {
                        val dpm = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
                        val componentName = android.content.ComponentName(context, com.familyeye.agent.receiver.FamilyEyeDeviceAdmin::class.java)
                        if (dpm.isAdminActive(componentName)) {
                            dpm.removeActiveAdmin(componentName)
                            android.widget.Toast.makeText(context, "Ochrana deaktivována", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    } catch (e: Exception) {
                        Timber.e(e, "Failed to remove active admin")
                    }
                    
                    // 2. Procced with Unpair
                    viewModel.unpair() 
                },
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.error
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Outlined.ExitToApp, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                // If admin is active, show "Deactivate", else "Unpair"
                val text = if (hasDeviceAdmin) "Deaktivovat a Odpárovat" else "Odpárovat zařízení"
                Text(text)
            }
            
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(
                text = "Verze ${BuildConfig.VERSION_NAME}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}


