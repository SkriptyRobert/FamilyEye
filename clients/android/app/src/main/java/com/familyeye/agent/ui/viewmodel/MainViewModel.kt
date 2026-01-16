package com.familyeye.agent.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import com.familyeye.agent.data.repository.AgentConfigRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import javax.inject.Inject

import dagger.hilt.android.qualifiers.ApplicationContext

@HiltViewModel
class MainViewModel @Inject constructor(
    @ApplicationContext private val context: android.content.Context,
    configRepository: AgentConfigRepository
) : ViewModel() {

    val isPaired: StateFlow<Boolean?> = configRepository.isPaired
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = null
        )

    val dataSaverEnabled: StateFlow<Boolean> = configRepository.dataSaverEnabled
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = false
        )
    
    // Config repository reference for setter
    // Config repository reference for setter
    private val repository = configRepository

    fun setDataSaver(enabled: Boolean) {
        viewModelScope.launch {
            repository.setDataSaverEnabled(enabled)
        }
    }

    data class PermissionState(
        val hasUsage: Boolean = false,
        val hasOverlay: Boolean = false,
        val hasAccessibility: Boolean = false,
        val hasDeviceAdmin: Boolean = false,
        val hasBatteryOpt: Boolean = false
    )

    private val _permissions = kotlinx.coroutines.flow.MutableStateFlow(PermissionState())
    val permissions = _permissions.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = PermissionState()
    )

    init {
        refreshPermissions()
    }

    fun refreshPermissions() {
        _permissions.value = PermissionState(
            hasUsage = hasUsageStatsPermission(),
            hasOverlay = hasOverlayPermission(),
            hasAccessibility = hasAccessibilityPermission(),
            hasDeviceAdmin = hasDeviceAdminPermission(),
            hasBatteryOpt = hasBatteryOptimizationException()
        )
    }

    private fun hasUsageStatsPermission(): Boolean {
        val appOps = context.getSystemService(android.content.Context.APP_OPS_SERVICE) as android.app.AppOpsManager
        val mode = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            appOps.unsafeCheckOpNoThrow(
                android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        } else {
            appOps.checkOpNoThrow(
                android.app.AppOpsManager.OPSTR_GET_USAGE_STATS,
                android.os.Process.myUid(),
                context.packageName
            )
        }
        return mode == android.app.AppOpsManager.MODE_ALLOWED
    }

    private fun hasOverlayPermission(): Boolean {
        return android.provider.Settings.canDrawOverlays(context)
    }

    private fun hasAccessibilityPermission(): Boolean {
        val componentName = android.content.ComponentName(context, com.familyeye.agent.service.AppDetectorService::class.java)
        val enabledServicesSetting = android.provider.Settings.Secure.getString(
            context.contentResolver,
            android.provider.Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false
        
        val colonSplitter = android.text.TextUtils.SimpleStringSplitter(':')
        colonSplitter.setString(enabledServicesSetting)
        
        while (colonSplitter.hasNext()) {
            val componentNameString = colonSplitter.next()
            val enabledComponent = android.content.ComponentName.unflattenFromString(componentNameString)
            if (enabledComponent != null && enabledComponent == componentName) {
                return true
            }
        }
        return false
    }

    fun unpair() {
        viewModelScope.launch {
            repository.clearPairingData()
        }
    }

    private fun hasBatteryOptimizationException(): Boolean {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
            val powerManager = context.getSystemService(android.content.Context.POWER_SERVICE) as android.os.PowerManager
            return powerManager.isIgnoringBatteryOptimizations(context.packageName)
        }
        return true // Not applicable on older versions (or different handling)
    }

    private fun hasDeviceAdminPermission(): Boolean {
        val devicePolicyManager = context.getSystemService(android.content.Context.DEVICE_POLICY_SERVICE) as android.app.admin.DevicePolicyManager
        val componentName = android.content.ComponentName(context, com.familyeye.agent.receiver.FamilyEyeDeviceAdmin::class.java)
        return devicePolicyManager.isAdminActive(componentName)
    }

    // PIN Protection
    suspend fun verifyPin(pin: String): Boolean {
        return repository.verifyPin(pin)
    }

    suspend fun hasPin(): Boolean {
        return repository.hasPin()
    }
}

