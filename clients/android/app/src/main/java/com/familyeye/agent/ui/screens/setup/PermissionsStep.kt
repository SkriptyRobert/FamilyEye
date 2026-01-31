package com.familyeye.agent.ui.screens.setup

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.familyeye.agent.ui.OemSetupViewModel
import com.familyeye.agent.ui.components.PermissionCard

@Composable
fun PermissionsStep(
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
