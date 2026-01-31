package com.familyeye.agent.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface RuleDao {
    @Query("SELECT * FROM rules")
    fun getAllRulesConfig(): Flow<List<RuleEntity>>

    @Query("SELECT * FROM rules")
    suspend fun getAllRulesSnapshot(): List<RuleEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(rules: List<RuleEntity>)

    @Query("DELETE FROM rules")
    suspend fun deleteAll()

    @Transaction
    suspend fun clearAndInsert(rules: List<RuleEntity>) {
        deleteAll()
        insertAll(rules)
    }
}
