package com.familyeye.agent.ui.viewmodel

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.admin.DevicePolicyManager
import android.content.Context
import android.content.pm.ServiceInfo
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.receiver.FamilyEyeDeviceAdmin
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

@HiltViewModel
class SetupWizardViewModel @Inject constructor(
    private val configRepository: AgentConfigRepository
) : ViewModel() {

    enum class SetupStep {
        WELCOME,
        PIN_SETUP,
        PERMISSIONS,
        OEM_CONFIG,
        DEVICE_OWNER_PREP,
        DEVICE_OWNER_PC,
        PAIRING,
        COMPLETE
    }

    private val _currentStep = MutableStateFlow(SetupStep.WELCOME)
    val currentStep: StateFlow<SetupStep> = _currentStep.asStateFlow()

    private val _isSetupComplete = MutableStateFlow(false)
    val isSetupComplete: StateFlow<Boolean> = _isSetupComplete.asStateFlow()

    fun nextStep(hasOemIssues: Boolean, isDeviceOwner: Boolean) {
        val current = _currentStep.value
        _currentStep.value = when (current) {
            SetupStep.WELCOME -> SetupStep.PIN_SETUP
            SetupStep.PIN_SETUP -> SetupStep.PERMISSIONS
            SetupStep.PERMISSIONS -> {
                if (hasOemIssues) SetupStep.OEM_CONFIG
                else if (isDeviceOwner) SetupStep.PAIRING
                else SetupStep.DEVICE_OWNER_PREP
            }
            SetupStep.OEM_CONFIG -> {
                if (isDeviceOwner) SetupStep.PAIRING
                else SetupStep.DEVICE_OWNER_PREP
            }
            SetupStep.DEVICE_OWNER_PREP -> SetupStep.DEVICE_OWNER_PC
            SetupStep.DEVICE_OWNER_PC -> SetupStep.PAIRING
            SetupStep.PAIRING -> SetupStep.COMPLETE
            SetupStep.COMPLETE -> SetupStep.COMPLETE
        }
    }

    fun previousStep(hasOemIssues: Boolean) {
        val current = _currentStep.value
        _currentStep.value = when (current) {
            SetupStep.WELCOME -> SetupStep.WELCOME
            SetupStep.PIN_SETUP -> SetupStep.WELCOME
            SetupStep.PERMISSIONS -> SetupStep.PIN_SETUP
            SetupStep.OEM_CONFIG -> SetupStep.PERMISSIONS
            SetupStep.DEVICE_OWNER_PREP -> {
                if (hasOemIssues) SetupStep.OEM_CONFIG
                else SetupStep.PERMISSIONS
            }
            SetupStep.DEVICE_OWNER_PC -> SetupStep.DEVICE_OWNER_PREP
            SetupStep.PAIRING -> {
                // If we came from PC step (user is DO) or skipped DO prep
                // This is a bit tricky, but usually we go back to the prep/pc flow
                SetupStep.DEVICE_OWNER_PREP 
            }
            SetupStep.COMPLETE -> SetupStep.PAIRING
        }
    }

    fun skipDeviceOwner() {
        if (_currentStep.value == SetupStep.DEVICE_OWNER_PREP) {
            _currentStep.value = SetupStep.PAIRING
        }
    }

    fun savePin(pin: String) {
        viewModelScope.launch {
            configRepository.savePin(pin)
            Timber.d("PIN saved")
        }
    }

    fun markSetupComplete() {
        viewModelScope.launch {
            // Could save a flag here if needed
            _isSetupComplete.value = true
        }
    }

    fun checkAccessibilityPermission(context: Context): Boolean {
        val accessibilityManager = context.getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        val enabledServices = accessibilityManager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
        
        return enabledServices.any { serviceInfo ->
            serviceInfo.resolveInfo.serviceInfo.packageName == context.packageName
        }
    }

    fun checkUsageStatsPermission(context: Context): Boolean {
        return try {
            val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE)
            if (usageStatsManager != null) {
                val appOpsManager = context.getSystemService(Context.APP_OPS_SERVICE) as android.app.AppOpsManager
                val mode = appOpsManager.checkOpNoThrow(
                    android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                    android.os.Process.myUid(),
                    context.packageName
                )
                mode == android.app.AppOpsManager.MODE_ALLOWED
            } else {
                false
            }
        } catch (e: Exception) {
            Timber.e(e, "Error checking usage stats permission")
            false
        }
    }

    fun checkOverlayPermission(context: Context): Boolean {
        return Settings.canDrawOverlays(context)
    }

    fun checkDeviceAdminPermission(context: Context): Boolean {
        val devicePolicyManager = context.getSystemService(Context.DEVICE_POLICY_SERVICE) as DevicePolicyManager
        val componentName = android.content.ComponentName(context, FamilyEyeDeviceAdmin::class.java)
        return devicePolicyManager.isAdminActive(componentName)
    }

    fun checkBatteryOptimizationPermission(context: Context): Boolean {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            val powerManager = context.getSystemService(Context.POWER_SERVICE) as android.os.PowerManager
            return powerManager.isIgnoringBatteryOptimizations(context.packageName)
        }
        return true
    }
}
