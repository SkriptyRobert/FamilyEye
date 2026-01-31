package com.familyeye.agent.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import kotlinx.coroutines.delay

@Composable
fun PinDialog(
    onPinVerified: () -> Unit,
    onDismiss: () -> Unit,
    verifyPin: suspend (String) -> Boolean
) {
    var pin by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var isVerifying by remember { mutableStateOf(false) }
    val focusRequester = remember { FocusRequester() }

    LaunchedEffect(Unit) {
        delay(100)
        focusRequester.requestFocus()
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Column(
                modifier = Modifier
                    .padding(24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "Rodičovský PIN",
                    style = MaterialTheme.typography.headlineSmall
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "Zadejte PIN pro přístup k nastavení",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center
                )
                
                Spacer(modifier = Modifier.height(24.dp))
                
                OutlinedTextField(
                    value = pin,
                    onValueChange = { 
                        if (it.length <= 6 && it.all { c -> c.isDigit() }) {
                            pin = it
                            error = null
                        }
                    },
                    label = { Text("PIN") },
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.NumberPassword,
                        imeAction = ImeAction.Done
                    ),
                    keyboardActions = KeyboardActions(
                        onDone = {
                            if (pin.length >= 4) {
                                isVerifying = true
                            }
                        }
                    ),
                    modifier = Modifier
                        .fillMaxWidth()
                        .focusRequester(focusRequester),
                    singleLine = true,
                    isError = error != null,
                    supportingText = error?.let { { Text(it, color = MaterialTheme.colorScheme.error) } },
                    enabled = !isVerifying
                )
                
                Spacer(modifier = Modifier.height(24.dp))
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDismiss,
                        modifier = Modifier.weight(1f),
                        enabled = !isVerifying
                    ) {
                        Text("Zrušit")
                    }
                    
                    Button(
                        onClick = { isVerifying = true },
                        modifier = Modifier.weight(1f),
                        enabled = pin.length >= 4 && !isVerifying
                    ) {
                        if (isVerifying) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Text("Ověřit")
                        }
                    }
                }
            }
        }
    }

    // Handle PIN verification
    LaunchedEffect(isVerifying) {
        if (isVerifying) {
            val isValid = verifyPin(pin)
            if (isValid) {
                onPinVerified()
            } else {
                error = "Nesprávný PIN"
                pin = ""
                isVerifying = false
            }
        }
    }
}

/**
 * Wrapper that requires PIN verification before showing content.
 */
@Composable
fun PinProtectedContent(
    verifyPin: suspend (String) -> Boolean,
    hasPin: suspend () -> Boolean,
    onDismiss: () -> Unit,
    content: @Composable () -> Unit
) {
    var pinVerified by remember { mutableStateOf(false) }
    var showPinDialog by remember { mutableStateOf(false) }
    var pinRequired by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        pinRequired = hasPin()
        if (!pinRequired) {
            // No PIN set, allow access
            pinVerified = true
        } else {
            showPinDialog = true
        }
    }

    if (pinVerified) {
        content()
    } else if (showPinDialog && pinRequired) {
        PinDialog(
            onPinVerified = {
                pinVerified = true
                showPinDialog = false
            },
            onDismiss = {
                showPinDialog = false
                onDismiss()
            },
            verifyPin = verifyPin
        )
    }
}
