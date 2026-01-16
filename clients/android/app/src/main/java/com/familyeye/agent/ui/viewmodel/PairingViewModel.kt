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
        viewModelScope.launch {
            _uiState.value = PairingUiState.Loading

            try {
                // Save backend URL first - this enables the dynamic URL interceptor
                val normalizedUrl = normalizeUrl(backendUrl)
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
                    _uiState.value = PairingUiState.Error("Chyba párování: ${response.code()}")
                }
            } catch (e: Exception) {
                Timber.e(e, "Pairing exception")
                _uiState.value = PairingUiState.Error(e.message ?: "Chyba připojení")
            }
        }
    }

    private fun normalizeUrl(url: String): String {
        var normalized = url.trim()
        // Ensure https:// prefix
        if (!normalized.startsWith("http://") && !normalized.startsWith("https://")) {
            normalized = "https://$normalized"
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
