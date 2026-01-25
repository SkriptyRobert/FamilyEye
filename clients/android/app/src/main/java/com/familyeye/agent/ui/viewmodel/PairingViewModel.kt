package com.familyeye.agent.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.api.dto.PairingRequest
import com.familyeye.agent.data.repository.AgentConfigRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber
import java.util.UUID
import javax.inject.Inject

@HiltViewModel
class PairingViewModel @Inject constructor(
    private val api: FamilyEyeApi,
    private val configRepository: AgentConfigRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<PairingUiState>(PairingUiState.Idle)
    val uiState: StateFlow<PairingUiState> = _uiState.asStateFlow()

    fun pairDevice(token: String, backendUrl: String, deviceName: String, macAddress: String) {
        if (_uiState.value is PairingUiState.Loading || _uiState.value is PairingUiState.Success) {
            Timber.w("Pairing already in progress or completed, ignoring request")
            return
        }

        viewModelScope.launch {
            _uiState.value = PairingUiState.Loading

            // Normalize URL before try block so it's available in catch
            val normalizedUrl = normalizeUrl(backendUrl)

            try {
                // Save backend URL first - this enables the dynamic URL interceptor
                configRepository.saveBackendUrl(normalizedUrl)
                Timber.d("Saved backend URL: $normalizedUrl")

                // Generate a persistent UUID for this device installation
                val deviceId = UUID.randomUUID().toString()

                val request = PairingRequest(
                    token = token,
                    deviceName = deviceName,
                    macAddress = macAddress,
                    deviceId = deviceId
                )
                
                Timber.d("Sending pairing request: $request")
                
                val response = api.pairDevice(request)
                
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    configRepository.savePairingData(
                         deviceId = body.deviceId,
                         apiKey = body.apiKey
                    )
                    _uiState.value = PairingUiState.Success
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "Unknown error"
                    Timber.e("Pairing failed: $errorMsg")
                    
                    val userMessage = when (response.code()) {
                        404 -> "Token nebyl nalezen nebo vypršel.\n\nZkuste vygenerovat nový QR kód."
                        400 -> "Neplatný požadavek: $errorMsg"
                        500 -> "Chyba serveru. Zkuste to později."
                        else -> "Chyba párování (${response.code()}): $errorMsg"
                    }
                    
                    _uiState.value = PairingUiState.Error(userMessage)
                }
            } catch (e: Exception) {
                Timber.e(e, "Pairing exception")
                
                // Provide user-friendly error messages
                val errorMessage = when {
                    e.message?.contains("ENETUNREACH") == true || 
                    e.message?.contains("Network is unreachable") == true ||
                    e.message?.contains("Failed to connect") == true -> {
                        "Nelze se připojit k serveru $normalizedUrl.\n\n" +
                        "Zkontrolujte:\n" +
                        "• Jste na stejné Wi-Fi síti?\n" +
                        "• Běží backend server?\n" +
                        "• Firewall neblokuje port 8000?\n" +
                        "• IP adresa je správná?"
                    }
                    e.message?.contains("SSL") == true || 
                    e.message?.contains("certificate") == true -> {
                        "Chyba SSL certifikátu.\n\n" +
                        "Pro lokální vývoj povolte self-signed certifikáty."
                    }
                    e.message?.contains("timeout") == true -> {
                        "Připojení vypršelo.\n\n" +
                        "Server neodpovídá. Zkontrolujte, zda backend běží."
                    }
                    else -> {
                        "Chyba připojení: ${e.message ?: "Neznámá chyba"}\n\n" +
                        "Zkontrolujte síťové připojení a URL serveru."
                    }
                }
                
                _uiState.value = PairingUiState.Error(errorMessage)
            }
        }
    }

    private fun normalizeUrl(url: String): String {
        var normalized = url.trim()
        
        // Remove any whitespace
        normalized = normalized.replace("\\s".toRegex(), "")
        
        // If user entered just IP:PORT, add https://
        if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
            // Check if it looks like IP:PORT or domain:PORT
            if (normalized.contains(":") && !normalized.contains("/")) {
                normalized = "https://$normalized"
            } else {
                // Assume it's a domain or IP without port
                normalized = "https://$normalized:8000"
            }
        }
        
        // Remove trailing slash
        return normalized.trimEnd('/')
    }

    fun resetState() {
        _uiState.value = PairingUiState.Idle
    }
}

sealed class PairingUiState {
    object Idle : PairingUiState()
    object Loading : PairingUiState()
    object Success : PairingUiState()
    data class Error(val message: String) : PairingUiState()
}
