package com.familyeye.agent.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

@Composable
fun BlockOverlayScreen(appName: String, blockType: BlockType, scheduleInfo: String? = null, onDismiss: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.95f)), // Increased opacity for immersive feel
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp)
        ) {
            // Branded Image
            androidx.compose.foundation.Image(
                painter = androidx.compose.ui.res.painterResource(id = com.familyeye.agent.R.drawable.block_shield),
                contentDescription = null,
                modifier = Modifier
                    .size(180.dp) // Larger branding
                    .padding(bottom = 24.dp)
            )
            
            // Primary Message: "App X is blocked" or "Device Locked"
            Text(
                text = when(blockType) {
                    BlockType.DEVICE_LOCK -> "Zařízení uzamčeno"
                    BlockType.DEVICE_SCHEDULE -> "Mimo povolený čas"
                    BlockType.DEVICE_LIMIT -> "Denní limit vyčerpán"
                    BlockType.APP_FORBIDDEN -> "Aplikace zakázána"
                    else -> "Aplikace zablokována"
                },
                style = MaterialTheme.typography.headlineMedium,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )
            
            if (blockType != BlockType.DEVICE_LOCK && blockType != BlockType.DEVICE_SCHEDULE && blockType != BlockType.DEVICE_LIMIT) {
                Text(
                     text = appName,
                     style = MaterialTheme.typography.titleLarge,
                     color = MaterialTheme.colorScheme.primary, // Highlight app name
                     fontWeight = FontWeight.SemiBold,
                     textAlign = TextAlign.Center,
                     modifier = Modifier.padding(top = 8.dp)
                )
            }
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Secondary Description
            Text(
                text = when(blockType) {
                    BlockType.DEVICE_LOCK -> "Rodič toto zařízení dočasně uzamkl."
                    BlockType.DEVICE_SCHEDULE -> "Používání zařízení je v tuto dobu omezeno rozvrhem."
                    BlockType.DEVICE_LIMIT -> "Tvůj časový limit pro používání zařízení na dnešek vypršel."
                    BlockType.APP_FORBIDDEN -> "Tato aplikace (nebo hra) není povolena."
                    BlockType.APP_SCHEDULE -> "Přístup k této aplikaci je v tuto dobu omezen."
                    BlockType.APP_LIMIT -> "Tvůj časový limit pro tuto aplikaci na dnešek vypršel."
                    else -> "Přístup zablokován."
                },
                style = MaterialTheme.typography.bodyLarge,
                color = Color.LightGray,
                textAlign = TextAlign.Center
            )
            
            if (scheduleInfo != null) {
                Spacer(modifier = Modifier.height(16.dp))
                // Info Box
                Surface(
                    color = Color.White.copy(alpha = 0.1f),
                    shape = MaterialTheme.shapes.medium,
                    modifier = Modifier.padding(horizontal = 16.dp)
                ) {
                    Text(
                        text = scheduleInfo,
                        style = MaterialTheme.typography.titleMedium,
                        color = MaterialTheme.colorScheme.primary, // Highlight
                        fontWeight = FontWeight.Bold,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(16.dp)
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(48.dp))
            
            if (blockType != BlockType.DEVICE_LOCK && blockType != BlockType.DEVICE_SCHEDULE && blockType != BlockType.DEVICE_LIMIT) {
                Button(
                    onClick = onDismiss,
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Text("Zavřít", style = MaterialTheme.typography.titleMedium)
                }
            } else {
                // For critical blocks, maybe just an icon or "Emergency" info?
                // Or nothing, as requested by user ("Zavřít co?").
                // Just spacer to balance layout
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
}

enum class BlockType {
    DEVICE_LOCK,
    DEVICE_SCHEDULE,
    DEVICE_LIMIT,
    APP_FORBIDDEN,
    APP_SCHEDULE,
    APP_LIMIT,
    GENERIC
}
