package com.familyeye.agent.ui

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyeye.agent.utils.OemCompatibility
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * ViewModel for managing OEM-specific setup status and actions.
 * Tracks if the app has necessary permissions and settings on different phone brands.
 */
@HiltViewModel
class OemSetupViewModel @Inject constructor(
    @ApplicationContext private val context: Context
) : ViewModel() {

    data class OemSetupState(
        val isAggressiveOem: Boolean = false,
        val manufacturer: String = "",
        val isIgnoringBatteryOptimizations: Boolean = true,
        val setupInstructions: String = "",
        val needsAttention: Boolean = false,
        val isStandardBatteryOptimizationIgnored: Boolean = true
    )

    private val _uiState = MutableStateFlow(OemSetupState())
    val uiState: StateFlow<OemSetupState> = _uiState.asStateFlow()

    init {
        refreshStatus()
    }

    /**
     * Refresh the current status of OEM settings.
     */
    fun refreshStatus() {
        viewModelScope.launch {
            val manufacturer = OemCompatibility.getManufacturer()
            val isAggressive = OemCompatibility.isAggressiveOem()
            val isIgnoringBattery = OemCompatibility.isIgnoringBatteryOptimizations(context)
            
            _uiState.value = OemSetupState(
                isAggressiveOem = isAggressive,
                manufacturer = manufacturer,
                isIgnoringBatteryOptimizations = isIgnoringBattery,
                isStandardBatteryOptimizationIgnored = isIgnoringBattery,
                setupInstructions = OemCompatibility.getSetupInstructions(),
                needsAttention = isAggressive // On aggressive OEMs, we always show it until they finish standard + manually do AutoStart
            )
        }
    }

    /**
     * Launch OEM-specific auto-start settings.
     */
    fun openAutoStartSettings() {
        OemCompatibility.openAutoStartSettings(context)
    }

    /**
     * Launch system battery optimization settings.
     */
    fun openBatteryOptimizationSettings() {
        OemCompatibility.openBatteryOptimizationSettings(context)
    }
}
