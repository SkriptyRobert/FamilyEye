package com.familyeye.agent.data.repository

import com.familyeye.agent.data.api.dto.RuleDTO
import kotlinx.coroutines.flow.Flow

interface RuleRepository {
    fun getRules(): Flow<List<RuleDTO>>
    suspend fun refreshRules()
    suspend fun getLocalRules(): List<RuleDTO>
}
