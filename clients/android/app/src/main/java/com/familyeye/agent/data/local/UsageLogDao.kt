package com.familyeye.agent.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

@Dao
interface UsageLogDao {
    @Insert
    suspend fun insert(log: UsageLogEntity): Long

    @Insert
    suspend fun insertAll(logs: List<UsageLogEntity>)

    @Query("SELECT * FROM usage_logs WHERE isSync = 0 ORDER BY timestamp ASC LIMIT :limit")
    suspend fun getUnsyncedLogs(limit: Int = 100): List<UsageLogEntity>

    @Query("UPDATE usage_logs SET isSync = 1 WHERE id IN (:ids)")
    suspend fun markAsSynced(ids: List<Long>)

    @Query("DELETE FROM usage_logs WHERE isSync = 1 AND timestamp < :olderThanTimestamp")
    suspend fun deleteSyncedLogsOlderThan(olderThanTimestamp: Long)
    
    @Query("SELECT SUM(durationSeconds) FROM usage_logs WHERE timestamp >= :startOfDayTimestamp")
    fun getTotalUsageToday(startOfDayTimestamp: Long): Flow<Int?>
    
    @Query("SELECT appName, SUM(durationSeconds) as total FROM usage_logs WHERE timestamp >= :startOfDayTimestamp GROUP BY appName")
    fun getAppUsageToday(startOfDayTimestamp: Long): Flow<List<AppUsageStats>>

    @Query("SELECT SUM(durationSeconds) FROM usage_logs WHERE packageName = :packageName AND timestamp >= :startOfDayTimestamp")
    suspend fun getUsageDurationForPackage(packageName: String, startOfDayTimestamp: Long): Int?
}

data class AppUsageStats(
    val appName: String,
    val total: Int
)
