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

    fun pairDevice(token: String, deviceName: String, macAddress: String) {
        viewModelScope.launch {
            _uiState.value = PairingUiState.Loading

            try {
                // Generate a persistent UUID for this device installation if needed
                // For now, we rely on the server validation or use a random one
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
                         deviceId = body.deviceId, // Server might return same or normalized ID
                         apiKey = body.apiKey
                    )
                    _uiState.value = PairingUiState.Success
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "Unknown error"
                    Timber.e("Pairing failed: $errorMsg")
                    _uiState.value = PairingUiState.Error("Failed to pair: ${response.code()}")
                }
            } catch (e: Exception) {
                Timber.e(e, "Pairing exception")
                _uiState.value = PairingUiState.Error(e.message ?: "Connection error")
            }
        }
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
