package com.familyeye.agent.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.ui.viewmodel.MainViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatusScreen(viewModel: MainViewModel = hiltViewModel()) {
    val context = LocalContext.current
    val hasUsage = viewModel.hasUsageStatsPermission()
    val hasOverlay = viewModel.hasOverlayPermission()
    val hasAccessibility = viewModel.hasAccessibilityPermission()
    val hasDeviceAdmin = viewModel.hasDeviceAdminPermission()

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(title = { Text("FamilyEye Agent") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
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
                            val componentName = android.content.ComponentName(context, com.familyeye.agent.receiver.FamilyEyeDeviceAdmin::class.java)
                            val intent = Intent(android.app.admin.DevicePolicyManager.ACTION_ADD_DEVICE_ADMIN).apply {
                                putExtra(android.app.admin.DevicePolicyManager.EXTRA_DEVICE_ADMIN, componentName)
                                putExtra(android.app.admin.DevicePolicyManager.EXTRA_ADD_EXPLANATION, "Potřebné pro prevenci odinstalace aplikace dítětem.")
                            }
                            context.startActivity(intent)
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
            
            Spacer(modifier = Modifier.weight(1f))
            
            Text(
                text = "Verze 1.0.0",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
fun PermissionItem(label: String, isGranted: Boolean, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(vertical = 12.dp, horizontal = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, style = MaterialTheme.typography.bodyLarge)
        if (isGranted) {
            Icon(
                imageVector = Icons.Outlined.CheckCircle,
                contentDescription = "Povoleno",
                tint = MaterialTheme.colorScheme.primary
            )
        } else {
             Icon(
                imageVector = Icons.Filled.Warning,
                contentDescription = "Vyžadováno",
                tint = MaterialTheme.colorScheme.error
            )
        }
    }
}
