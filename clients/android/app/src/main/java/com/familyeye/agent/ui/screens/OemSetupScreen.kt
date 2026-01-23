package com.familyeye.agent.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.familyeye.agent.ui.OemSetupViewModel

@Composable
fun OemSetupWarningCard(
    viewModel: OemSetupViewModel,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()

    if (uiState.needsAttention) {
        val isError = !uiState.isStandardBatteryOptimizationIgnored
        val containerColor = if (isError) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer
        val contentColor = if (isError) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSecondaryContainer
        val iconColor = if (isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary

        Card(
            modifier = modifier
                .fillMaxWidth()
                .padding(16.dp),
            colors = CardDefaults.cardColors(
                containerColor = containerColor
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Varování",
                        tint = iconColor
                    )
                    Text(
                        text = if (isError) "Vyžadována oprava nastavení" else "Doporučené nastavení výrobce",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = contentColor
                    )
                }

                Text(
                    text = if (isError) 
                        "Váš telefon (${uiState.manufacturer}) může aplikaci ukončit. Pro správné fungování povolte:" 
                        else "Standardní oprávnění jsou OK, ale pro 100% spolehlivost na zařízení ${uiState.manufacturer} zbývá:",
                    style = MaterialTheme.typography.bodyMedium,
                    color = contentColor
                )

                Text(
                    text = uiState.setupInstructions,
                    style = MaterialTheme.typography.bodySmall,
                    fontWeight = FontWeight.SemiBold,
                    color = contentColor
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = { viewModel.refreshStatus() }) {
                        Text("Zkontrolovat")
                    }
                    
                    if (!uiState.isStandardBatteryOptimizationIgnored) {
                        Button(
                            onClick = { viewModel.openBatteryOptimizationSettings() },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.error
                            )
                        ) {
                            Text("Povolit optimalizaci")
                        }
                    } else if (uiState.isAggressiveOem) {
                        Button(
                            onClick = { viewModel.openAutoStartSettings() },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.primary
                            )
                        ) {
                            Text("Povolit Autostart")
                        }
                    }
                }
            }
        }
    }
}
