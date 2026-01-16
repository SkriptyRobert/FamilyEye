package com.familyeye.agent.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.ui.viewmodel.SetupWizardViewModel

/**
 * Screen for setting up parental PIN after pairing.
 * This is step 2 of the setup flow: Pairing → PIN → Permissions → Dashboard
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SetupPinScreen(
    viewModel: SetupWizardViewModel = hiltViewModel(),
    onPinSet: () -> Unit
) {
    var pin by remember { mutableStateOf("") }
    var confirmPin by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(title = { Text("Nastavení PIN") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center
        ) {
            Icon(
                Icons.Default.Lock,
                contentDescription = null,
                modifier = Modifier.size(64.dp),
                tint = MaterialTheme.colorScheme.primary
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
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
                onValueChange = { 
                    if (it.length <= 6 && it.all { c -> c.isDigit() }) {
                        pin = it
                        error = null
                    }
                },
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
                onValueChange = { 
                    if (it.length <= 6 && it.all { c -> c.isDigit() }) {
                        confirmPin = it
                        error = null
                    }
                },
                label = { Text("Potvrdit PIN") },
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                isError = error != null,
                supportingText = error?.let { { Text(it, color = MaterialTheme.colorScheme.error) } }
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            Button(
                onClick = {
                    when {
                        pin.length < 4 -> error = "PIN musí mít alespoň 4 číslice"
                        pin != confirmPin -> error = "PIN se neshoduje"
                        else -> {
                            viewModel.savePin(pin)
                            onPinSet()
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = pin.length >= 4 && confirmPin.isNotEmpty()
            ) {
                Text("Pokračovat")
            }
        }
    }
}
