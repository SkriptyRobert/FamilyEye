package com.familyeye.agent.data.repository

import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.api.dto.RuleDTO
import com.familyeye.agent.data.local.RuleDao
import com.familyeye.agent.data.local.toDTO
import com.familyeye.agent.data.local.toEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RuleRepositoryImpl @Inject constructor(
    private val api: FamilyEyeApi,
    private val ruleDao: RuleDao,
    private val configRepository: AgentConfigRepository
) : RuleRepository {

    override fun getRules(): Flow<List<RuleDTO>> {
        return ruleDao.getAllRulesConfig().map { entities ->
            entities.map { it.toDTO() }
        }
    }

    override suspend fun refreshRules() {
        try {
            val deviceId = configRepository.getDeviceId() ?: run {
                Timber.w("Cannot refresh rules: Device ID not found")
                return
            }
            val apiKey = configRepository.getApiKey() ?: run {
                Timber.w("Cannot refresh rules: API Key not found")
                return
            }

            Timber.d("Refreshing rules from backend...")
            val response = api.getRules(
                com.familyeye.agent.data.api.dto.AgentAuthRequest(deviceId, apiKey)
            )
            if (response.isSuccessful) {
                val rulesResponse = response.body()
                if (rulesResponse != null) {
                    Timber.i("Fetched ${rulesResponse.rules.size} rules from backend")
                    // Save to local DB
                    val entities = rulesResponse.rules.map { it.toEntity() }
                    ruleDao.clearAndInsert(entities)
                    
                    // Note: We could also update usage stats if needed, but that's handled separately usually
                }
            } else {
                Timber.e("Failed to fetch rules: ${response.code()}")
            }
        } catch (e: Exception) {
            Timber.e(e, "Error during rule refresh")
            // On error, we just keep using local rules (Offline Mode support!)
        }
    }

    override suspend fun getLocalRules(): List<RuleDTO> {
        return ruleDao.getAllRulesSnapshot().map { it.toDTO() }
    }
}
