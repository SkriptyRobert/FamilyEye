package com.familyeye.agent.di

import android.content.Context
import com.familyeye.agent.BuildConfig
import com.familyeye.agent.data.api.FamilyEyeApi
import com.familyeye.agent.data.repository.AgentConfigRepository
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Dns
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import timber.log.Timber
import java.net.InetAddress
import java.net.Inet4Address
import java.security.SecureRandom
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.inject.Singleton
import javax.net.ssl.SSLContext
import javax.net.ssl.TrustManager
import javax.net.ssl.X509TrustManager

/**
 * Hilt module providing network-related dependencies.
 * Uses dynamic base URL from AgentConfigRepository.
 */
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    // Placeholder URL - will be replaced by interceptor
    private const val PLACEHOLDER_BASE_URL = "https://placeholder.local/"

    @Provides
    @Singleton
    fun provideMoshi(): Moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    /**
     * DNS resolver that prefers IPv4 addresses to avoid IPv6 connection issues
     * when server is only accessible via IPv4 (common in local networks).
     */
    private val ipv4PreferredDns: Dns = object : Dns {
        override fun lookup(hostname: String): List<InetAddress> {
            val addresses = Dns.SYSTEM.lookup(hostname)
            // Prefer IPv4 addresses - filter IPv6 if IPv4 exists
            val ipv4Addresses = addresses.filter { it is Inet4Address }
            
            // If we have IPv4 addresses, use only those. Otherwise use all.
            return if (ipv4Addresses.isNotEmpty()) {
                Timber.d("DNS lookup for $hostname: Using IPv4 addresses (${ipv4Addresses.size})")
                ipv4Addresses
            } else {
                Timber.d("DNS lookup for $hostname: No IPv4 found, using all addresses (${addresses.size})")
                addresses // Fallback to all if no IPv4 available
            }
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        @ApplicationContext context: Context,
        configRepository: AgentConfigRepository
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .protocols(listOf(okhttp3.Protocol.HTTP_1_1)) // Force HTTP/1.1 to avoid ALPN/SSL issues on local server
            .dns(ipv4PreferredDns) // Prefer IPv4 to avoid ENETUNREACH errors

        // Dynamic Base URL Interceptor
        val dynamicUrlInterceptor = Interceptor { chain ->
            val originalRequest = chain.request()
            val originalUrl = originalRequest.url

            // Get stored backend URL
            val storedUrl = runBlocking { configRepository.getBackendUrl() }
            
            if (storedUrl != null && (originalUrl.host == "placeholder.local" || originalUrl.host == "127.0.0.1" || originalUrl.host == "localhost")) {
                // Replace placeholder or local with actual backend URL
                val newBaseUrl = storedUrl.toHttpUrlOrNull()
                if (newBaseUrl != null) {
                    val newUrl = originalUrl.newBuilder()
                        .scheme(newBaseUrl.scheme)
                        .host(newBaseUrl.host)
                        .port(newBaseUrl.port)
                        .build()
                    
                    val newRequest = originalRequest.newBuilder()
                        .url(newUrl)
                        .header("Connection", "close") // Avoid socket reuse issues
                        .build()
                    
                    return@Interceptor chain.proceed(newRequest)
                }
            }
            
            chain.proceed(originalRequest)
        }
        
        builder.addInterceptor(dynamicUrlInterceptor)

        // Add logging in debug builds
        if (BuildConfig.DEBUG) {
            val loggingInterceptor = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            builder.addInterceptor(loggingInterceptor)
            
            try {
                // Trust all certificates for local development (self-signed)
                val trustAllCerts = arrayOf<TrustManager>(object : X509TrustManager {
                    override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
                    override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {}
                    override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
                })
                
                val sslContext = SSLContext.getInstance("TLS")
                sslContext.init(null, trustAllCerts, SecureRandom())
                
                builder.sslSocketFactory(sslContext.socketFactory, trustAllCerts[0] as X509TrustManager)
                builder.hostnameVerifier { _, _ -> true }
            } catch (e: Exception) {
                Timber.e(e, "Failed to set up TrustAll certificates")
            }
        }

        return builder.build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(okHttpClient: OkHttpClient, moshi: Moshi): Retrofit = Retrofit.Builder()
        .baseUrl(PLACEHOLDER_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .build()

    @Provides
    @Singleton
    fun provideFamilyEyeApi(retrofit: Retrofit): FamilyEyeApi = 
        retrofit.create(FamilyEyeApi::class.java)
}
