package com.familyeye.agent.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Backspace
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.ShieldMoon
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.widget.Toast
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.device.DeviceOwnerPolicyEnforcer
import com.familyeye.agent.ui.viewmodel.MainViewModel
import kotlinx.coroutines.launch

enum class AdminScreenState {
    PIN_ENTRY,
    MENU,
    DEVICE_OWNER_DEACTIVATE
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminLoginScreen(
    viewModel: MainViewModel = hiltViewModel(),
    onLoginSuccess: () -> Unit,
    onBack: () -> Unit
) {
    var pin by remember { mutableStateOf("") }
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isLoading by remember { mutableStateOf(false) }
    var screenState by remember { mutableStateOf(AdminScreenState.PIN_ENTRY) }
    
    // Device Owner state
    val enforcer = remember { DeviceOwnerPolicyEnforcer.create(context) }
    var isDeviceOwner by remember { mutableStateOf(enforcer.isDeviceOwner()) }
    var showDeactivateConfirm by remember { mutableStateOf(false) }

    LaunchedEffect(pin) {
        if (pin.length == 4) {
            isLoading = true
            val isValid = viewModel.verifyPin(pin)
            if (isValid) {
                // Show menu after successful PIN
                screenState = AdminScreenState.MENU
            } else {
                Toast.makeText(context, "Nespravny PIN", Toast.LENGTH_SHORT).show()
                pin = ""
            }
            isLoading = false
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Text(when (screenState) {
                        AdminScreenState.PIN_ENTRY -> "Administrace"
                        AdminScreenState.MENU -> "Admin Menu"
                        AdminScreenState.DEVICE_OWNER_DEACTIVATE -> "Deaktivace Device Owner"
                    })
                },
                navigationIcon = {
                    IconButton(onClick = {
                        when (screenState) {
                            AdminScreenState.PIN_ENTRY -> onBack()
                            AdminScreenState.MENU -> onBack()
                            AdminScreenState.DEVICE_OWNER_DEACTIVATE -> screenState = AdminScreenState.MENU
                        }
                    }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Zpet")
                    }
                }
            )
        }
    ) { padding ->
        when (screenState) {
            AdminScreenState.PIN_ENTRY -> {
                // PIN Entry Screen
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(bottom = 32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(top = 48.dp)
                    ) {
                        Text(
                            text = "Zadejte PIN",
                            style = MaterialTheme.typography.titleLarge
                        )
                        Spacer(modifier = Modifier.height(32.dp))
                        
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            if (isLoading) {
                                CircularProgressIndicator(color = MaterialTheme.colorScheme.primary)
                            } else {
                                repeat(4) { index ->
                                    Box(
                                        modifier = Modifier
                                            .size(16.dp)
                                            .clip(CircleShape)
                                            .background(
                                                if (index < pin.length) MaterialTheme.colorScheme.primary 
                                                else MaterialTheme.colorScheme.surfaceVariant
                                            )
                                    )
                                }
                            }
                        }
                    }

                    // Numeric Keypad
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        val keys = listOf(
                            listOf("1", "2", "3"),
                            listOf("4", "5", "6"),
                            listOf("7", "8", "9"),
                            listOf("", "0", "DEL")
                        )

                        keys.forEach { row ->
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceEvenly
                            ) {
                                row.forEach { key ->
                                    KeypadButton(
                                        text = key,
                                        onClick = {
                                            if (key == "DEL") {
                                                if (pin.isNotEmpty()) pin = pin.dropLast(1)
                                            } else if (key.isNotEmpty()) {
                                                if (pin.length < 4) pin += key
                                            }
                                        }
                                    )
                                }
                            }
                        }
                    }
                }
            }
            
            AdminScreenState.MENU -> {
                // Admin Menu Screen
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Settings button
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onLoginSuccess() },
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .padding(20.dp)
                                .fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Icon(
                                Icons.Default.Settings,
                                contentDescription = null,
                                modifier = Modifier.size(32.dp)
                            )
                            Column {
                                Text(
                                    "Nastaveni",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    "Zobrazit nastaveni aplikace",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                    
                    // Device Owner section
                    if (isDeviceOwner) {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { screenState = AdminScreenState.DEVICE_OWNER_DEACTIVATE },
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.errorContainer
                            )
                        ) {
                            Row(
                                modifier = Modifier
                                    .padding(20.dp)
                                    .fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                Icon(
                                    Icons.Default.ShieldMoon,
                                    contentDescription = null,
                                    modifier = Modifier.size(32.dp),
                                    tint = MaterialTheme.colorScheme.error
                                )
                                Column {
                                    Text(
                                        "Deaktivovat Device Owner",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onErrorContainer
                                    )
                                    Text(
                                        "Odebrat vsechny ochrany Device Owner",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.7f)
                                    )
                                }
                            }
                        }
                    } else {
                        // Device Owner is not active - show info
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant
                            )
                        ) {
                            Row(
                                modifier = Modifier
                                    .padding(20.dp)
                                    .fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                Icon(
                                    Icons.Default.Shield,
                                    contentDescription = null,
                                    modifier = Modifier.size(32.dp),
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                Column {
                                    Text(
                                        "Device Owner neni aktivni",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        "Pro aktivaci pouzijte dashboard na PC",
                                        style = MaterialTheme.typography.bodyMedium,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }
                    }
                }
            }
            
            AdminScreenState.DEVICE_OWNER_DEACTIVATE -> {
                // Device Owner Deactivation Confirmation Screen
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(padding)
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(24.dp)
                ) {
                    // Warning Card
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .padding(16.dp)
                                .fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(16.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Icon(
                                Icons.Default.Warning,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.error,
                                modifier = Modifier.size(32.dp)
                            )
                            Column {
                                Text(
                                    "Upozorneni",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.error
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    "Toto odstraní vsechny Device Owner ochrany z tohoto zarizeni.",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onErrorContainer
                                )
                            }
                        }
                    }
                    
                    // What will happen
                    Card {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Text(
                                "Co se stane:",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold
                            )
                            listOf(
                                "Aplikaci FamilyEye bude mozne odinstalovat",
                                "Factory reset bude povolen",
                                "Safe Mode bude povolen",
                                "Force Stop bude povolen",
                                "USB debugging bude povolen"
                            ).forEach { item ->
                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text("•", fontWeight = FontWeight.Bold)
                                    Text(item, style = MaterialTheme.typography.bodyMedium)
                                }
                            }
                        }
                    }
                    
                    Spacer(modifier = Modifier.weight(1f))
                    
                    // Confirm Checkbox and Button
                    var confirmChecked by remember { mutableStateOf(false) }
                    
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.clickable { confirmChecked = !confirmChecked }
                    ) {
                        Checkbox(
                            checked = confirmChecked,
                            onCheckedChange = { confirmChecked = it }
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            "Rozumim dusledkum a chci pokracovat",
                            style = MaterialTheme.typography.bodyMedium
                        )
                    }
                    
                    Button(
                        onClick = {
                            val success = enforcer.deactivateAllProtections()
                            if (success) {
                                isDeviceOwner = false
                                Toast.makeText(
                                    context, 
                                    "Device Owner ochrany byly deaktivovany", 
                                    Toast.LENGTH_LONG
                                ).show()
                                screenState = AdminScreenState.MENU
                            } else {
                                Toast.makeText(
                                    context, 
                                    "Chyba pri deaktivaci ochran", 
                                    Toast.LENGTH_LONG
                                ).show()
                            }
                        },
                        enabled = confirmChecked,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Deaktivovat ochrany", modifier = Modifier.padding(vertical = 8.dp))
                    }
                }
            }
        }
    }
}

@Composable
fun KeypadButton(text: String, onClick: () -> Unit) {
    Box(
        modifier = Modifier
            .size(80.dp)
            .clip(CircleShape)
            .background(if (text.isNotEmpty()) MaterialTheme.colorScheme.surfaceVariant else Color.Transparent)
            .clickable(enabled = text.isNotEmpty(), onClick = onClick),
        contentAlignment = Alignment.Center
    ) {
        if (text == "DEL") {
            Icon(Icons.Default.Backspace, contentDescription = "Vymazat")
        } else {
            Text(
                text = text,
                style = MaterialTheme.typography.titleLarge,
                fontSize = 28.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}
