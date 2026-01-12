package com.familyeye.agent.ui.screens

import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PairingScreen(
    viewModel: PairingViewModel = hiltViewModel(),
    onPairingSuccess: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    var showManualInput by remember { mutableStateOf(true) }
    var manualToken by remember { mutableStateOf("") }
    
    // Auto-navigate on success
    LaunchedEffect(uiState) {
        if (uiState is PairingUiState.Success) {
            onPairingSuccess()
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(title = { Text("Párování zařízení") })
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
                        Text("Párování...")
                    }
                }
                is PairingUiState.Error -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
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
                                .padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            Text(
                                text = "Zadejte párovací token z webu:",
                                style = MaterialTheme.typography.titleMedium
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            OutlinedTextField(
                                value = manualToken,
                                onValueChange = { manualToken = it },
                                label = { Text("Token") },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true
                            )
                            Spacer(modifier = Modifier.height(24.dp))
                            Button(
                                onClick = {
                                    if (manualToken.isNotBlank()) {
                                        viewModel.pairDevice(
                                            token = manualToken,
                                            deviceName = android.os.Build.MODEL,
                                            macAddress = "02:00:00:00:00:00"
                                        )
                                    }
                                },
                                enabled = manualToken.isNotBlank(),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Spárovat")
                            }
                            Spacer(modifier = Modifier.height(16.dp))
                            TextButton(onClick = { showManualInput = false }) {
                                Text("Použít skener QR kódu")
                            }
                        }
                    } else {
                        // Camera View
                        QRCameraScanner(
                            onQrCodeScanned = { token ->
                                viewModel.pairDevice(
                                    token = token,
                                    deviceName = android.os.Build.MODEL,
                                    macAddress = "02:00:00:00:00:00"
                                )
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
                                text = "Naskenujte QR kód z webu",
                                color = MaterialTheme.colorScheme.onBackground
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Button(
                                onClick = { showManualInput = true },
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text("Zadat kód ručně")
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
