package com.familyeye.agent.ui.screens

import android.net.Uri
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.familyeye.agent.ui.viewmodel.PairingUiState
import com.familyeye.agent.ui.viewmodel.PairingViewModel
import com.google.zxing.BinaryBitmap
import com.google.zxing.MultiFormatReader
import com.google.zxing.PlanarYUVLuminanceSource
import com.google.zxing.common.HybridBinarizer
import timber.log.Timber
import java.util.concurrent.Executors

/**
 * Data class for parsed QR code content.
 * QR format: parental-control://pair?token=XXX&backend=https://IP:PORT
 */
data class QrPairingData(
    val token: String,
    val backendUrl: String
)

/**
 * Parse QR code content to extract token and backend URL.
 */
fun parseQrCode(qrContent: String): QrPairingData? {
    return try {
        // Try URI format first: parental-control://pair?token=XXX&backend=https://IP:PORT
        if (qrContent.startsWith("parental-control://") || qrContent.startsWith("familyeye://")) {
            val uri = Uri.parse(qrContent)
            val token = uri.getQueryParameter("token")
            val backend = uri.getQueryParameter("backend")
            
            if (token != null && backend != null) {
                return QrPairingData(token, backend)
            }
        }
        
        // Try JSON format: {"token":"XXX","backend":"https://IP:PORT"}
        if (qrContent.contains("\"token\"") && qrContent.contains("\"backend\"")) {
            // Simple regex extraction
            val tokenMatch = Regex("\"token\"\\s*:\\s*\"([^\"]+)\"").find(qrContent)
            val backendMatch = Regex("\"backend\"\\s*:\\s*\"([^\"]+)\"").find(qrContent)
            
            if (tokenMatch != null && backendMatch != null) {
                return QrPairingData(
                    tokenMatch.groupValues[1],
                    backendMatch.groupValues[1]
                )
            }
        }
        
        null
    } catch (e: Exception) {
        Timber.e(e, "Failed to parse QR code")
        null
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PairingScreen(
    viewModel: PairingViewModel = hiltViewModel(),
    onPairingSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showManualInput by remember { mutableStateOf(true) }
    var manualToken by remember { mutableStateOf("") }
    var manualBackendUrl by remember { mutableStateOf("") }
    
    // Auto-navigate on success
    LaunchedEffect(uiState) {
        if (uiState is PairingUiState.Success) {
            onPairingSuccess()
        }
    }

    Scaffold(
        topBar = {
            // Removed as per request for cleaner UI
        }
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            when (uiState) {
                is PairingUiState.Loading -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        CircularProgressIndicator()
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("Připojování k serveru...")
                    }
                }
                is PairingUiState.Error -> {
                    Column(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = (uiState as PairingUiState.Error).message,
                            color = MaterialTheme.colorScheme.error
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(onClick = { viewModel.resetState() }) {
                            Text("Zkusit znovu")
                        }
                    }
                }
                else -> {
                        if (showManualInput) {
                        Column(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(24.dp)
                                .verticalScroll(androidx.compose.foundation.rememberScrollState()),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            // Branded Header
                            // Branded Header
                            // Branded Header
                            androidx.compose.foundation.Image(
                                painter = androidx.compose.ui.res.painterResource(id = com.familyeye.agent.R.drawable.ic_logo_header),
                                contentDescription = "FamilyEye",
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(150.dp)
                                    .padding(bottom = 16.dp),
                                contentScale = androidx.compose.ui.layout.ContentScale.Fit
                            )
                            
                            Spacer(modifier = Modifier.height(32.dp))
                            
                            Spacer(modifier = Modifier.height(32.dp))
                            
                            // Backend URL Input
                            OutlinedTextField(
                                value = manualBackendUrl,
                                onValueChange = { manualBackendUrl = it },
                                label = { Text("Adresa serveru") },
                                placeholder = { Text("např. 192.168.0.100:8000") },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                                    unfocusedBorderColor = MaterialTheme.colorScheme.outline
                                ),
                                supportingText = { 
                                    Text("IP adresa nebo doména serveru FamilyEye") 
                                }
                            )
                            
                            Spacer(modifier = Modifier.height(16.dp))
                            
                            // Token Input
                            OutlinedTextField(
                                value = manualToken,
                                onValueChange = { manualToken = it },
                                label = { Text("Párovací token") },
                                placeholder = { Text("Zkopírujte z webové aplikace") },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true,
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = MaterialTheme.colorScheme.primary,
                                    unfocusedBorderColor = MaterialTheme.colorScheme.outline
                                )
                            )
                            
                            Spacer(modifier = Modifier.height(32.dp))
                            
                            Button(
                                onClick = {
                                    if (manualToken.isNotBlank() && manualBackendUrl.isNotBlank()) {
                                        viewModel.pairDevice(
                                            token = manualToken.trim(),
                                            backendUrl = manualBackendUrl.trim(),
                                            deviceName = android.os.Build.MODEL,
                                            macAddress = "02:00:00:00:00:00"
                                        )
                                    }
                                },
                                enabled = manualToken.isNotBlank() && manualBackendUrl.isNotBlank(),
                                modifier = Modifier.fillMaxWidth().height(50.dp)
                            ) {
                                Text("Spárovat zařízení", style = MaterialTheme.typography.titleMedium)
                            }
                            
                            Spacer(modifier = Modifier.height(24.dp))
                            
                            TextButton(onClick = { showManualInput = false }) {
                                Text("Skenovat QR kód")
                            }
                        }
                    } else {
                        // Camera View
                        QRCameraScanner(
                            onQrCodeScanned = { qrContent ->
                                val parsed = parseQrCode(qrContent)
                                if (parsed != null) {
                                    viewModel.pairDevice(
                                        token = parsed.token,
                                        backendUrl = parsed.backendUrl,
                                        deviceName = android.os.Build.MODEL,
                                        macAddress = "02:00:00:00:00:00"
                                    )
                                } else {
                                    // Fallback: treat as token only, ask for URL
                                    manualToken = qrContent
                                    showManualInput = true
                                }
                            }
                        )
                        
                        // Scan Frame Overlay
                        Box(
                            modifier = Modifier
                                .size(250.dp)
                                .align(Alignment.Center)
                        ) {
                            // TODO: Draw corner borders
                        }
                        
                        Column(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(bottom = 32.dp, start = 16.dp, end = 16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = "Naskenujte QR kód z webové aplikace",
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(
                                text = "QR kód obsahuje adresu serveru a párovací token",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Button(
                                onClick = { showManualInput = true },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Zadat ručně")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun QRCameraScanner(onQrCodeScanned: (String) -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraProviderFuture = remember { ProcessCameraProvider.getInstance(context) }
    
    AndroidView(
        factory = { ctx ->
            PreviewView(ctx).apply {
                implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            }
        },
        modifier = Modifier.fillMaxSize(),
        update = { previewView ->
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                
                val imageAnalysis = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                    .also {
                        it.setAnalyzer(Executors.newSingleThreadExecutor()) { imageProxy ->
                            try {
                                val buffer = imageProxy.planes[0].buffer
                                val data = ByteArray(buffer.remaining())
                                buffer.get(data)
                                
                                val source = PlanarYUVLuminanceSource(
                                    data, imageProxy.width, imageProxy.height,
                                    0, 0, imageProxy.width, imageProxy.height, false
                                )
                                val binaryBitmap = BinaryBitmap(HybridBinarizer(source))
                                val result = MultiFormatReader().decode(binaryBitmap)
                                
                                onQrCodeScanned(result.text)
                            } catch (e: Exception) {
                                // Not found, ignore
                            } finally {
                                imageProxy.close()
                            }
                        }
                    }

                try {
                    cameraProvider.unbindAll()
                    cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageAnalysis
                    )
                } catch (e: Exception) {
                    Timber.e(e, "Camera binding failed")
                }
            }, ContextCompat.getMainExecutor(context))
        }
    )
}
