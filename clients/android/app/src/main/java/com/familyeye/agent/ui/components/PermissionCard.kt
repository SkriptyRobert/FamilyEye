package com.familyeye.agent.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

/**
 * Card style permission item used in Setup Wizard
 */
@Composable
fun PermissionCard(
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

/**
 * Row style permission item used in Settings
 */
@Composable
fun PermissionItem(
    label: String,
    isGranted: Boolean,
    onClick: () -> Unit
) {
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
