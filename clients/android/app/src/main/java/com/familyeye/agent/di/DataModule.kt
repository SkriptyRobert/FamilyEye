package com.familyeye.agent.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStore
import androidx.room.Room
import com.familyeye.agent.data.local.AgentDatabase
import com.familyeye.agent.data.local.UsageLogDao
import com.familyeye.agent.data.local.RuleDao
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.familyeye.agent.data.repository.AgentConfigRepositoryImpl
import com.familyeye.agent.data.repository.RuleRepository
import com.familyeye.agent.data.repository.RuleRepositoryImpl
import com.familyeye.agent.data.repository.UsageRepository
import com.familyeye.agent.data.repository.UsageRepositoryImpl
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

// DataStore extension
private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "agent_settings")

/**
 * Hilt module providing data storage dependencies.
 */
@Module
@InstallIn(SingletonComponent::class)
object DataModule {

    @Provides
    @Singleton
    fun provideDataStore(@ApplicationContext context: Context): DataStore<Preferences> = 
        context.dataStore

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AgentDatabase = 
        Room.databaseBuilder(
            context,
            AgentDatabase::class.java,
            "familyeye_agent.db"
        )
        .fallbackToDestructiveMigration()
        .build()

    @Provides
    @Singleton
    fun provideUsageLogDao(database: AgentDatabase): UsageLogDao = 
        database.usageLogDao()

    @Provides
    @Singleton
    fun provideRuleDao(database: AgentDatabase): RuleDao = 
        database.ruleDao()
        
    @Provides
    @Singleton
    fun provideEncryptedSharedPreferences(@ApplicationContext context: Context): android.content.SharedPreferences {
        // Try to use EncryptedSharedPreferences, but fallback to regular SharedPreferences
        // if encryption fails (common on emulators or after Clear Data)
        return try {
            val masterKey = androidx.security.crypto.MasterKey.Builder(context)
                .setKeyScheme(androidx.security.crypto.MasterKey.KeyScheme.AES256_GCM)
                .build()

            androidx.security.crypto.EncryptedSharedPreferences.create(
                context,
                "secret_agent_prefs",
                masterKey,
                androidx.security.crypto.EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
                androidx.security.crypto.EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
            )
        } catch (e: Exception) {
            timber.log.Timber.e(e, "EncryptedSharedPreferences failed, using fallback regular SharedPreferences")
            // Fallback to regular SharedPreferences (less secure but stable)
            context.getSharedPreferences("agent_prefs_fallback", Context.MODE_PRIVATE)
        }
    }
}

@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    
    @Binds
    @Singleton
    abstract fun bindAgentConfigRepository(
        impl: AgentConfigRepositoryImpl
    ): AgentConfigRepository

    @Binds
    @Singleton
    abstract fun bindRuleRepository(
        impl: RuleRepositoryImpl
    ): RuleRepository

    @Binds
    @Singleton
    abstract fun bindUsageRepository(
        impl: UsageRepositoryImpl
    ): UsageRepository
}
