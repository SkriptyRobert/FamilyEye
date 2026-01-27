package com.familyeye.agent.ui.screens.setup

import android.content.Intent
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.familyeye.agent.utils.AccountHelper

@Composable
fun DeviceOwnerPrepStep(
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
