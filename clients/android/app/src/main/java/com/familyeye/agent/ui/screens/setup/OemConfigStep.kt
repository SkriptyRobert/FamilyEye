package com.familyeye.agent.ui.screens.setup

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.familyeye.agent.ui.OemSetupViewModel
import com.familyeye.agent.ui.screens.OemSetupWarningCard

@Composable
fun OemConfigStep(
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
